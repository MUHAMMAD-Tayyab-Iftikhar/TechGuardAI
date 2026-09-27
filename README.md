# TechGuardAI ⚡
> **AI-Powered Windows System Optimization & Diagnostics Platform**

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![UI Framework](https://img.shields.io/badge/GUI-CustomTkinter-2980b9.svg)](https://customtkinter.tomschimansky.com/)
[![AI Engine](https://img.shields.io/badge/AI-Google%20Gemini%20API-orange.svg?logo=google)](https://ai.google.dev/)
[![Auth](https://img.shields.io/badge/Auth-Firebase%20Authentication-FFCA28.svg?logo=firebase&logoColor=black)](https://firebase.google.com/)
[![Database](https://img.shields.io/badge/Database-SQLite-003B57.svg?logo=sqlite)](https://www.sqlite.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6.svg?logo=windows)](https://www.microsoft.com/windows)

---

## 📌 Overview

**TechGuardAI** is a desktop application engineered to monitor, diagnose, and optimize Windows systems. By combining native Windows system hooks (`psutil`, `WMI`, Windows Event Logs) with the **Google Gemini AI Engine**, TechGuardAI delivers real-time health metrics, automated diagnostics, proactive system maintenance, and intelligent troubleshooting assistance.

---

## ✨ Features

- 📊 **Real-Time System Health:** Live telemetry for CPU, RAM, Disk, and Network usage.
- 🤖 **AI Diagnostics & Assistant:** Integrated Gemini AI chatbot providing context-aware troubleshooting and optimization recommendations.
- 🧹 **System Cleanup Center:** Safe automated cleaning for temporary files, cache, and system junk.
- 🛡️ **Security Audit & Process Analyzer:** Detection of high-resource or suspicious background processes and administrative privileges.
- 💾 **Drive Space Analyzer:** Visual scan and detection of large files eating up disk capacity.
- 🚀 **Startup Application Management:** Audit and control software launching at Windows boot.
- 🔐 **Firebase Cloud Authentication:** Secure login, account creation, and password reset flows with email verification.
- 🗄️ **Local Telemetry & Event History:** Persistent SQLite database storing performance logs and diagnostic history.

---

## 👨‍💻 Key Contributions

- **Modern Desktop Interface:** Developed the multi-screen dark-theme UI with responsive cards and tabbed navigation using **CustomTkinter**.
- **System Telemetry & Diagnostics:** Engineered real-time hardware telemetry and health monitoring using **psutil**, **WMI**, and Windows Event Log mining.
- **AI Chatbot Integration:** Integrated the **Google Gemini API** into an interactive assistant that analyzes real-time system snapshots.
- **Authentication & Security:** Implemented user authentication workflows (login, registration, password recovery) backed by **Firebase Auth**.
- **Persistent Data Layer:** Structured an embedded **SQLite** database (`techguard_telemetry.db`) to record metrics, diagnostic logs, and scan history.
- **Packaging & Distribution:** Configured **PyInstaller** specifications (`TechGuardAI.spec`) and automated batch build scripts (`build.bat`) for one-click standalone executable generation.

---

## 📸 Screenshots

| 📊 System Dashboard | 🤖 AI Diagnostics |
|:---:|:---:|
| ![Dashboard](screenshots/dashboard.png) | ![AI Diagnostics](screenshots/ai_diagnostics.png) |

| 🛡️ Security Audit | 🧹 System Cleanup |
|:---:|:---:|
| ![Security Audit](screenshots/security_audit.png) | ![System Cleanup](screenshots/system_cleanup.png) |

> *Tip: Place your screenshots inside the [`screenshots/`](screenshots/) directory using the filenames above.*

---

## 🏗️ Architecture & Project Structure

```
TechGuardAI/
├── main.py                  # Main application entry point
├── build.bat                # Automated PyInstaller build script
├── TechGuardAI.spec         # PyInstaller build specification
├── requirements.txt         # Project dependencies
├── .env.example             # Template for API keys
├── .gitignore               # Ignored files (secrets, builds, temp databases)
├── auth/                    # Firebase authentication modules
│   └── firebase_auth.py
├── ai/                      # Gemini AI engine and prompts
│   ├── chatbot_engine.py
│   └── health_analyzer.py
├── core/                    # System monitors, cleaners, and analyzers
│   ├── system_monitor.py
│   ├── cleaner.py
│   ├── disk_analyzer.py
│   ├── drive_health.py
│   ├── event_log_miner.py
│   ├── fix_library.py
│   └── suspicious_process.py
├── ui/                      # CustomTkinter interface screens
│   ├── auth_screen.py
│   ├── home_screen.py
│   ├── dashboard.py
│   ├── chatbot_ui.py
│   ├── cleaner_screen.py
│   ├── security_screen.py
│   └── styles.py
├── utils/                   # Helpers and Windows admin checks
│   └── admin_check.py
└── screenshots/             # Repository preview images
```

---

## 🚀 Getting Started (How to Run)

### 1. Prerequisites
- **Operating System:** Windows 10 or Windows 11
- **Python:** Python 3.10, 3.11, or 3.12 ([Download Python](https://www.python.org/downloads/))
- **Google Gemini API Key:** Free key available from [Google AI Studio](https://aistudio.google.com/app/apikey)

### 2. Clone the Repository
```bash
git clone https://github.com/<your-username>/TechGuardAI.git
cd TechGuardAI
```

### 3. Create a Virtual Environment (Recommended)
```bash
python -m venv venv
venv\Scripts\activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure API Key
Create a `.env` file in the root folder (or copy from `.env.example`):
```bash
copy .env.example .env
```
Open `.env` and insert your Gemini API key:
```ini
GEMINI_API_KEY=your_actual_api_key_here
```

### 6. Run the Application
```bash
python main.py
```

---

## 📦 Building the Standalone Executable (.exe)

To build a standalone `.exe` that non-technical users can run without installing Python:

```cmd
build.bat
```

The output will be placed inside `dist/TechGuardAI/`. Users can launch the app directly by double-clicking `TechGuardAI.exe`.

---

## 📄 License
This project is developed as an academic and open-source system optimization tool.
