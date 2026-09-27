import customtkinter as ctk
from ui.styles import THEME, FONTS
import threading
import re
import time
from core.action_handler import ActionHandler
from core.security_scanner import SecurityScanner

class ChatBubble(ctk.CTkFrame):
    def __init__(self, master, sender, message, is_user=True, **kwargs):
        # Determine alignment and color
        bg_color = THEME["user_bubble"] if is_user else THEME["bot_bubble"]
        align = "e" if is_user else "w"
        padx = (50, 5) if is_user else (5, 50)
        
        super().__init__(master, fg_color=bg_color, corner_radius=15, **kwargs)
        
        # Header (Sender Name)
        ctk.CTkLabel(self, text=sender, font=FONTS["small"], text_color="#aaaaaa").pack(anchor="w", padx=10, pady=(5, 0))
        
        # Message Body
        self.msg_label = ctk.CTkLabel(self, text=message, font=FONTS["body"], 
                                      wraplength=220, justify="left")
        self.msg_label.pack(anchor="w", padx=10, pady=(0, 10))

    def update_text(self, new_text):
        self.msg_label.configure(text=new_text)

class ChatbotFrame(ctk.CTkFrame):
    def __init__(self, master, bot_engine, bot_brain, monitor, navigate_cb=None):
        super().__init__(master, fg_color=THEME["card_color"], width=300)
        self.bot = bot_engine
        self.bot_brain = bot_brain
        self.monitor = monitor
        self.navigate_cb = navigate_cb   # callback: navigate_cb("drive_analyzer")
        self.action_handler = ActionHandler()
        self.security_scanner = SecurityScanner()
        
        self.pack_propagate(False)
        
        # Header
        ctk.CTkLabel(self, text="🤖 TechGuard AI Chatbot", font=FONTS["header"]).pack(pady=(15, 10))
        
        # Chat Display Space (Scrollable)
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Typing Indicator (Hidden by default)
        self.typing_label = ctk.CTkLabel(self.scroll_frame, text="TechGuard is thinking...", 
                                         font=FONTS["small"], text_color=THEME["accent_color"])
        
        self.entry_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.entry_frame.pack(fill="x", padx=10, pady=10)
        
        self.entry = ctk.CTkEntry(self.entry_frame, placeholder_text="Ask about system health...", height=40)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self.send_message)
        
        self.send_btn = ctk.CTkButton(self.entry_frame, text="Send", width=60, height=40, 
                                      fg_color=THEME["accent_color"], command=self.send_message)
        self.send_btn.pack(side="right", padx=(5,0))
        
        self.last_bubble = None
        self.action_btn = None
        self._pending_text = None  # For batched streaming updates
        self._chat_history = []    # Rolling conversation history [(role, text), ...]
        
        # Fast scroll — bind mouse wheel to scroll 3× faster
        self._bind_fast_scroll(self.scroll_frame)

    def _bind_fast_scroll(self, widget):
        """Binds mouse wheel to scroll 3x faster than the default."""
        def _on_scroll(event):
            widget._parent_canvas.yview_scroll(int(-1 * (event.delta / 40)), "units")
        widget.bind("<MouseWheel>", _on_scroll)
        # Also bind all children added later
        widget._parent_canvas.bind("<MouseWheel>", _on_scroll)

    def send_message(self, event=None):
        msg = self.entry.get().strip()
        if not msg: return

        self._display_bubble("You", msg, is_user=True)
        self.entry.delete(0, "end")
        self._chat_history.append(("user", msg))

        # Show typing indicator
        self.typing_label.pack(anchor="w", padx=10, pady=5)

        # Run AI (pass a copy of history so threading is safe)
        threading.Thread(
            target=self._get_ai_response,
            args=(msg, list(self._chat_history)),
            daemon=True
        ).start()

    def run_security_scan(self):
        msg = "Please run a Security Audit."
        self._display_bubble("You", msg, is_user=True)
        self._chat_history.append(("user", msg))
        self.typing_label.pack(anchor="w", padx=10, pady=5)
        threading.Thread(
            target=self._get_ai_response,
            args=("Analyze system security.", list(self._chat_history), True),
            daemon=True
        ).start()

    def _get_ai_response(self, msg, history=None, include_security=False):
        stats = self.monitor.get_all_stats()
        cleanup = self.monitor.get_cleanup_candidates()
        security = self.security_scanner.get_security_snapshot() if include_security else None

        if self.bot_brain.client:
            # Create empty bot bubble
            self.after(0, lambda: self._display_bubble("Bot", "", is_user=False))

            full_response = ""
            last_ui_update = time.time()

            try:
                for chunk in self.bot_brain.ask_gemini(msg, stats, cleanup, security, history):
                    full_response += chunk
                    now = time.time()
                    if now - last_ui_update >= 0.06:
                        self._update_last_bubble_thread_safe(full_response)
                        last_ui_update = now

                self._update_last_bubble_thread_safe(full_response)
                self._parse_and_handle_actions(full_response)

                # Store bot reply in history (trim to last 10 exchanges = 20 messages)
                self._chat_history.append(("bot", full_response))
                if len(self._chat_history) > 20:
                    self._chat_history = self._chat_history[-20:]

            except Exception:
                fallback = (full_response.strip() + "\n\n" if full_response.strip() else "") + \
                           "🌐 The connection was lost before I could finish. " \
                           "Please check your internet and try again."
                self._update_last_bubble_thread_safe(fallback)

            finally:
                self.after(0, self.typing_label.pack_forget)
        else:
            response = self.bot.get_response(msg)
            self.after(0, self.typing_label.pack_forget)
            self._display_bubble("Bot", response, is_user=False)

    def _display_bubble(self, sender, text, is_user):
        align = "e" if is_user else "w"
        padx = (40, 5) if is_user else (5, 40)
        
        bubble = ChatBubble(self.scroll_frame, sender, text, is_user=is_user)
        bubble.pack(anchor=align, padx=padx, pady=5, fill="x")
        
        if not is_user:
            self.last_bubble = bubble
            
        # Scroll to bottom
        self.after(10, lambda: self.scroll_frame._parent_canvas.yview_moveto(1.0))

    def _update_last_bubble_thread_safe(self, text):
        if self.last_bubble:
            self.after(0, lambda: self.last_bubble.update_text(text))
            self.after(0, lambda: self.scroll_frame._parent_canvas.yview_moveto(1.0))

    def _parse_and_handle_actions(self, text):
        cleaned_text = re.sub(r'\[ACTION:.*?\]', '', text)
        if cleaned_text != text:
             self._update_last_bubble_thread_safe(cleaned_text)

        kill_match = re.search(r'\[ACTION: KILL_PID: (\d+)\]', text)
        if kill_match:
            pid = int(kill_match.group(1))
            self._show_fix_button(f"Terminate PID {pid}", lambda: self._execute_kill(pid))

        if "[ACTION: CLEAR_TEMP]" in text:
            self._show_fix_button("Clear Temp Files", self._execute_clear_temp)

        if "[ACTION: OPEN_DRIVE_ANALYZER]" in text:
            self._show_fix_button("💾 Open Drive Analyzer", self._execute_open_drive_analyzer)

        if "[ACTION: OPEN_PRO_TOOLS]" in text:
            self._show_fix_button("🛠️ Open Pro Tools", lambda: self._execute_navigate("pro_tools"))

        if "[ACTION: OPEN_FIX_CENTER]" in text:
            self._show_fix_button("🔧 Open Fix Center", lambda: self._execute_navigate("fix_center"))

    def _show_fix_button(self, label, command):
        def _create():
            if self.action_btn: self.action_btn.destroy()
            self.action_btn = ctk.CTkButton(self, text=f"🛠 {label}", 
                                           fg_color=THEME["danger_color"], command=command)
            self.action_btn.pack(pady=10, padx=20, fill="x")
        self.after(0, _create)

    def _execute_kill(self, pid):
        success, msg = self.action_handler.terminate_process(pid)
        self._display_bubble("System", msg, is_user=False)
        if success and self.action_btn: self.action_btn.destroy()

    def _execute_clear_temp(self):
        success, msg = self.action_handler.clear_temp_files()
        self._display_bubble("System", msg, is_user=False)
        if success and self.action_btn: self.action_btn.destroy()

    def _execute_open_drive_analyzer(self):
        self._execute_navigate("cleanup")

    def _execute_navigate(self, page_id):
        # Map old IDs directly to the new 5-category layout
        route_map = {
            "drive_analyzer": "cleanup",
            "pro_tools": "security", # Maps network/privacy directly
            "fix_center": "fixes"
        }
        target = route_map.get(page_id, page_id)
        
        if self.navigate_cb:
            self.navigate_cb(target)
            if self.action_btn:
                self.action_btn.destroy()
                self.action_btn = None
        else:
            self._display_bubble("System", f"Please click the button in the sidebar.", is_user=False)
