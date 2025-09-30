import os
import json
import time
import random
import string
import traceback
import sqlite3
import requests
import discord
from discord.ext import commands
from discord import app_commands
from discord.ext.commands import CommandNotFound
from discord.ui import View, Button
from dotenv import load_dotenv
from dadjokes import Dadjoke
from datetime import datetime, timedelta, timezone
import pyjokes
import asyncio

last_time_say = {}

# ------------------------------
# Logging Setup
# ------------------------------
def log_output(message: str, console_output=False):
    """Log messages to file and optionally to console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    # Always write to file
    with open("Misc/output.txt", "a", encoding="utf-8") as f:
        f.write(log_entry)
    
    # Optionally print to console
    if console_output:
        print(message)

# ------------------------------
# Load environment variables
# ------------------------------
load_dotenv("misc/.env")
DISCORD_TOKEN, ERLC_API_KEY, SERVER_URL = (
    os.getenv("DISCORD_TOKEN"),
    os.getenv("ERLC_API_KEY"),
    os.getenv("SERVER_URL"),
)

# ------------------------------
# Bot Configuration
# ------------------------------
intents = discord.Intents.default()
intents.message_content = intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------------
# File loading helpers
# ------------------------------
def load_roles_from_file(filename, default=None):
    try:
        with open(filename, "r") as f:
            return [int(line.strip()) for line in f if line.strip().isdigit()]
    except FileNotFoundError:
        log_output(f"Warning: {filename} not found. Using empty list.", False)
    except Exception as e:
        log_output(f"Error loading {filename}: {e}", False)
    return default or []

def load_lines(filename, fallback=None):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return fallback or []

# ------------------------------
# Configuration Loading
# ------------------------------
highrank        = load_roles_from_file("Roles/highrank.txt")
modadmin_roles  = load_roles_from_file("Roles/mods.txt")
promotionauth   = load_roles_from_file("promotion_related/promotionauth.txt")
promotables     = load_roles_from_file("promotion_related/promotableroles.txt")
infract_staff_roles = load_roles_from_file("infraction_stuff/infractstaff.txt")
infract_remove_roles = load_roles_from_file("infraction_stuff/infractremoveroles.txt")

bot_jokes       = load_lines("jokes/bot_jokes.txt", ["Error: Cannot open bot_jokes.txt"])
ping_messages   = load_lines("jokes/ping_messages.txt", ["Error: Cannot open ping_messages.txt"])
no_ping_messages= load_lines("jokes/no_ping_messages.txt", ["Error: Cannot open no_ping_messages.txt"])
file_jokes      = load_lines("jokes/random_jokes.txt", [])


# ------------------------------
# Error logging
# ------------------------------
def log_error(error: Exception, command_name: str = ""):
    error_time = datetime.now()
    with open("Misc/error_logger.txt", "a", encoding="utf-8") as f:
        f.write(f"\n--- {error_time} ---\n")
        if command_name:
            f.write(f"Command: {command_name}\n")
        f.write("".join(traceback.format_exception(type(error), error, error.__traceback__)))
        f.write("\n")

# ------------------------------
# Bot Events
# ------------------------------
@bot.event
async def on_ready():
    try:
        log_output(f"Bot initialized: {bot.user} (ID: {bot.user.id})")
        
        GUILD_ID = 1016748575289516122
        
        # Guild command synchronization
        guild = discord.Object(id=GUILD_ID)
        await bot.tree.sync(guild=guild)
        log_output("Guild slash commands synchronized")
        
        # Global command synchronization
        await bot.tree.sync()
        log_output("Global slash commands synchronized")
        
        # Command verification
        guild_commands = await bot.tree.fetch_commands(guild=guild)
        global_commands = await bot.tree.fetch_commands()
        
        log_output(f"Guild commands registered: {len(guild_commands)}")
        log_output(f"Global commands registered: {len(global_commands)}")
        
    except Exception as e:
        log_output(f"Error during initialization: {e}")
        log_error(e, "on_ready")

# ------------------------------
# Command Definitions
# ------------------------------
@bot.command()
async def ping(ctx):
    try:
        if not any(r.id in modadmin_roles for r in ctx.author.roles):
            return
        
        latency = round(bot.latency * 1000)
        embed = discord.Embed(
            title="System Status",
            description=f"Bot operational and responsive.\n**Latency:** {latency}ms",
            color=discord.Color.green(),
            timestamp=datetime.now()
        ).set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        
        msg = await ctx.send(embed=embed)
        await msg.delete(delay=20)
        
    except Exception as e:
        await ctx.send("Error processing command")
        log_error(e, "ping")

@bot.command()
async def game(ctx, cmd: str, username: str):
    try:
        if not any(role.id in highrank for role in ctx.author.roles):
            return await ctx.send("Insufficient permissions for this command")

        valid_cmds = ["bring", "kill", "refresh", "load", "heal"]
        if cmd.lower() not in valid_cmds:
            return await ctx.send("Invalid command specified")

        payload = {"command": f":{cmd} {username}"}
        headers = {
            "Authorization": ERLC_API_KEY,
            "Content-Type": "application/json"
        }

        response = requests.post(SERVER_URL + "/commands", headers=headers, json=payload)
        if response.status_code == 200:
            await ctx.send(f"Command executed: `:{cmd} {username}`")
        else:
            await ctx.send(f"Command execution failed (Error {response.status_code})")

    except Exception as e:
        await ctx.send("Error processing game command")
        log_error(e, "game")

@bot.command()
async def players(ctx):
    try:
        if not any(role.id in highrank for role in ctx.author.roles):
            return await ctx.send("Insufficient permissions for this command")

        headers = {"Authorization": ERLC_API_KEY, "Content-Type": "application/json"}
        response = requests.get(SERVER_URL + "/players", headers=headers)

        if response.status_code != 200:
            return await ctx.send(f"Failed to retrieve player data (Error {response.status_code})")

        players_data = response.json()
        teams = {"DOT": [], "FD": [], "Police": [], "Sheriff": [], "Civilian": []}

        for player in players_data.get("players", []):
            team = player.get("team", "Civilian")
            username = player.get("username", "Unknown")
            if team in teams:
                teams[team].append(username)
            else:
                teams["Civilian"].append(username)

        for team in teams:
            teams[team].sort()

        embed = discord.Embed(title="Active Players", color=discord.Color.blue())
        for team_name, members in teams.items():
            if members:
                embed.add_field(name=f"{team_name} Team", value="\n".join(members), inline=False)

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send("Error retrieving player information")
        log_error(e, "players")

@bot.command()
async def joke(ctx, member: discord.Member = None):
    try:
        if member == ctx.author:
            return await ctx.send(
                f"{ctx.author.mention} Self-referential commands are not supported",
                delete_after=10,
            )

        if member and member.id == bot.user.id:
            return await ctx.send(
                f"{ctx.author.mention} Command cannot target the bot",
                delete_after=10,
            )

        if member and member.id == 1274667778300706866:
            return await ctx.send(
                f"{ctx.author.mention} Restricted user targeting",
                delete_after=10,
            )

        # Bot interaction case
        if member and member.bot and member.id != bot.user.id:
            return await ctx.send(f"{member.mention} {random.choice(bot_jokes)}")

        # Permission verification
        if not any(role.id in modadmin_roles for role in ctx.author.roles):
            return

        # Rate limiting
        now = time.time()
           
        YOUR_USER_ID = 1274667778300706866

# Only apply rate limit if it's NOT you using !joke
        if ctx.command.name == "joke" and ctx.author.id == YOUR_USER_ID:
           pass
        else:
    # Normal rate limiting for everyone else (and for other commands)
          if ctx.author.id in last_time_say and now - last_time_say[ctx.author.id] < 300:
           await ctx.message.delete()
           return await ctx.send(f"{ctx.author.mention} Command rate limit exceeded", delete_after=5)
        last_time_say[ctx.author.id] = now

        # Member targeting
        if member:
            if member == ctx.guild.default_role:
                return await ctx.send("Mass mention not permitted", delete_after=5)
            if not ctx.channel.permissions_for(member).read_messages:
                return await ctx.send(f"{member.display_name} cannot access this channel", delete_after=5)
            message = pyjokes.get_joke() if random.choice([True, False]) else random.choice(ping_messages)
            return await ctx.send(f"{member.mention} {message}")

        # General joke
        message = pyjokes.get_joke() if random.choice([True, False]) else random.choice(no_ping_messages)
        await ctx.send(f"{message}")

    except discord.Forbidden:
        await ctx.send("Insufficient permissions for user mention", delete_after=5)
    except discord.HTTPException:
        await ctx.send("Message delivery failed", delete_after=5)
    except Exception as e:
        await ctx.send("Command execution error", delete_after=5)
        log_error(e, "joke")

@bot.command()
async def guide(ctx):
    if not any(role.id in modadmin_roles for role in ctx.author.roles):
        return

    try:
        pages_data = [
            {
                "title": "Command Reference • Page 1/4",
                "desc": "Prefix command documentation:",
                "color": discord.Color.blue(),
                "fields": [
                    ("!ping", "System status check\n**Usage:** `!ping`"),
                    ("!game <command> <username>", "Game command execution\n**Valid commands:** bring, kill, refresh, load, heal\n**Usage:** `!game bring JohnDoe`"),
                    ("!players", "Player roster display\n**Usage:** `!players`"),
                    ("!joke <@user>", "Interactive humor system\n**Usage:** `!joke @user` or `!joke`"),
                    ("!link", "Account verification system\n**Usage:** `!link`"),
                    ("!removelink <@member>", "Account linkage removal\n**Usage:** `!removelink @member`"),
                    ("!yesno <question>", "Decision support system\n**Usage:** `!yesno Is this operational?`"),
                    ("!reload <cog_name>", "System module management\n**Usage:** `!reload RoleManagement`")
                ]
            },
            {
                "title": "Command Reference • Page 2/4",
                "desc": "Role management commands:",
                "color": discord.Color.green(),
                "fields": [
                    ("/add_role <member> <role>", "Role assignment system\n**Usage:** `/add_role Username Role`"),
                    ("/remove_role <member> <role>", "Role removal system\n**Usage:** `/remove_role Username Role`"),
                    ("/promote <staff> <role>", "Staff promotion system\n**Usage:** `/promote @Staff Role`")
                ]
            },
            {
                "title": "Command Reference • Page 3/4",
                "desc": "Staff evaluation system:",
                "color": discord.Color.purple(),
                "fields": [
                    ("/review", "Performance feedback submission\n**Usage:** `/review staff:@Staff rating:3 feedback:'Performance review'`"),
                    ("/myreviews", "Personal review access\n**Usage:** `/myreviews`"),
                    ("/viewreview <staff>", "Staff review management\n**Usage:** `/viewreview staff:@Staff`"),
                    ("/deletereview <staff> <review_id>", "Review data management\n**Usage:** `/deletereview staff:@Staff review_id:1234567890`")
                ]
            },
            {
                "title": "Command Reference • Page 4/4",
                "desc": "Administrative systems:",
                "color": discord.Color.orange(),
                "fields": [
                    ("/infract <user> <type> <doc_link> <appealable>", "Infraction management\n**Types:** Warning, Strike, Suspension, Demotion, Termination, Blacklist\n**Usage:** `/infract @User Strike https://docs.google.com/... True`"),
                    ("/infraction_history <user>", "Infraction record access\n**Usage:** `/infraction_history @User`"),
                    ("/loa_request <reason> <duration>", "Leave management\n**Duration:** 5D, 2W, 1M\n**Usage:** `/loa_request Vacation 1W`"),
                    ("/loa_history <member>", "Leave history review\n**Usage:** `/loa_history @Staff`"),
                    ("!guide", "Command documentation\n**Usage:** `!guide`")
                ]
            }
        ]

        pages = []
        for p in pages_data:
            embed = discord.Embed(title=p["title"], description=p["desc"], color=p["color"])
            for name, value in p["fields"]:
                embed.add_field(name=name, value=value, inline=False)
            pages.append(embed)

        class GuidePagination(View):
            def __init__(self, pages):
                super().__init__(timeout=180)
                self.pages = pages
                self.index = 0

            @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
            async def back(self, interaction: discord.Interaction, button: Button):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("Session authentication failed", ephemeral=True)
                self.index = (self.index - 1) % len(self.pages)
                await interaction.response.edit_message(embed=self.pages[self.index], view=self)

            @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
            async def next(self, interaction: discord.Interaction, button: Button):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("Session authentication failed", ephemeral=True)
                self.index = (self.index + 1) % len(self.pages)
                await interaction.response.edit_message(embed=self.pages[self.index], view=self)

        await ctx.send(embed=pages[0], view=GuidePagination(pages))

    except Exception as e:
        await ctx.send("Guide system error")
        log_error(e, "guide")

# ------------------------------
# Database Systems
# ------------------------------
conn = sqlite3.connect("reviews.db")
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS reviews (
                id TEXT PRIMARY KEY,
                staff_id INTEGER,
                staff_name TEXT,
                reviewer_id INTEGER,
                reviewer_name TEXT,
                rating INTEGER,
                feedback TEXT
            )""")
conn.commit()

def generate_review_id():
    return "".join(random.choices(string.digits, k=16))

REVIEWER_ROLE_ID = 1158148745393868872

@bot.command()
async def link(ctx):
    try:
        if not any(r.id in modadmin_roles for r in ctx.author.roles):
            return await ctx.send("Insufficient permissions", delete_after=10)

        api_url = f"https://api.bloxlink/v4/public/guilds/1016748575289516122/discord-to-roblox/{ctx.author.id}"
        log_output(f"API Request: {api_url}", False)

        response = requests.get(api_url, timeout=10)
        log_output(f"API Response: {response.status_code}", False)
        
        if response.status_code != 200:
            return await ctx.send(f"API communication error: {response.status_code}", delete_after=10)

        data = response.json()
        if not data.get("status") or not data.get("robloxId"):
            return await ctx.send("Account verification required", delete_after=10)

        roblox_id, roblox_username = str(data["robloxId"]), data.get("robloxUsername", "Unknown")

        c.execute('''CREATE TABLE IF NOT EXISTS linked_accounts (
                        discord_id TEXT PRIMARY KEY,
                        roblox_id TEXT NOT NULL,
                        roblox_username TEXT NOT NULL)''')
        conn.commit()

        c.execute("SELECT discord_id FROM linked_accounts WHERE roblox_id=?", (roblox_id,))
        row = c.fetchone()
        if row and row[0] != str(ctx.author.id):
            return await ctx.send(f"Account already linked: {roblox_username}", delete_after=15)

        c.execute("INSERT OR REPLACE INTO linked_accounts VALUES (?, ?, ?)", (str(ctx.author.id), roblox_id, roblox_username))
        conn.commit()

        await ctx.send(f"Account linked: {roblox_username} ({roblox_id})", delete_after=15)

    except Exception as e:
        await ctx.send("Linking process error", delete_after=10)
        log_error(e, "link")

@bot.command()
async def removelink(ctx, member: discord.Member):
    try:
        if not any(r.id in highrank for r in ctx.author.roles):
            return await ctx.send("Insufficient permissions", delete_after=10)

        c.execute("SELECT roblox_username FROM linked_accounts WHERE discord_id=?", (str(member.id),))
        row = c.fetchone()
        if not row:
            return await ctx.send(f"No linked account: {member.display_name}", delete_after=10)

        c.execute("DELETE FROM linked_accounts WHERE discord_id=?", (str(member.id),))
        conn.commit()

        await ctx.send(f"Account unlinked: {member.display_name} from {row[0]}", delete_after=15)

    except Exception as e:
        await ctx.send("Unlinking process error", delete_after=10)
        log_error(e, "removelink")

# ------------------------------
# Automated Systems
# ------------------------------
TARGET_CHANNEL_ID = 1045896138953326763
last_jokes, MAX_HISTORY = [], 5

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.channel.id == TARGET_CHANNEL_ID and random.random() < 0.005:
        try:
            response = Dadjoke().joke if random.choice([True, False]) else (
                random.choice(file_jokes) if file_jokes else "Humor system offline"
            )

            attempts = 0
            while response in last_jokes and attempts < 10:
                response = Dadjoke().joke if random.choice([True, False]) else random.choice(file_jokes)
                attempts += 1

            await message.reply(response)

            last_jokes.append(response)
            if len(last_jokes) > MAX_HISTORY:
                last_jokes.pop(0)

        except Exception as e:
            log_error(e, "on_message")

    await bot.process_commands(message)

@bot.command(name="yesno")
@commands.cooldown(1, 300, commands.BucketType.user)
async def yes_or_no(ctx, *, question: str = None):
    if ctx.author.id == 1274667778300706866:
        ctx.command.reset_cooldown(ctx)

    responses = [
        "Yes.", "No.", "Affirmative.", "Negative.", "Maybe", "Confirmed.",
        "Unlikely.", "Certain.", "Re-evaluate."
    ]
    answer = random.choice(responses)

    if ctx.message.reference:
        try:
            replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            await ctx.send(
                f"Query: {replied_message.author.mention}: {replied_message.content}\nResponse: {answer}"
            )
        except discord.NotFound:
            await ctx.send(f"Reference resolution failed\nResponse: {answer}")
    else:
        if question:
            await ctx.send(f"Query: {ctx.author.mention}: {question}\nResponse: {answer}")
        else:
            await ctx.send(f"No query provided\nResponse: {answer}")

@yes_or_no.error
async def yes_or_no_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            f"Command cooldown active: {int(error.retry_after)}s remaining",
            delete_after=10
        )

# ------------------------------
# System Administration
# ------------------------------
DEVELOPER_IDS = [1274667778300706866]
COGS = [
    "RoleManagement",
    "ReviewSystem",
    "PromotionSystem",
    "InfractionSystem",
    "LOACog",
    "BanAppealSystem",
    "FileUploadMonitor",
    "Priority"
]

@bot.command(name="reload")
async def reload_cog(ctx, cog_name: str):
    if ctx.author.id not in DEVELOPER_IDS:
        return await ctx.send("Administrative authorization required")

    if cog_name not in COGS:
        return await ctx.send(f"Invalid system module: {cog_name}")

    try:
        await bot.unload_extension(f"cogs.{cog_name}")
        await bot.load_extension(f"cogs.{cog_name}")
        await ctx.send(f"Module reloaded: {cog_name}")

        GUILD_ID = 1016748575289516122
        guild = discord.Object(id=GUILD_ID)
        await bot.tree.sync(guild=guild)
        await ctx.send("Command synchronization complete")

    except commands.ExtensionNotFound:
        await ctx.send(f"Module not found: {cog_name}")
    except commands.ExtensionFailed as e:
        await ctx.send(f"Module reload failure: {cog_name}\n```{e}```")
    except Exception as e:
        await ctx.send(f"System error: {e}")




# ------------------------------
# System Initialization
# ------------------------------
async def main():
    log_output("System initialization started")
    
    loaded_count = 0
    for cog in COGS:
        try:
            await bot.load_extension(f"cogs.{cog}")
            log_output(f"Module loaded: {cog}")
            loaded_count += 1
        except Exception as e:
            log_output(f"Module load failure: {cog} - {e}")

    log_output(f"Modules loaded: {loaded_count}/{len(COGS)}")
    
    command_count = len(bot.tree.get_commands())
    log_output(f"Commands registered: {command_count}")
    
    log_output("System startup initiated")
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())








          






