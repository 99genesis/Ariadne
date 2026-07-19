<div align="center">

# ARIADNE OSINT FRAMEWORK
**Next-Generation Terminal Intelligence Platform & Cybernetic Knowledge Graph Engine**

[![Version](https://img.shields.io/badge/Version-1.0.0-00ffff?style=for-the-badge)](https://github.com/99genesis/ariadne)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-333333?style=for-the-badge)]()
[![Knowledge Base](https://img.shields.io/badge/Graph-Obsidian%20Compatible-7A367B?style=for-the-badge&logo=obsidian)](https://obsidian.md/)
[![License](https://img.shields.io/badge/License-MIT-00FF66?style=for-the-badge)]()

*Engineered by **99genesis***

</div>

---

## ⚡ Overview

**Ariadne** is an enterprise-grade, asynchronous Open Source Intelligence (OSINT) terminal framework designed for cybersecurity researchers, threat intelligence analysts, and digital forensics investigators. 

Unlike traditional OSINT tools that generate isolated static reports or messy spreadsheet exports, Ariadne transforms raw intelligence data into a **Living Cybernetic Knowledge Graph**. Every username, telephone number, domain name, EXIF metadata tag, and cross-platform alias discovered during an investigation is dynamically synthesized into structured markdown notes enriched with YAML frontmatter and `[[Double Bracket]]` relational links—ready for instant visualization inside **Obsidian**.

---

## 🎯 Key Capabilities

* **🔍 Multi-Vector Target Reconnaissance:**
  * **Username & Profile Intelligence:** Real-time account verification across decentralized networks (Mastodon, HackerNews, Telegram, GitHub, Steam, Reddit, Twitter/X, Instagram, TikTok, and more).
  * **Image & Media Forensics:** Deep EXIF extraction, perceptual hash calculation, metadata geo-tagging, and AI-powered visual analysis.
  * **Network Reconnaissance:** DNS record enumeration, WHOIS lookups, IP geolocation tracking, and infrastructure mapping.
  * **Alias & Mutation Engine:** Advanced cross-platform username mutation (`endann` ➔ `end_ann`, `Austin123` ➔ `Austin_123`) to uncover hidden secondary identities.

* **🧠 AI-Powered Intelligence Synthesis:**
  * Integrates seamlessly with multi-tier AI providers (Google Gemini Studio, OpenAI GPT-4o, OpenRouter, and local Ollama models) to generate executive summaries, threat assessments, and risk scorecards from raw reconnaissance data.

* **🗂️ Multi-Target Workspace Isolation:**
  * Conduct multiple parallel investigations without data contamination. Each target gets a dedicated investigation vault (`Targets/<Target_Name>/Vault`), dedicated SQLite indexing database (`notes.db`), and isolated two-tier cache.

* **📊 Executive Terminal Dashboard (`target info`):**
  * View real-time intelligence breakdowns right from the command line, featuring confidence-rated findings tables, entity distributions, top tags, and master briefing reports.

* **🛡️ Operating System Credential Vault:**
  * Zero plaintext API key storage. All API tokens and sensitive credentials are encrypted and stored directly inside your native OS Credential Store (Windows Credential Manager / macOS Keychain).

---

## 🛠️ System Requirements

* **Operating System:** Windows 10/11, Linux (Debian/Ubuntu/Arch), or macOS
* **Python:** Version `3.10` or higher
* **Network:** Active internet connection for live OSINT querying and API resolution
* **Optional:** [Obsidian](https://obsidian.md/) installed locally to view the generated relational graph

---

## 📦 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/99genesis/ariadne.git
cd ariadne
```

### 2. Create a Virtual Environment (Recommended)
```bash
# On Windows (PowerShell / CMD)
python -m venv venv
venv\Scripts\activate

# On Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Initial Configuration & Boot
Run the framework for the first time. Ariadne will launch an interactive setup wizard (`setup`) to configure your default language, primary workspace directory, and optional AI provider credentials:
```bash
python main.py
```

---

## 🚀 Usage Guide

Ariadne can be operated in two modes: **Interactive REPL Shell** or **Direct Command Line Execution**.

### Interactive Terminal Shell
To launch the continuous interactive environment (`ariadne [Workspace] >`), simply execute:
```bash
python main.py
```

Once inside the shell, you can execute commands seamlessly with TAB auto-completion:
```text
ariadne [Ariadne_Workspace] > help
ariadne [Ariadne_Workspace] > target create Operation_Blackout
ariadne [Ariadne_Workspace] > username northyuksel
ariadne [Ariadne_Workspace] > domain discord.gg/wessex
ariadne [Ariadne_Workspace] > target info Operation_Blackout
```

### Direct CLI One-Shot Execution
Execute specific intelligence modules directly from your system terminal without entering the interactive loop:
```bash
# Run username intelligence query against a specific handle
python main.py username torvalds

# Analyze an image file for EXIF data and AI reconnaissance
python main.py image C:/evidence/suspect_photo.jpg

# Switch active target workspace
python main.py target switch Operation_Blackout

# Display executive intelligence dashboard for target
python main.py target info Operation_Blackout
```

---

## 🖥️ Command Reference

| Command | Description | Example Usage |
| :--- | :--- | :--- |
| `username` | Enumerate social accounts, developer profiles, and aliases | `username <handle>` |
| `domain` | Perform DNS enumeration, WHOIS, and network analysis | `domain <example.com>` |
| `ip` | Trace IP geolocation, ISP data, and routing info | `ip <8.8.8.8>` |
| `phone` | Analyze telephone numbers, carrier, and line status | `phone <+90542...>` |
| `email` | Check email breaches, domain MX, and social links | `email <target@domain.com>` |
| `image` | Extract EXIF, perceptual hash, and visual AI intelligence | `image <path_to_image>` |
| `geo` | Perform coordinate geolocation intelligence | `geo <lat,long>` |
| `profile` | Synthesize comprehensive multi-vector profile report | `profile <target_name>` |
| `target` | Manage multi-target workspaces (`create`, `switch`, `list`, `info`) | `target info <name>` |
| `setup` | Launch configuration wizard for API keys and language | `setup` |
| `help` | Display terminal manual and parameter breakdowns | `help <command>` |

---

## 🌐 Obsidian Knowledge Graph Integration

Every time an investigation finishes, Ariadne prompts you with an **Interactive Review** in the terminal where you can select and export findings directly into your workspace vault.

### How Graph Linking Works:
1. When a finding (e.g., GitHub account `@northyuksel`) is saved, Ariadne generates a markdown note inside `Targets/<Target_Name>/Vault/Username_northyuksel/`.
2. Entities mentioned inside the note automatically receive double brackets (`[[IDENTITY_CORRELATION_northyuksel]]`, `[[DOMAIN_github.com]]`).
3. Open your workspace folder (`Ariadne_Workspace/`) inside **Obsidian** and press `Ctrl+G` (or `Cmd+G`) to view the interactive **Graph View**. You will see how entities, IP addresses, domains, and usernames cluster together dynamically across investigations.

---

## 🔒 Security & Privacy

* **Zero Cloud Telemetry:** All intelligence data, SQLite indexes (`notes.db`), and markdown vaults remain strictly on your local disk (`Ariadne_Workspace/`).
* **OS Credential Protection:** API keys (`Google AI Studio`, `OpenAI`, `OpenRouter`) are encrypted by the OS native credential store. Neither `config.json` nor any exported report will ever leak or store your private tokens in plaintext.

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

<div align="center">
  <sub>Built with precision for threat intelligence and cybersecurity operations.</sub>
</div>
