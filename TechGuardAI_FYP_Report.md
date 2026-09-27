# TechGuardAI: Intelligent System Optimization and Context-Aware AI Diagnostics
**Final Year Project (FYP) Report Documentation**

---

## 1. Introduction
With the increasing complexity of modern operating systems, diagnosing performance lags, identifying privacy concerns, and managing system bloat has become exceptionally difficult for non-technical users. **TechGuardAI** is a proactive Windows system architect and diagnostic platform that solves this problem by combining powerful system-level scripts with an autonomous, context-aware Generative AI chatbot (powered by Google Gemini). By bridging the gap between highly technical OS data (such as WMI hardware queries, registry keys, and network socket maps) and plain-english explanations, TechGuardAI allows everyday users to visualize, secure, and optimize their computers effortlessly.

## 2. Problem Statement
Traditional system utility tools (e.g., Windows Task Manager, Event Viewer, CCleaner) suffer from two major flaws:
1. **Cognitive Overload & Technical Jargon:** End-users are provided raw data (e.g., "PID 7402", "142.250.190.46:443", or complex registry strings) without any meaningful explanation of what that data represents or if it is malicious.
2. **Disconnected Diagnostics:** When a computer is experiencing issues like thermal throttling or failing drives, users typically have to search error codes manually. There is no intermediate "intelligence" layer that automatically aggregates system vitals and contextualizes the solution for the user within a single interface.

TechGuardAI aims to eradicate these barriers by providing an automatic "Beginner Mode" data translation engine and a companion AI capable of directly "reading" the user's PC state to troubleshoot issues seamlessly.

## 3. Related Work
Currently, the market is populated with static utility tools:
- **CCleaner / BleachBit:** Excellent for purging cache files, but functionally static. They do not teach the user about system health or actively troubleshoot hardware problems.
- **Windows Task Manager:** Displays running apps but provides zero context regarding whether a high-memory background app is essential, malware, or bloatware.
- **Standalone Chatbots (ChatGPT / Gemini Web):** While intelligent, these models operate in a vacuum. A user must manually copy-paste crash logs or error codes into the browser to get help. 

*TechGuardAI sits at the intersection of these tools, automating system maintenance while natively passing the OS error logs to the AI without user friction.*

## 4. Methodology
The development of TechGuardAI follows an asynchronous, modular architecture divided into three discrete layers:
1. **Data Acquisition (The Core):** A suite of backend managers built using `psutil`, `winreg`, and `wmi`. These modules silently run background tasks to scrape live telemetry (Network sockets, Thermal statistics, System startup registries).
2. **Context-Aware Inference (The AI Brain):** When the user interacts with the AI, the backend injects a real-time "System Snapshot" into the hidden context of the LLM prompt. The AI knows exactly how much RAM is free and what apps are crashing without the user needing to type it. The AI can also return localized command tags (e.g., `[ACTION: OPEN_PRO_TOOLS]`) which magically warp the user's GUI to the correct category.
3. **Non-Blocking User Interface (The GUI):** Tkinter-based apps traditionally crash or freeze when executing heavy system scans. The project employs a strict **Thread-Worker Model**. All intensive hardware scans run in "Daemon Threads", safely passing the retrieved data back to the primary Graphic loop via `tkinter.after()` event marshalling.

## 5. Tools & Technologies
- **Programming Language:** Python 3.12+
- **GUI Framework:** `customtkinter` (for a modern, hardware-accelerated dark/light UX).
- **Core OS Libraries:** 
  - `psutil` (Hardware metrics)
  - `wmi` (Deep Windows Management Instrumentation for Thermal/Drive SMART diagnostics)
  - `winreg` (Modifying Windows startup behaviors)
- **AI Integration:** `google-genai` (Google's official Python SDK connecting the system to the Gemini API).
- **Data Persistence:** `sqlite3` (Local database for historic anomaly mapping and system logging).
- **Compilation:** `PyInstaller` (Translates the entire Python ecosystem into one standalone `TechGuardAI.exe` executable).

## 6. Results
The implementation yielded a highly stable, 5-category desktop application:
- **Clean Interface:** Consolidated hundreds of OS features into 5 intuitive Host Screens (Dashboard, Cleanup, Performance, Security, Fixes).
- **Thread Stability:** Successfully avoided "Application Not Responding" hangs by moving OS queries strictly into asynchronous thread queues, allowing the app to launch and navigate simultaneously in under `1.0` seconds.
- **UX Innovation:** The successful implementation of "Beginner Mode" visually masks raw PIDs and MBs, replacing them with dynamic algorithmic translations (e.g., "🔴 Heavy Impact" or translating active network sockets to domain names like "google.com").

## 7. Conclusions & Future Work
**Conclusion:** 
TechGuardAI establishes that system maintenance software does not need to be inherently technical. By utilizing LLMs practically as dynamic interpreters rather than simple text generators, non-technical users can perform "Pro-Level" hardware administration safely and correctly.

**Future Work:** 
Future iterations of TechGuardAI could incorporate:
- **Heuristic Malware Sandboxing:** Detecting zero-day viruses via behavioral process tracking.
- **Duplicate File Finder & Deep Disk Mapping:** Extending the cleanup tools.
- **Active Remediation Automation:** Allowing the AI brain to execute its own PowerShell scripts to repair corrupted OS components completely autonomously via verified signature repositories.

## 8. Demonstration (Presentation Guide)
*For your FYP Defense, follow this flow to show off the app's power:*

1. **The UX Toggle:** Start the app and click the `⚙️ Expert Mode` / `🎓 Beginner Mode` button. Show how terrifying raw registry keys and obscure PIDs instantly transform into beautifully simple English. 
2. **The 1-Click Optimize:** Go to the Dashboard and click the "Boost" button. Explain how the app asynchronously flushes the DNS and clears temp files securely in the background without freezing the UI.
3. **The Chatbot Context:** Ask the Chatbot: *"What is currently slowing down my PC?"*. It will accurately name the heaviest app running on your actual computer because it reads the hidden system snapshot!
4. **Action Routing:** Tell the Chatbot *"I want to update my old software"*. Watch as the AI identifies the intent and actually switches the live application's screen to the "Fixes & Updates" tab automatically.
5. **Advanced Diagnostics:** Show off the "Diagnostics" panel where WMI queries detect Thermal CPU Throttling and SMART drive failures—a feature typically only found in advanced server-grade monitoring tools.
