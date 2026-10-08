import os
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv


# ============================================================
# ONCE HUMAN SERVER TIMER BOT
# ============================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CONFIG_FILE = "config.json"

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN was not found in your .env file."
    )

EASTERN = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


# ============================================================
# BOT SETUP
# ============================================================

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# CONFIG
# ============================================================

config = {
    "timer_channel_id": None,
    "timer_message_id": None,

    "scenario": None,
    "server_start": None,

    "weekly_reset": None
}


def load_config():
    global config

    if not os.path.exists(CONFIG_FILE):
        print("No config.json found yet.")
        return

    try:
        with open(CONFIG_FILE, "r") as file:
            saved = json.load(file)

        # This lets old config files continue working.
        for key in config:
            if key in saved:
                config[key] = saved[key]

        print("Saved configuration loaded.")

    except Exception as error:
        print(f"Could not load config: {error}")


def save_config():
    try:
        with open(CONFIG_FILE, "w") as file:
            json.dump(config, file, indent=4)

        print("Configuration saved.")

    except Exception as error:
        print(f"Could not save config: {error}")


load_config()


# ============================================================
# SCENARIO PRESETS
# ============================================================

SCENARIOS = {
    "manibus": {
        "name": "Manibus",

        # Length of each phase in days.
        "phases": [
            5,   # Phase 1
            5,   # Phase 2
            14,  # Phase 3
            16   # Phase 4
        ]
    },

    "winter": {
        "name": "The Way of Winter",

        # Phase 4 is open-ended.
        "phases": [
            8,   # Phase 1
            7,   # Phase 2
            8    # Phase 3
        ]
    }
}


# ============================================================
# DATE HELPERS
# ============================================================

def utc_now():
    return datetime.now(UTC)


def datetime_to_string(value):
    return value.astimezone(UTC).isoformat()


def string_to_datetime(value):
    if not value:
        return None

    return datetime.fromisoformat(value).astimezone(UTC)


def discord_timestamp(value):
    return int(value.timestamp())


# ============================================================
# COUNTDOWN
# ============================================================

def countdown(target):
    now = utc_now()

    remaining = target - now

    total_seconds = max(
        0,
        int(remaining.total_seconds())
    )

    days = total_seconds // 86400

    hours = (
        total_seconds % 86400
    ) // 3600

    minutes = (
        total_seconds % 3600
    ) // 60

    if days > 0:
        return f"{days}d {hours}h {minutes}m"

    if hours > 0:
        return f"{hours}h {minutes}m"

    return f"{minutes}m"


# ============================================================
# LOOT RESET
#
# This is the same schedule that was already working.
# ============================================================

def next_loot_reset():
    now = datetime.now(EASTERN)

    reset_hours = [
        0,
        4,
        8,
        12,
        16,
        20
    ]

    for hour in reset_hours:
        reset = now.replace(
            hour=hour,
            minute=0,
            second=0,
            microsecond=0
        )

        if reset > now:
            return reset.astimezone(UTC)

    tomorrow = now + timedelta(days=1)

    reset = tomorrow.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    return reset.astimezone(UTC)


# ============================================================
# WEEKLY COMMISSION RESET
# ============================================================

def next_weekly_reset():
    saved_reset = string_to_datetime(
        config.get("weekly_reset")
    )

    if saved_reset is None:
        return None

    now = utc_now()

    # Keep adding 7 days until the reset
    # is in the future.
    while saved_reset <= now:
        saved_reset += timedelta(days=7)

    # If we advanced it, save the new target.
    new_value = datetime_to_string(saved_reset)

    if config.get("weekly_reset") != new_value:
        config["weekly_reset"] = new_value
        save_config()

    return saved_reset


# ============================================================
# SCENARIO CALCULATIONS
# ============================================================

def get_scenario_info():
    scenario_key = config.get("scenario")

    if not scenario_key:
        return None

    if scenario_key not in SCENARIOS:
        return None

    server_start = string_to_datetime(
        config.get("server_start")
    )

    if server_start is None:
        return None

    now = utc_now()

    preset = SCENARIOS[scenario_key]

    elapsed = now - server_start

    elapsed_seconds = elapsed.total_seconds()

    if elapsed_seconds < 0:
        return {
            "scenario": preset["name"],
            "phase": 1,
            "server_start": server_start,
            "not_started": True
        }

    elapsed_days = (
        elapsed_seconds / 86400
    )

    running_days = 0

    for index, phase_length in enumerate(
        preset["phases"]
    ):
        phase_number = index + 1

        phase_start_days = running_days
        phase_end_days = (
            running_days + phase_length
        )

        if elapsed_days < phase_end_days:

            phase_start = (
                server_start
                + timedelta(days=phase_start_days)
            )

            phase_end = (
                server_start
                + timedelta(days=phase_end_days)
            )

            return {
                "scenario": preset["name"],
                "phase": phase_number,
                "phase_start": phase_start,
                "phase_end": phase_end,
                "server_start": server_start,
                "final_phase": False
            }

        running_days += phase_length

    # Way of Winter Phase 4 is open-ended.
    if scenario_key == "winter":

        phase_start = (
            server_start
            + timedelta(days=running_days)
        )

        return {
            "scenario": preset["name"],
            "phase": 4,
            "phase_start": phase_start,
            "phase_end": None,
            "server_start": server_start,
            "final_phase": True
        }

    # Manibus after Phase 4.
    return {
        "scenario": preset["name"],
        "phase": 4,
        "phase_start": (
            server_start
            + timedelta(days=24)
        ),
        "phase_end": None,
        "server_start": server_start,
        "final_phase": True
    }


# ============================================================
# MANIBUS UNLOCKS
# ============================================================

def get_manibus_unlocks(server_start):
    unlock_time = (
        server_start
        + timedelta(days=15)
    )

    now = utc_now()

    if now >= unlock_time:
        return {
            "unlocked": True,
            "time": unlock_time
        }

    return {
        "unlocked": False,
        "time": unlock_time
    }


# ============================================================
# TIMER PANEL
# ============================================================

def create_timer_embed():
    scenario_info = get_scenario_info()

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    if scenario_info:
        title = (
            f"🌎 {scenario_info['scenario']} "
            f"— Phase {scenario_info['phase']}"
        )
    else:
        title = "🌎 Once Human Server Timers"

    embed = discord.Embed(
        title=title,
        color=discord.Color.from_rgb(
            0,
            220,
            180
        )
    )

    # --------------------------------------------------------
    # SCENARIO
    # --------------------------------------------------------

    if scenario_info:

        if scenario_info.get("not_started"):

            start = scenario_info["server_start"]

            embed.add_field(
                name="🚀 Server Opens",
                value=(
                    f"⏳ **{countdown(start)}**\n"
                    f"🕐 <t:{discord_timestamp(start)}:F>"
                ),
                inline=False
            )

        elif scenario_info["final_phase"]:

            embed.add_field(
                name="🏁 Current Phase",
                value=(
                    f"**Phase {scenario_info['phase']}**\n"
                    "Final / open-ended phase"
                ),
                inline=False
            )

        else:

            phase_end = scenario_info["phase_end"]

            next_phase = (
                scenario_info["phase"] + 1
            )

            embed.add_field(
                name=f"⏳ Phase {next_phase} Opens",
                value=(
                    f"**{countdown(phase_end)}**\n"
                    f"🕐 <t:{discord_timestamp(phase_end)}:F>"
                ),
                inline=False
            )

        # ----------------------------------------------------
        # MANIBUS SPECIAL UNLOCKS
        # ----------------------------------------------------

        if config.get("scenario") == "manibus":

            unlock = get_manibus_unlocks(
                scenario_info["server_start"]
            )

            if unlock["unlocked"]:

                embed.add_field(
                    name="🔥 Pro Prime Wars",
                    value="✅ **Unlocked**",
                    inline=True
                )

                embed.add_field(
                    name="☠️ Nightmare Silos",
                    value="✅ **Unlocked**",
                    inline=True
                )

            else:

                unlock_time = unlock["time"]

                embed.add_field(
                    name="🔥 Pro Prime Wars",
                    value=(
                        f"⏳ **{countdown(unlock_time)}**\n"
                        f"<t:{discord_timestamp(unlock_time)}:F>"
                    ),
                    inline=True
                )

                embed.add_field(
                    name="☠️ Nightmare Silos",
                    value=(
                        f"⏳ **{countdown(unlock_time)}**\n"
                        f"<t:{discord_timestamp(unlock_time)}:F>"
                    ),
                    inline=True
                )

    else:

        embed.description = (
            "No scenario has been configured yet.\n"
            "Use **/setup_scenario** to configure the server."
        )

    # --------------------------------------------------------
    # LOOT RESET
    # --------------------------------------------------------

    loot_time = next_loot_reset()

    embed.add_field(
        name="📦 Loot Reset",
        value=(
            f"⏳ **{countdown(loot_time)}**\n"
            f"🕐 <t:{discord_timestamp(loot_time)}:F>"
        ),
        inline=False
    )

    # --------------------------------------------------------
    # WEEKLY / COMMISSIONS
    # --------------------------------------------------------

    weekly_time = next_weekly_reset()

    if weekly_time:

        embed.add_field(
            name="📅 Weekly Reset / Commissions",
            value=(
                f"⏳ **{countdown(weekly_time)}**\n"
                f"🕐 <t:{discord_timestamp(weekly_time)}:F>\n"
                "♻️ Every 7 days"
            ),
            inline=False
        )

    else:

        embed.add_field(
            name="📅 Weekly Reset / Commissions",
            value=(
                "⚠️ Not calibrated yet\n"
                "Use **/setup_weekly**"
            ),
            inline=False
        )

    embed.set_footer(
        text=(
            "Once Human Server Timer • "
            "Updates every minute"
        )
    )

    return embed


# ============================================================
# UPDATE EXISTING PERMANENT PANEL
# ============================================================

async def refresh_panel():
    channel_id = config.get(
        "timer_channel_id"
    )

    message_id = config.get(
        "timer_message_id"
    )

    if not channel_id or not message_id:
        return False

    try:
        channel = bot.get_channel(channel_id)

        if channel is None:
            channel = await bot.fetch_channel(
                channel_id
            )

        message = await channel.fetch_message(
            message_id
        )

        await message.edit(
            embed=create_timer_embed()
        )

        return True

    except discord.NotFound:
        print(
            "Saved timer panel could not be found."
        )

        config["timer_channel_id"] = None
        config["timer_message_id"] = None

        save_config()

        return False

    except Exception as error:
        print(
            f"Panel refresh error: {error}"
        )

        return False


# ============================================================
# AUTOMATIC UPDATER
# ============================================================

@tasks.loop(minutes=1)
async def update_timer_panel():

    updated = await refresh_panel()

    if updated:
        print("Timer panel updated.")


@update_timer_panel.before_loop
async def before_timer_update():
    await bot.wait_until_ready()


# ============================================================
# BOT READY
# ============================================================

@bot.event
async def on_ready():

    print()
    print("======================================")
    print("       ONCE HUMAN TIMER BOT")
    print("======================================")
    print(f"Logged in as: {bot.user}")
    print("Status: ONLINE")

    if (
        config.get("timer_channel_id")
        and config.get("timer_message_id")
    ):
        print("Permanent timer panel: FOUND")
    else:
        print("Permanent timer panel: NOT SET")

    if config.get("scenario"):
        print(
            f"Scenario: {config['scenario']}"
        )
    else:
        print("Scenario: NOT SET")

    print("======================================")

    try:
        synced = await bot.tree.sync()

        print(
            f"Synced {len(synced)} "
            "slash command(s)."
        )

    except Exception as error:
        print(
            f"Command sync error: {error}"
        )

    if not update_timer_panel.is_running():

        update_timer_panel.start()

        print(
            "Automatic timer updater started."
        )


# ============================================================
# /TIMERS
# ============================================================

@bot.tree.command(
    name="timers",
    description="View the Once Human server timers."
)
async def timers(
    interaction: discord.Interaction
):

    await interaction.response.send_message(
        embed=create_timer_embed(),
        ephemeral=True
    )


# ============================================================
# /SETUP_TIMERS
#
# Creates the permanent panel.
# You normally only need this once.
# ============================================================

@bot.tree.command(
    name="setup_timers",
    description="Create the permanent timer panel."
)
async def setup_timers(
    interaction: discord.Interaction
):

    if not interaction.user.guild_permissions.manage_guild:

        await interaction.response.send_message(
            "❌ You need **Manage Server** "
            "permission.",
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        "⏱️ Creating the permanent timer panel...",
        ephemeral=True
    )

    message = await interaction.channel.send(
        embed=create_timer_embed()
    )

    config["timer_channel_id"] = (
        interaction.channel.id
    )

    config["timer_message_id"] = (
        message.id
    )

    save_config()

    print(
        "Permanent timer panel created."
    )


# ============================================================
# SCENARIO SETUP MODAL
# ============================================================

class ScenarioSetupModal(
    discord.ui.Modal,
    title="Set Current Server"
):

    phase = discord.ui.TextInput(
        label="Current Phase",
        placeholder="Example: 3",
        required=True,
        max_length=1
    )

    days = discord.ui.TextInput(
        label="Days until next phase",
        placeholder="Example: 10",
        required=True,
        max_length=3
    )

    hours = discord.ui.TextInput(
        label="Hours until next phase",
        placeholder="Example: 18",
        required=True,
        max_length=2
    )

    minutes = discord.ui.TextInput(
        label="Minutes until next phase",
        placeholder="Example: 50",
        required=True,
        max_length=2
    )

    def __init__(self, scenario_key):
        super().__init__()

        self.scenario_key = scenario_key

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        try:
            phase = int(self.phase.value)
            days = int(self.days.value)
            hours = int(self.hours.value)
            minutes = int(self.minutes.value)

        except ValueError:

            await interaction.response.send_message(
                "❌ Please use numbers only.",
                ephemeral=True
            )

            return

        if hours < 0 or hours > 23:
            await interaction.response.send_message(
                "❌ Hours must be between 0 and 23.",
                ephemeral=True
            )
            return

        if minutes < 0 or minutes > 59:
            await interaction.response.send_message(
                "❌ Minutes must be between 0 and 59.",
                ephemeral=True
            )
            return

        preset = SCENARIOS[
            self.scenario_key
        ]

        phase_lengths = preset["phases"]

        if (
            phase < 1
            or phase > len(phase_lengths)
        ):

            await interaction.response.send_message(
                "❌ That phase number does not "
                "match this scenario preset.",
                ephemeral=True
            )

            return

        # How much time remains in the
        # current phase.
        remaining = timedelta(
            days=days,
            hours=hours,
            minutes=minutes
        )

        phase_end = (
            utc_now() + remaining
        )

        current_phase_length = timedelta(
            days=phase_lengths[phase - 1]
        )

        phase_start = (
            phase_end
            - current_phase_length
        )

        # Add all previous phase lengths
        # to determine how far the current
        # phase is from server opening.
        previous_days = sum(
            phase_lengths[:phase - 1]
        )

        server_start = (
            phase_start
            - timedelta(
                days=previous_days
            )
        )

        config["scenario"] = (
            self.scenario_key
        )

        config["server_start"] = (
            datetime_to_string(
                server_start
            )
        )

        save_config()

        await refresh_panel()

        await interaction.response.send_message(
            (
                f"✅ **{preset['name']}** configured.\n"
                f"Current Phase: **{phase}**\n"
                f"Next phase in: "
                f"**{days}d {hours}h {minutes}m**"
            ),
            ephemeral=True
        )


# ============================================================
# SCENARIO BUTTONS
# ============================================================

class ScenarioSelectView(
    discord.ui.View
):

    def __init__(self):
        super().__init__(
            timeout=120
        )

    @discord.ui.button(
        label="Manibus",
        emoji="🌎",
        style=discord.ButtonStyle.primary
    )
    async def manibus(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            ScenarioSetupModal(
                "manibus"
            )
        )

    @discord.ui.button(
        label="The Way of Winter",
        emoji="❄️",
        style=discord.ButtonStyle.primary
    )
    async def winter(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            ScenarioSetupModal(
                "winter"
            )
        )


# ============================================================
# /SETUP_SCENARIO
# ============================================================

@bot.tree.command(
    name="setup_scenario",
    description="Set the current Once Human scenario."
)
async def setup_scenario(
    interaction: discord.Interaction
):

    if not interaction.user.guild_permissions.manage_guild:

        await interaction.response.send_message(
            "❌ You need **Manage Server** "
            "permission.",
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        (
            "**Choose your current "
            "Once Human scenario:**"
        ),
        view=ScenarioSelectView(),
        ephemeral=True
    )


# ============================================================
# WEEKLY RESET MODAL
# ============================================================

class WeeklySetupModal(
    discord.ui.Modal,
    title="Weekly Commission Reset"
):

    days = discord.ui.TextInput(
        label="Days remaining",
        placeholder="Example: 0",
        required=True,
        max_length=2
    )

    hours = discord.ui.TextInput(
        label="Hours remaining",
        placeholder="Example: 18",
        required=True,
        max_length=2
    )

    minutes = discord.ui.TextInput(
        label="Minutes remaining",
        placeholder="Example: 48",
        required=True,
        max_length=2
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        try:
            days = int(self.days.value)
            hours = int(self.hours.value)
            minutes = int(self.minutes.value)

        except ValueError:

            await interaction.response.send_message(
                "❌ Please use numbers only.",
                ephemeral=True
            )

            return

        if days < 0:
            await interaction.response.send_message(
                "❌ Days cannot be negative.",
                ephemeral=True
            )
            return

        if hours < 0 or hours > 23:
            await interaction.response.send_message(
                "❌ Hours must be between 0 and 23.",
                ephemeral=True
            )
            return

        if minutes < 0 or minutes > 59:
            await interaction.response.send_message(
                "❌ Minutes must be between 0 and 59.",
                ephemeral=True
            )
            return

        reset_time = (
            utc_now()
            + timedelta(
                days=days,
                hours=hours,
                minutes=minutes
            )
        )

        config["weekly_reset"] = (
            datetime_to_string(
                reset_time
            )
        )

        save_config()

        await refresh_panel()

        await interaction.response.send_message(
            (
                "✅ Weekly commissions configured.\n"
                f"Next reset in "
                f"**{days}d {hours}h {minutes}m**.\n"
                "After that it will automatically "
                "repeat every 7 days."
            ),
            ephemeral=True
        )


# ============================================================
# /SETUP_WEEKLY
# ============================================================

@bot.tree.command(
    name="setup_weekly",
    description="Calibrate the weekly commission reset."
)
async def setup_weekly(
    interaction: discord.Interaction
):

    if not interaction.user.guild_permissions.manage_guild:

        await interaction.response.send_message(
            "❌ You need **Manage Server** "
            "permission.",
            ephemeral=True
        )

        return

    await interaction.response.send_modal(
        WeeklySetupModal()
    )


# ============================================================
# START BOT
# ============================================================

bot.run(TOKEN)