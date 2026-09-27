import os
import sys
import socket
import time
import configparser
import requests
import tkinter as tk
from tkinter import simpledialog, messagebox
from google import genai
from google.api_core.exceptions import ResourceExhausted, GoogleAPICallError
from core.database_manager import DatabaseManager
from core import diagnostics_cache
from core.disk_analyzer import DiskAnalyzer
from utils import mode_manager

_MODEL = "gemini-2.5-flash"  # Best available model on this API key (confirmed via ListModels)
_MAX_RETRIES = 2             # Retry on 429 before showing error
_RETRY_DELAY = 5             # Seconds to wait between retries

def _get_config_path():
    """Returns path to config.ini next to the exe (or script in dev mode)."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller .exe
        base = os.path.dirname(sys.executable)
    else:
        # Running as script (dev mode) — use project root
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "config.ini")

def _load_api_key():
    """Load API key from config.ini, or prompt the user to enter it."""
    config_path = _get_config_path()
    config = configparser.ConfigParser()

    # Try reading existing key
    if os.path.exists(config_path):
        config.read(config_path)
        key = config.get("TechGuardAI", "GEMINI_API_KEY", fallback="").strip()
        if key and "your_key_here" not in key.lower():
            return key

    # No key found — show a clean dialog asking for it
    root = tk.Tk()
    root.withdraw()  # Hide the blank root window

    messagebox.showinfo(
        "TechGuardAI — First-Time Setup",
        "Welcome to TechGuardAI!\n\n"
        "To enable the AI assistant, you need a free Google Gemini API key.\n\n"
        "Get yours free at:\nhttps://aistudio.google.com/app/apikey\n\n"
        "Click OK to enter your key now.",
        parent=root
    )

    key = simpledialog.askstring(
        "Enter Gemini API Key",
        "Paste your Gemini API key below:",
        parent=root
    )
    root.destroy()

    if key and key.strip():
        key = key.strip()
        # Save for next time
        config["TechGuardAI"] = {"GEMINI_API_KEY": key}
        try:
            with open(config_path, "w") as f:
                config.write(f)
        except Exception as e:
            print(f"[Config] Could not save API key: {e}")
        return key

    return None

class TechGuardBrain:
    def __init__(self):
        api_key = _load_api_key()

        # Check if key is missing or is the default placeholder
        if not api_key or "your_key_here" in api_key.lower():
            self.client = None
            print("Warning: No Gemini API Key configured.")
        else:
            try:
                # Initialize the modern Gemini Client
                self.client = genai.Client(api_key=api_key)
            except Exception as e:
                self.client = None
                print(f"Error initializing Gemini: {e}")
        self.db = DatabaseManager()
        self.disk_analyzer = DiskAnalyzer("C:\\")

    def ask_gemini(self, user_message, system_snapshot, cleanup_candidates=None,
                   security_snapshot=None, chat_history=None):
        """
        Sends the user message + system stats + conversation history to Gemini.
        chat_history: list of (role, text) tuples — last 10 exchanges.
        """
        if not self.client:
            yield "⚠️ API Key not configured. Please restart TechGuardAI and enter your Gemini API key when prompted."
            return

        # ── Context sections (only include if genuinely relevant) ──────────────
        diag_snapshot = diagnostics_cache.get_snapshot()
        diag_section = f"\n### DIAGNOSTICS (last scan):\n{diag_snapshot}\n" if diag_snapshot else ""

        try:
            disk_summary = self.disk_analyzer.get_chatbot_summary()
        except Exception:
            disk_summary = "Disk analysis unavailable."

        raw_predictions = self.db.get_predictions(days=7)
        predictions_section = ""
        if raw_predictions:
            lines = "\n".join(f"- {p}" for p in raw_predictions)
            predictions_section = f"\n### RECURRING ISSUES (last 7 days):\n{lines}\n"

        # ── Conversation history ───────────────────────────────────────────────
        history_text = ""
        if chat_history:
            # Only include last 6 messages (3 exchanges) for token efficiency
            recent = chat_history[-6:]
            history_lines = []
            for role, text in recent:
                label = "User" if role == "user" else "Assistant"
                # Truncate long bot responses in history to save tokens
                snippet = text[:300] + "..." if len(text) > 300 else text
                history_lines.append(f"{label}: {snippet}")
            history_text = "\n### CONVERSATION SO FAR:\n" + "\n".join(history_lines) + "\n"

        # ── Main prompt ────────────────────────────────────────────────────────
        # ── Beginner-mode language instruction ───────────────────────────────────
        beginner_block = ""
        if mode_manager.is_beginner():
            beginner_block = """
### IMPORTANT — USER IS IN BEGINNER MODE:
This person is NOT technical. You MUST follow ALL of these rules:
- Say "processor" not "CPU", "memory" not "RAM", "storage" not "disk"
- NEVER use percentages, error codes, log names, or technical jargon
- Keep every reply SHORT — 2-3 sentences max for simple questions
- Always end with ONE easy action the user can take right now
- Use simple analogies: processor = car engine, memory = desk space, storage = filing cabinet
- Be warm, calm, and encouraging — like explaining to a friend with no tech knowledge
- If something is fine, just say "Everything looks great!" and stop.
"""

        prompt = f"""{beginner_block}You are TechGuard AI — a friendly Windows PC assistant embedded in a sidebar chat.

### RESPONSE RULES (follow these above all else):
1. **Match the detail level to the question.**
   - Simple/short question (e.g. "hi", "yes", "is my PC ok?") → 1-3 sentences max.
   - Broad/full request (e.g. "tell me everything", "full report", "what do you know about my PC", "analyze my system") → give a COMPLETE, structured breakdown covering CPU, RAM, Disk, Network, Battery, top processes, recurring issues, and any diagnostic data available.
   - Action follow-up (e.g. "yes", "ok", "do it", "sure") → continue directly from your last message without repeating system info.
2. **Follow the conversation thread.** If the user says "yes" or "ok", look at your LAST message and continue from there. Do NOT restart or re-dump stats.
3. **Only mention stats if relevant** — unless a broad report was requested.
4. **Actions work.** You CAN navigate the user or perform actions.
   - `[ACTION: OPEN_PRO_TOOLS]` (Use this if they ask to update software, check startup apps, view active network connections, or block Windows privacy tracking.)
   - `[ACTION: OPEN_FIX_CENTER]` (Use this if they ask for step-by-step fixes to a common Windows error or symptom, like bluescreens, slow wifi, or event logs.)
   - `[ACTION: OPEN_DRIVE_ANALYZER]` (To find large files)
   - `[ACTION: CLEAR_TEMP]` (To clean system temp files)
   - `[ACTION: KILL_PID: <pid>]` (To kill an exact process ID)
5. Plain English only — no raw error codes or log dumps.

### SYSTEM SNAPSHOT:
{system_snapshot}

### DISK (C: Drive):
{disk_summary}

### SECURITY AUDIT:
{security_snapshot if security_snapshot else "N/A"}
{diag_section}{predictions_section}
### 24h TRENDS:
{self.db.get_historical_context(24)}
{history_text}
### USER MESSAGE:
"{user_message}"

Respond now — match the depth and detail to exactly what the user asked for:"""

        # Inject alert only when system is under real pressure
        cpu_usage = float(system_snapshot.get("CPU Logic", "0%").split("%")[0])
        ram_usage = float(system_snapshot.get("RAM Usage", "0%").split("%")[0])

        if (cpu_usage > 70 or ram_usage > 80) and cleanup_candidates:
            alert = "\n### HIGH RESOURCE ALERT (mention briefly if relevant):\n"
            for app in cleanup_candidates:
                alert += f"- {app['name']} (PID: {app['pid']}, {app['mem']} MB)\n"
            prompt = prompt.replace("### USER MESSAGE:", alert + "\n### USER MESSAGE:")

        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = self.client.models.generate_content_stream(
                    model=_MODEL,
                    contents=prompt
                )
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                return  # Success — exit the retry loop

            except ResourceExhausted:
                # google.api_core 429 — wait and retry
                if attempt < _MAX_RETRIES:
                    print(f"[AI] Rate limited (attempt {attempt+1}), retrying in {_RETRY_DELAY}s...")
                    time.sleep(_RETRY_DELAY)
                    continue
                yield "⚠️ The AI service is busy (rate limit). Please wait a minute and try again."
                return

            except (socket.gaierror, socket.timeout, ConnectionError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout, OSError) as e:
                print(f"Network Error: {e}")
                yield ("🌐 Looks like you're offline! I couldn't reach the AI service.\n\n"
                       "Please check your internet connection and try again.")
                return

            except GoogleAPICallError as e:
                err_lower = str(e).lower()
                if "api key" in err_lower or "permission" in err_lower or "unauthenticated" in err_lower:
                    print(f"Auth Error: {e}")
                    yield ("🔑 There's a problem with the API key. Please check that your "
                           "GEMINI_API_KEY in the .env file is correct and try again.")
                elif "not found" in err_lower or "model" in err_lower:
                    print(f"Model Error: {e}")
                    yield "🤖 Hmm, I couldn't find the right AI model. Please try again in a moment."
                else:
                    print(f"API Error: {e}")
                    yield "😕 Something went wrong on the AI service side. Please try again in a moment."
                return

            except Exception as e:
                err_lower = str(e).lower()
                print(f"AI Error: {type(e).__name__}: {e}")

                # The google-genai Client SDK raises 429 as its own type — catch by message
                is_rate_limit = any(w in err_lower for w in (
                    "429", "quota", "resource_exhausted", "resource exhausted",
                    "rate limit", "too many requests"
                ))
                if is_rate_limit and attempt < _MAX_RETRIES:
                    print(f"[AI] Rate limited (attempt {attempt+1}), retrying in {_RETRY_DELAY}s...")
                    time.sleep(_RETRY_DELAY)
                    continue

                if is_rate_limit:
                    yield ("⚠️ The AI service is busy right now (rate limit reached). "
                           "Please wait a moment and try again.")
                elif any(w in err_lower for w in ("connect", "network", "internet", "timeout",
                                                   "unreachable", "dns", "ssl", "timed out")):
                    yield ("🌐 Looks like you're offline! I couldn't reach the AI service.\n\n"
                           "Please check your internet connection and try again.")
                elif any(w in err_lower for w in ("api key", "unauthenticated", "permission",
                                                   "forbidden", "401", "403")):
                    yield ("🔑 There's a problem with the API key. Please check that your "
                           "GEMINI_API_KEY in the .env file is correct and try again.")
                elif any(w in err_lower for w in ("not found", "404", "model")):
                    yield "🤖 The AI model wasn't found. Please try again in a moment."
                else:
                    yield ("😕 Something unexpected happened and I couldn't get a response. "
                           "Please try again in a moment.")
                return