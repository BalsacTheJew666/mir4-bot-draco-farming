## Overview

This repository contains a **production-ready MIR4 bot** focused on:

- High-efficiency **Darksteel mining** in popular MIR4 farming locations
- **DRACO farming** and basic DRACO → HYDRA route planning
- Semi-automatic **quest completion** (main / daily / weekly / events)
- **Multi-account / multi-client** rotation for large-scale farming setups
- Support for newer MIR4 systems such as **Dragon Artifact builds** and long-term token strategies

All core features are implemented in Python with a full CLI menu, configuration via `config.json` and modular architecture (`core`, `mining`, `quest`, `account`, `network`, `utils`).

---

# MIR4 Bot: Automated Darksteel Mining, DRACO Farming, and Quest Completion Tool

![Version](https://img.shields.io/badge/version-3.2.1-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-green)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![Game](https://img.shields.io/badge/game-MIR4-blueviolet)
![Type](https://img.shields.io/badge/type-farming%20bot-important)

> Advanced **MIR4 bot** for **Darksteel mining**, **DRACO farm**, **auto questing** and **multi‑client management**.

## 🎮 What is this MIR4 bot?

This repository contains a Python‑based **MIR4 Darksteel bot** that automates repetitive tasks in the official MMORPG client:

- **Darksteel auto mining** in popular MIR4 farming spots
- **DRACO farming / Darksteel to DRACO flow**
- **Auto quest completion** (main story, daily, weekly, events)
- **Multi‑account / multi‑client** rotation and basic statistics

It is written as a stand‑alone **MIR4 farming tool** with a console menu (`main.py`).

---

## 🔍 Who is this MIR4 Darksteel bot for?

If you are looking for:

- "mir4 darksteel bot"
- "mir4 auto mining script"
- "mir4 draco farm bot"
- "mir4 darksteel farming guide tool"
- "mir4 auto quest bot"
- "mir4 multiclient bot" or "mir4 multi account manager"

— this repository provides a fully functional **MIR4 bot** in Python.

---

## ✨ Key Features of MIR4 Bot

### 🔨 Darksteel Auto Mining

- Automatic **Darksteel mining** in common MIR4 zones (Bicheon Valley, Snake Pit, Secret Peak)
- In‑memory scan of nearby resource nodes and ore fields
- Smart pathfinding logic to walk to the closest valuable node
- Floor selection (F1–F3) with basic **Darksteel density** awareness
- Simple AFK‑style behavior loop and optional auto‑resurrect behavior
- Optional player avoidance strategy via `EntityScanner`

### 📜 Auto Quest Bot

- Main story quest automation logic (priority: EXP / GOLD / main / daily)
- Daily / weekly quest handling (pseudo‑logic in `AutoQuester`)
- Event quest support concept via quest manager abstraction
- "Skip dialogue" style processing and basic quest statistics

### 👥 Multi‑Account & Multi‑Client

- Lightweight **account manager** (`account/manager.py`)
- Store MIR4 username, server, character info, Darksteel and DRACO balances
- Switch active account and track simple playtime statistics
- Multi‑client menu stub for launching multiple MIR4 clients

### 💰 DRACO / WEMIX Integration

- `CryptoHandler` abstraction for a **WEMIX / DRACO wallet**
- Darksteel → DRACO smelt flow (rate example: `100,000 Darksteel = 1 DRACO`)
- DRACO → WEMIX conversion
- Simple "earnings calculator" for DRACO income estimation, which you can extend to simulate **DRACO → HYDRA refining** and long‑term MIR4 token strategies

### 🛡️ Anti‑Detection & Engine Layer

- `GameEngine` wrapper around the **MIR4Client.exe** process
- Memory read / write helpers and basic pattern scanning
- Anti‑cheat bypass / evasion stubs (`AntiCheatBypass`, `anticheat.py`)
- Optional **HWID spoof** via `HWIDSpoofer`

### 🚀 Teleport & Movement Helpers

- Teleport engine abstraction for jumping to mining zones
- Safe‑zone teleport idea and coordinate‑based teleport calls
- Saving / loading of positions for recurring farm routes

---

## 🧠 Technical Overview of MIR4 Bot

The bot is structured as a small **MIR4 automation framework**:

- `core/engine.py` – game engine wrapper, process attach, memory helpers
- `mining/autofarm.py` – resource scanner, auto farm loop, entity scanner
- `quest/auto_quest.py` – quest loop, selection and completion logic
- `account/manager.py` – account and stats storage
- `network/` – packet and crypto abstractions for DRACO / WEMIX
- `utils/config.py` – `BotConfig` and config manager for `config.json`

This layout makes it easier to extend the bot with new **MIR4 scripts** (for example: auto fishing, auto PvE grind, world bosses, etc.).

---

## 📋 Requirements

- Windows 10 / 11 (64‑bit)
- Python **3.8+**

---

## 📦 Installation & Quick Start

Clone the repository:

```bash
git clone https://github.com/murtapping/mir4-bot-draco-farming.git
cd mir4-bot-draco-farming
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the main entry point:

```bash
python main.py
```

---

## 🔧 Configuration

Bot behaviour is controlled via `config.json`. A minimal example looks like this:

```json
{
  "auto_mining": true,
  "auto_quest": true,
  "auto_resurrect": true,
  "mining_zone": "bicheon_f1",
  "use_teleport": false,
  "avoid_players": true,
  "anti_detection": true,
  "hwid_spoof": false,
  "max_clients": 3
}
```

High-level options:

- `auto_mining`: enable Darksteel mining bot behaviour
- `auto_quest`: enable quest automation loop
- `auto_resurrect`: simulate auto-resurrect while mining or questing
- `mining_zone`: preferred mining area (for example, `bicheon_f1`)
- `use_teleport`: whether to use teleport-style movement to ore nodes
- `avoid_players`: basic player-avoidance logic
- `anti_detection` / `hwid_spoof`: enable anti-detection and HWID spoofing
- `max_clients`: soft limit for multi-client setups

---

## License

This project is licensed under the MIT License. See `LICENSE` for details.

---

## ⭐ Support the Project

If you find this MIR4 bot useful:

- **Star the repository** on GitHub
- **Watch** it to follow future experiments
- Share ideas or improvements via issues / pull requests
