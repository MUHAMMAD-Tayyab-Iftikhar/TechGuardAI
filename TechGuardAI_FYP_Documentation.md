# TechGuardAI — Final Year Project (FYP) Technical Documentation

## Executive Summary
**TechGuardAI** is an intelligent, context-aware Windows system optimization, diagnostic, and security platform. Unlike traditional static utility cleaners (like CCleaner or Task Manager), TechGuardAI bridges the gap between expert-level diagnostic tools and non-technical end-users by integrating a real-time Generative AI assistant (Google Gemini) directly into the system's runtime memory. 

The application utilizes a completely asynchronous UI architecture, preventing freezing while parsing complex OS-level commands (WMI, Windows Registry, network sockets) in the background. It features a dual-mode UX: **Beginner Mode** (translates complex technical data like PIDs and IP addresses into plain English) and **Expert Mode** (exposes underlying system variables).

---

## 1. Tech Stack Overview

### Language & Frameworks
- **Core Language:** Python 3.12+
- **GUI Framework:** `customtkinter` (A dark-mode native, hardware-accelerated wrapper over standard `tkinter`).
- **Data Persistence:** `sqlite3` (Built-in lightweight SQL database for tracking historical crashes and system events).
- **Compilation/Packaging:** `PyInstaller` (Translates the Python logic and assets into a portable, standalone `.exe` without requiring users to install Python).

### Key External Libraries
- **`psutil` (Process & System Utilities):** The backbone for measuring live hardware telemetry (CPU frequencies, RAM consumption, Disk IO, Network Bandwidth) and iterating over running system applications.
- **`google-genai`:** The official SDK connecting the local application to the Gemini API cloud backend.
- **`wmi` (Windows Management Instrumentation):** The native Windows API used for deep hardware queries (fetching core temperatures, SMART hard drive firmware health, and critical Event Log crashes).
- **`send2trash`:** Safe file deletion API used in the Drive Analyzer to move large files to the Recycle Bin rather than permanently deleting them.

---

## 2. Software Architecture

TechGuardAI follows a heavily decoupled, modular architecture separated into three major layers: **Core (Backend)**, **AI (Intelligence)**, and **UI (Frontend)**.

### A. The Core Modules (`/core`)
This layer handles direct OS communication. No GUI logic exists here.
* **`system_monitor.py`:** A continuously running class that scrapes PC vitals (CPU, RAM, Top Processes). It caches results briefly (`_STATS_CACHE_TTL`) to prevent GIL (Global Interpreter Lock) thread stagnation.
* **`cleaner.py` / `disk_analyzer.py`:** Crawls specific Windows temp directories (`AppData\Local\Temp`, `Windows\Prefetch`) and uses `os.walk` to categorize files over customizable byte thresholds.
* **`startup_manager.py`:** Interacts directly with `winreg` (Windows Registry API) to read and manipulate the `HKEY_LOCAL_MACHINE` and `HKEY_CURRENT_USER` `\Run` keys. 
* **`network_privacy.py`:** Combines `psutil.net_connections()` with Python's native `socket.gethostbyaddr` to translate raw active IP sockets into human-readable domain names. It also toggles Windows Telemetry via known registry blocking keys.
* **`event_log_miner.py`:** Parses deep Microsoft Event Viewer logs to extract critical error codes and app crashes from the last 24 hours.

### B. The AI Brain (`/ai`)
The intelligence layer acts as the bridge between the Core variables and the user.
* **`bot_brain.py` (TechGuardBrain):** Responsible for constructing the massive Prompt Context. Every time the user asks a question, this class silently injects a vast "System Snapshot" (containing current CPU/RAM, Event Log crashes, SMART drive health, and active processes). 
* **Action Routing (`[ACTION:...]`):** The AI is programmed with specific callback triggers. If the AI detects a user trying to optimize their network, it returns `[ACTION: OPEN_PRO_TOOLS]`. The frontend intercepts this string, removes it from the chat bubble, and executes a Python function to swap the screen for the user dynamically.

### C. The Frontend GUI (`/ui`)
A multi-threaded, non-blocking interface.
* **Frame Switching:** Instead of opening multiple OS windows, `main.py` utilizes a Master Window routing system. It destroys and grids `CTkFrames` dynamically inside a main column to switch between the 5 Master Categories (Dashboard, Cleanup Center, Performance, Security, Fixes & Updates).
* **Cross-Thread Event Marshalling:** To solve UI freezing over long tasks (e.g., fetching network sockets), heavy functions are pushed to `threading.Thread(target=...)`. When the thread completes its work, it passes the data back to the `mainloop` safely using Tkinter’s GUI event queue: `self.after(0, lambda: render_ui_function(data))`.

---

## 3. Notable "Pro" Features Explained

### 1-Click Optimize Automation
Located on the Dashboard, this feature utilizes a Daemon Thread to execute a chain of system scripts invisibly:
1. Spawns `subprocess.Popen("ipconfig /flushdns")` to clear stale network routing files.
2. Invokes the `SystemCleaner` algorithm to purge `<24hr` old temp caches without deleting active software handles.

### Thermal Throttle & SMART Diagnostics
Instead of basic logic, `diagnostics_screen.py` uses WMI to query `MSAcpi_ThermalZoneTemperature`. It checks if the current heat is approaching `CriticalTripPoint`. For drives, it queries `MSStorageDriver_FailurePredictStatus` to determine if a hard disk's internal firmware predicts a mechanical failure is imminent.

### The App Updater (`winget` Wrapper)
The `software_updater.py` avoids building a custom package manager. Instead, it creates a silent headless subprocess mapping into Microsoft's native `winget` tool. It parses the CLI output to extract App IDs, Current Versions, and Available Versions, returning them as a JSON-like Python dictionary for the UI to map.

---

## 4. Design Patterns Used

1. **Singleton Pattern (Service Locator):** Instances of `SystemMonitor` and `TechGuardBrain` are initialized once in `main.py` and passed down to every screen frame via dependency injection.
2. **Observer/Callback Pattern:** The `utils.mode_manager` tracks whether the user is in "Beginner" or "Expert" mode. UI screens register callbacks (`mode_manager.register_callback(function)`) so they magically re-render themselves without a hard refresh when the mode is switched.
3. **Thread-Worker Model:** Deep scans run entirely decoupled from the main processor loop, avoiding "Program Not Responding" crashes.

---

## 5. System Requirements Specification (SRS)

### Functional Requirements
These define the specific behaviors, features, and capabilities the system must perform:
1. **Context-Aware AI Chatbot:** The system must integrate a generative AI that dynamically reads live system hardware states and provides context-aware troubleshooting advice.
2. **Real-time Telemetry:** The app must passively monitor and display CPU, Memory, Disk, Network Speed, and Top Running Processes.
3. **Automated Maintenance (1-Click Optimize):** The system must allow users to clear temporary files, flush DNS caches, and empty the recycle bin in a single interaction.
4. **Hardware Diagnostics:** The app must query hardware to detect Thermal Throttling, SMART Drive Failure predictions, and Windows Event Log system crashes.
5. **Security & Privacy Controls:** The logic must permit users to identify suspicious processes, view active outbound connection mappings, and safely toggle Windows Telemetry metrics off via the registry.
6. **Software Management:** The system must scan for outdated third-party applications using `winget` and allow one-click background updating.
7. **Process & Startup Control:** Users must be able to view, kill, and disable applications that consume high memory or launch automatically at PC boot.
8. **Dual-Mode UX:** The GUI must support an instant toggle separating "Expert Mode" (PIDs, IP Addresses, MBs) from "Beginner Mode" (translates tech jargon into 'Heavy/Light', plain domains, and simplified names).

### Non-Functional Requirements
These define the quality, performance, and architectural constraints of the system:
1. **Performance & Responsiveness:** Complex scans (Network mapping, Process memory iterating) must execute in `< 3.0` seconds, and must utilize asynchronous background `Daemon Threads` to ensure the GUI rendering loop never drops frames or freezes.
2. **Stability / Thread-Safety:** Background thread data must be safely pushed across memory queues using `Tkinter.after()` event marshalling to absolutely prevent race conditions or cross-thread UI crashes (`RuntimeError: main thread not in main loop`).
3. **Usability (UX/UI):** The interface must utilize a modern, dark-themed, 5-category tabbed environment (`customtkinter`) that mitigates cognitive overload for non-technical users. 
4. **Portability & Deployment:** The entire Python ecosystem, AI libraries, and UI assets must be packaged into a single standalone Windows executable (`.exe`) via PyInstaller, requiring zero terminal setup or Python installation on the target host PC.
5. **Security & Privilege Handling:** The system must gracefully degrade. If the app is launched without Administrator privileges, features that require deep registry write access (like Telemetry Toggles) must disable themselves and notify the user safely, rather than crashing.
