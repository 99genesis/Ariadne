<div align="center">

# ARIADNE OSINT FRAMEWORK
**Next-Generation Terminal Intelligence Platform & Cybernetic Knowledge Graph Engine**

[![Version](https://img.shields.io/badge/Version-1.0.0-00ffff?style=for-the-badge)](https://github.com/99genesis/Ariadne)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Obsidian Required](https://img.shields.io/badge/Obsidian-v1.4.0%2B_Required-7A367B?style=for-the-badge&logo=obsidian)](https://obsidian.md/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-333333?style=for-the-badge)]()
[![License](https://img.shields.io/badge/License-MIT-00FF66?style=for-the-badge)]()

*Engineered by **99genesis***

</div>

---

## ⚡ Overview

**Ariadne** is an enterprise-grade, asynchronous Open Source Intelligence (OSINT) reconnaissance framework designed specifically for cybersecurity researchers, threat intelligence analysts, and digital forensics investigators.

While traditional OSINT tools dump raw, fragmented output into transient console logs or static CSV/PDF spreadsheets, Ariadne operates as a **Cybernetic Knowledge Graph Engine**. Every piece of intelligence discovered across social networks, domain infrastructures, visual media, and geolocation footprints is dynamically normalized into structured **Obsidian Markdown Notes** (`.md`). These notes are enriched with strict YAML frontmatter metadata and `[[Double Bracket]]` relational links, transforming your investigation into an interconnected, living intelligence graph.

---

## 💎 Core Architectural Highlights

* **🔒 Clean Architecture & SOLID Engineering:**
  * Built from the ground up utilizing strict separation of concerns, Dependency Injection (`DI Container`), and protocol-driven interfaces. Inner domain models and execution pipelines remain completely independent of external providers, CLI presentation mechanisms, and storage engines.

* **🔌 Zero-Dependency Plugin Ecosystem:**
  * Modular, plug-and-play intelligence pipeline (`Discovery ➔ Loader ➔ Registry ➔ Manager ➔ Execution Pipeline`). New OSINT vectors and correlation modules can be dropped into the ecosystem without modifying core framework mechanics.

* **🗄️ Hybrid Indexing Engine (SQLite + Markdown Single Source of Truth):**
  * To eliminate latency during large-scale investigations, Ariadne runs a background asynchronous watchdog (`notes.db`) that indexes structured attributes across all target workspaces. High-speed executive queries (`target info`) complete in milliseconds via SQLite, while markdown files inside your vault remain the permanent, human-readable single source of truth.

* **⚡ High-Speed Asynchronous & Event-Driven Core:**
  * Powered by `asyncio` and `aiohttp` for non-blocking, highly concurrent multi-vector network scanning. An asynchronous Pub/Sub **Event Bus** decouples live reconnaissance from disk IO, ensuring background database indexing and markdown serialization never freeze the interactive terminal.

* **🧠 Multi-Tier AI Provider & Fallback Synthesis:**
  * Dynamic discovery and fallback execution across leading AI engines (**Google Gemini Studio**, **OpenAI GPT-4o**, **OpenRouter**, and local **Ollama** models). If an API rate limit or CDN timeout occurs, the system automatically cascades through fallback models to synthesize threat assessments, risk scorecards, and executive summaries seamlessly.

* **🛡️ Two-Tier Caching & Masked Audit Logging:**
  * Incorporates an ultra-fast in-memory L1 cache combined with a persistent, TTL-driven L2 disk cache (`cache_manager`) to eliminate redundant API requests. Furthermore, the rotating logger automatically sanitizes and masks sensitive API tokens before writing diagnostic logs (`storage/logger.py`).

---

## 🔍 Comprehensive Intelligence Vectors

* **👤 Username & Social Graph Reconnaissance (`username`):**
  * Deep enumeration and verification across decentralized networks, developer platforms, gaming hubs, and technical forums (including GitHub, GitLab, DockerHub, PyPI, npm, Steam, HackerNews, Mastodon, Telegram, Twitter/X, Reddit, Instagram, TikTok, Technopat, DonanımArşivi, and more).
  * Includes an **Intelligent Alias Mutation Engine** that generates cross-platform username variations (`endann` ➔ `end_ann`, `Austin123` ➔ `Austin_123`) to uncover hidden secondary accounts.

* **🖼️ Visual & EXIF Adli Bilişim (Forensics) (`image`):**
  * Extracts precise EXIF metadata, camera hardware models, exposure metrics, embedded GPS coordinates, and calculates perceptual hashes (`dhash`) to detect duplicate or modified imagery.
  * Integrates multi-cloud Vision AI models to perform environmental scene recognition, optical character recognition (OCR), and geolocation clue extraction from raw photos.

* **🌐 Network, DNS & Infrastructure Mapping (`domain`, `ip`):**
  * Comprehensive WHOIS lookups, DNS record enumeration (`A`, `MX`, `TXT`, `NS`), IP geolocation tracking, ISP identification, and ASN mapping to chart target digital infrastructure.

* **📍 Spatial GEO-INT & District Guessing (`geo`):**
  * Analyzes spatial coordinates and executes a 4-Tier hierarchical district and administrative zone prediction (`district_guess`), mapping raw coordinates directly to localized intelligence profiles.

* **🗂️ Multi-Target Case Management (`target`):**
  * Complete workspace isolation. Create dedicated target cases (`Targets/<Target_Name>/Vault`), switch active investigation contexts on the fly, and view rich executive summaries via the `target info` dashboard.

---

## 🖥️ System Requirements

* **Operating System:** Windows 10/11, Linux (Debian/Ubuntu/Arch/RHEL), or macOS
* **Python Runtime:** Python `3.10`, `3.11`, or `3.12`
* **Knowledge Graph Visualization:** [Obsidian Desktop (`v1.4.0` or higher required)](https://obsidian.md/)
  * *Why Obsidian `v1.4.0+` is Required:* Ariadne uses modern YAML frontmatter schemas (`identity`, `tags`, `aliases`, `provenance`) and advanced double-bracket correlation links (`[[IDENTITY_CORRELATION_...]]`, `[[DOMAIN_...]]`, `[[GEO_...]]`). Obsidian `v1.4.0+` is required to properly parse these attributes into filterable canvas groups and dynamic graph nodes.
* **Network:** Active internet connection for live OSINT querying and provider API resolution

---

## 📦 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/99genesis/Ariadne.git
cd Ariadne
```

### 2. Create an Isolated Virtual Environment (Recommended)
```bash
# On Windows (PowerShell / CMD)
python -m venv venv
venv\Scripts\activate

# On Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Core Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Initial Configuration & Setup Wizard
Launch Ariadne for the first time. The framework will automatically invoke its interactive terminal setup wizard (`setup`) to configure your preferred interface language (`English`, `Turkish`, `Russian`, `Chinese`), primary workspace path (`Ariadne_Workspace`), and optional AI keys:
```bash
python main.py
```

---

## 🚀 Usage Guide & Terminal Operations

Ariadne operates seamlessly in both **Continuous Interactive REPL Shell** and **Direct Command Line Execution** modes.

### Interactive REPL Terminal
Launch the full interactive cybernetic terminal (`ariadne [Workspace] >`) with dynamic status rendering, ASCII splash screens, and TAB auto-completion:
```bash
python main.py
```

Inside the interactive REPL prompt:
```text
ariadne [Ariadne_Workspace] > help
ariadne [Ariadne_Workspace] > target create Investigation_Alpha
ariadne [Ariadne_Workspace] > target switch Investigation_Alpha
ariadne [Ariadne_Workspace] > username torvalds
ariadne [Ariadne_Workspace] > domain github.com
ariadne [Ariadne_Workspace] > image C:/Evidence/sample_exif.jpg
ariadne [Ariadne_Workspace] > target info Investigation_Alpha
```

### Direct CLI One-Shot Execution
Execute automated investigations right from your standard system command line without entering the interactive loop:
```bash
# Run multi-vector username discovery against a handle
python main.py username torvalds

# Run network reconnaissance on a target domain
python main.py domain discord.gg

# Extract EXIF and AI visual reconnaissance from an image
python main.py image C:/Evidence/sample_exif.jpg

# Display real-time executive dashboard for an active case
python main.py target info Investigation_Alpha
```

---

## 📋 Command Reference

| Command | Module Description | Example Usage |
| :--- | :--- | :--- |
| `username` | Enumerate accounts across social, developer, forum, and gaming networks | `username <handle>` |
| `domain` | Perform DNS enumeration, WHOIS lookups, and network mapping | `domain <example.com>` |
| `ip` | Trace IP geolocation, ISP data, ASN, and routing footprints | `ip <8.8.8.8>` |
| `phone` | Analyze telephone numbers, carrier registration, and line status | `phone <+90542...>` |
| `email` | Check email data breaches, domain MX records, and social links | `email <target@domain.com>` |
| `image` | Extract EXIF, camera hardware info, dhash, and visual AI clues | `image <path_to_image>` |
| `geo` | Perform coordinate geolocation intelligence and district mapping | `geo <lat,long>` |
| `profile` | Synthesize comprehensive multi-vector profile report via AI | `profile <target_name>` |
| `target` | Manage multi-target workspaces (`create`, `switch`, `list`, `info`) | `target info <name>` |
| `setup` | Launch interactive setup wizard for API keys and language selection | `setup` |
| `help` | Display interactive terminal manual and parameter breakdowns | `help <command>` |

---

## 🌐 Obsidian Knowledge Graph Integration (`v1.4.0+ Required`)

Ariadne is explicitly architected to act as the backend engine for your **Obsidian Second Brain**. Every scan automatically outputs structured markdown notes directly into your active target's vault (`Targets/<Target_Name>/Vault/`).

### How to Visualize Your Intelligence Graph:
1. Download and install **[Obsidian Desktop (`v1.4.0` or higher)](https://obsidian.md/)**.
2. Open Obsidian and select **"Open folder as vault"**.
3. Choose your local Ariadne workspace directory (`Ariadne_Workspace/`) generated by the framework.
4. Press `Ctrl+G` (Windows/Linux) or `Cmd+G` (macOS) inside Obsidian to open the **Graph View**.
5. Watch dynamically as all discovered usernames, domains, IP addresses, EXIF data points, and AI synthesized threat profiles cluster together via double brackets (`[[IDENTITY_CORRELATION_torvalds]]`, `[[DOMAIN_github.com]]`), revealing hidden links and cross-platform identities instantly.

---

## 📦 Building Standalone Executable (`build.bat` / `build.sh`)

Ariadne includes automated, one-click build engines to compile the entire framework into a portable, zero-dependency standalone binary across all major operating systems (`Windows`, `Linux`, `macOS`).

### Automatic Dependency & Library Installation (`Zero-Preinstall Requirement`):
You do **not** need to manually install dependencies or compilers before building. Even on a fresh operating system installation where required libraries (`requirements.txt`) and `PyInstaller` are completely missing, our build engine automatically verifies, downloads, and installs all necessary packages before initiating the compilation pipeline:

```cmd
# Windows (PowerShell / CMD) — Compiles dist\Ariadne.exe with custom icon (ariadne.ico)
.\build.bat

# Linux / macOS — Compiles standalone binary dist/Ariadne
chmod +x build.sh
./build.sh
```
Once the automated pipeline finishes, your portable standalone executable (featuring the custom `ariadne.ico` icon) will be generated inside:
```text
dist/Ariadne.exe   (Windows)
dist/Ariadne       (Linux / macOS)
```

---

## 🔒 Security & Privacy Architecture

* **Zero Cloud Telemetry & Local Isolation:** All target databases (`notes.db`), intelligence cache tiers, API interaction logs, and markdown vaults reside strictly on your local filesystem (`Ariadne_Workspace/`). Ariadne never transmits telemetry or investigation logs to external third-party servers.
* **Operating System Credential Vault Protection (`OSSecretsManager`):** Ariadne enforces zero plaintext API key storage. All AI Studio (`Google Gemini`, `OpenAI`, `OpenRouter`) and provider API tokens entered during setup are encrypted and stored directly inside your native operating system credential vault (**Windows Credential Manager** / **macOS Keychain** via `keyring`). Neither local configuration files (`config.json`) nor exported markdown notes will ever expose your private credentials.

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

<div align="center">
  <sub>Built with precision by <b>99genesis</b> for threat intelligence and cybersecurity operations.</sub>
</div>
