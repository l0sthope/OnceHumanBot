# Once Human Discord Timer Bot

A Discord bot for **Once Human** that tracks server phases, special unlocks, loot resets, and weekly commissions.

The bot maintains one permanent Discord timer panel that automatically updates every minute.

## Features

- 🌎 Manibus scenario tracking
- ❄️ The Way of Winter scenario tracking
- ⏳ Automatic phase countdowns
- 🔥 Pro Prime Wars unlock timer
- ☠️ Nightmare Silos unlock timer
- 📦 Loot Reset every 4 hours
- 📅 Weekly Commission Reset
- 🕐 Discord timestamps that display in each viewer's local timezone
- 💾 Saves settings between restarts
- 🔄 Updates the existing panel instead of sending new messages

## Installation

**1. Install Python 3.12 or newer.**

**2. Download or clone this repository.**

**3. Install the required packages:**

```bash
pip install -r requirements.txt
```

**4. Create a `.env` file** in the bot folder:

```env
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN
```

Get your token from the [Discord Developer Portal](https://discord.com/developers/applications).

Never share or upload your real bot token.

**5. Start the bot:**

```bash
python bot.py
```

## Discord Commands

| Command | Description |
|---|---|
| `/timers` | Privately view the current timers |
| `/setup_timers` | Create the permanent timer panel |
| `/setup_scenario` | Choose Manibus or The Way of Winter and calibrate the current phase |
| `/setup_weekly` | Set the weekly commission reset countdown |

Commands that change settings require the **Manage Server** permission.

## Scenario Presets

### Manibus

| Phase | Duration |
|---|---|
| Phase 1 | 5 days |
| Phase 2 | 5 days |
| Phase 3 | 14 days |
| Phase 4 | 16 days |

Pro Prime Wars and Nightmare Silos unlock on server Day 15.

### The Way of Winter

| Phase | Duration |
|---|---|
| Phase 1 | 8 days |
| Phase 2 | 7 days |
| Phase 3 | 8 days |
| Phase 4 | Open-ended |

## Setting Up the Bot

Invite your bot to your Discord server with the required permissions to view channels, send messages, embed links, and read message history.

Run `/setup_timers` in the channel where you want the permanent timer panel.

Then run `/setup_scenario` and select your scenario. Enter the current phase and the time remaining until the next phase.

Run `/setup_weekly` and enter the current in-game countdown until the next commission reset.

The bot will automatically maintain the countdowns afterward.

## Important Files

- `bot.py` — Main bot code
- `requirements.txt` — Python dependencies
- `.env.example` — Example token configuration
- `.gitignore` — Excludes private and temporary files
- `config.json` — Automatically saved local server settings (not uploaded)
- `.env` — Private Discord token (not uploaded)

## Notes

The bot must remain running to update the Discord panel. It can run on a spare laptop, home computer, or hosting service.

This is a fan-made project and is not officially affiliated with Once Human or its developers.