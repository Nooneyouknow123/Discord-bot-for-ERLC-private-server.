import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from datetime import datetime, timedelta, timezone

# ---------- CONSTANTS ----------
DB_FILE = "loa_requests.db"
MODS_FILE = "Roles/mods.txt"              # staff who can request LOA
HIGHRANK_FILE = "Roles/highrank.txt"      # staff who can approve/deny
LOA_CHANNEL_ID = 1051891408136568862
LOA_ROLE_ID = 1051277740495618068         # role given on approval

# ---------- HELPERS ----------
def read_id_file(path: str):
    try:
        with open(path, "r") as f:
            return [int(line.strip()) for line in f if line.strip().isdigit()]
    except FileNotFoundError:
        return []

def format_dt(ts: int):
    return f"<t:{ts}:F>"  # Discord timestamp

def parse_duration(duration: str):
    """Convert 5D / 2W / 1M → start_ts, end_ts"""
    duration = duration.upper().strip()
    now = datetime.now(tz=timezone.utc)

    if duration.endswith("D") and duration[:-1].isdigit():
        end = now + timedelta(days=int(duration[:-1]))
    elif duration.endswith("W") and duration[:-1].isdigit():
        end = now + timedelta(weeks=int(duration[:-1]))
    elif duration.endswith("M") and duration[:-1].isdigit():
        end = now + timedelta(days=int(duration[:-1]) * 30)  # approx months
    else:
        return None

    return int(now.timestamp()), int(end.timestamp())

# ---------- DATABASE ----------
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS loa_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            start_ts INTEGER NOT NULL,
            end_ts INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            approver_id INTEGER,
            created_ts INTEGER NOT NULL
        )
        """)

def add_request(user_id: int, reason: str, start_ts: int, end_ts: int):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO loa_requests (user_id, reason, start_ts, end_ts, status, created_ts) VALUES (?,?,?,?,?,?)",
            (user_id, reason, start_ts, end_ts, "Pending", int(datetime.now(tz=timezone.utc).timestamp()))
        )
        return cur.lastrowid

def set_request_status(req_id: int, status: str, approver_id: int | None):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("UPDATE loa_requests SET status = ?, approver_id = ? WHERE id = ?", (status, approver_id, req_id))

def get_request(req_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        return conn.execute("SELECT * FROM loa_requests WHERE id = ?", (req_id,)).fetchone()

def get_active_or_pending_request(user_id: int):
    now_ts = int(datetime.now(tz=timezone.utc).timestamp())
    with sqlite3.connect(DB_FILE) as conn:
        return conn.execute("""
        SELECT id, user_id, reason, start_ts, end_ts, status
        FROM loa_requests
        WHERE user_id = ? AND (status = 'Pending' OR (status = 'Approved' AND end_ts > ?))
        ORDER BY created_ts DESC LIMIT 1
        """, (user_id, now_ts)).fetchone()

def get_past_loas_count(user_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM loa_requests WHERE user_id = ? AND status = 'Approved'", (user_id,)
        ).fetchone()[0]

def get_history_for_user(user_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        return conn.execute("""
        SELECT id, reason, start_ts, end_ts, status, approver_id, created_ts
        FROM loa_requests WHERE user_id = ? ORDER BY created_ts DESC
        """, (user_id,)).fetchall()

# ---------- BUTTONS ----------
class ApproveDenyView(discord.ui.View):
    def __init__(self, req_id: int, target_id: int):
        super().__init__(timeout=None)
        self.req_id = req_id
        self.target_id = target_id

    async def _has_permission(self, interaction):
        return any(r.id in read_id_file(HIGHRANK_FILE) for r in interaction.user.roles)

    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._has_permission(interaction):
            return await interaction.response.send_message("You are not allowed to approve LOAs.", ephemeral=True)

        set_request_status(self.req_id, "Approved", interaction.user.id)
        req = get_request(self.req_id)
        user = interaction.guild.get_member(req[1])

        if user and (role := interaction.guild.get_role(LOA_ROLE_ID)):
            await user.add_roles(role)

        embed = discord.Embed(title="Las Vegas Roleplay\nLOA Request", color=discord.Color.green())
        embed.add_field(
            name="📄 Staff Information",
            value=f"Staff Member: {user.mention if user else req[1]}\n"
                  f"Top Role: {user.top_role.mention if user else 'N/A'}\n"
                  f"Past LOAs: {get_past_loas_count(req[1])}\nShift Time: 0s",
            inline=False
        )
        embed.add_field(
            name="🎫 Request Information",
            value=f"Reason: {req[2]}\nStarts: {format_dt(req[3])}\nEnds: {format_dt(req[4])}",
            inline=False
        )
        embed.add_field(name="📝 Approved By", value=interaction.user.mention, inline=False)

        await interaction.message.delete()
        await interaction.channel.send(content=user.mention if user else "", embed=embed)

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._has_permission(interaction):
            return await interaction.response.send_message("You are not allowed to deny LOAs.", ephemeral=True)

        set_request_status(self.req_id, "Denied", interaction.user.id)
        req = get_request(self.req_id)
        user = interaction.guild.get_member(req[1])

        embed = discord.Embed(title="Las Vegas Roleplay\nLOA Request", color=discord.Color.red())
        embed.add_field(
            name="📄 Staff Information",
            value=f"Staff Member: {user.mention if user else req[1]}\n"
                  f"Top Role: {user.top_role.mention if user else 'N/A'}\n"
                  f"Past LOAs: {get_past_loas_count(req[1])}\nShift Time: 0s",
            inline=False
        )
        embed.add_field(
            name="🎫 Request Information",
            value=f"Reason: {req[2]}\nStarts: {format_dt(req[3])}\nEnds: {format_dt(req[4])}",
            inline=False
        )
        embed.add_field(name="📝 Denied By", value=interaction.user.mention, inline=False)

        await interaction.message.delete()
        await interaction.channel.send(content=user.mention if user else "", embed=embed)

# ---------- HISTORY PAGER ----------
class HistoryPager(discord.ui.View):
    def __init__(self, interaction, rows):
        super().__init__(timeout=None)
        self.rows = rows
        self.page = 0
        self.interaction = interaction

    def make_embed(self):
        if not self.rows:
            return discord.Embed(title="LOA History", description="No LOAs found.")
        r = self.rows[self.page]
        approver = self.interaction.guild.get_member(r[5])
        embed = discord.Embed(title=f"LOA History • Page {self.page + 1}/{len(self.rows)}")
        embed.add_field(name="Reason", value=r[1], inline=False)
        embed.add_field(name="Starts", value=format_dt(r[2]), inline=True)
        embed.add_field(name="Ends", value=format_dt(r[3]), inline=True)
        embed.add_field(name="Status", value=r[4], inline=True)
        embed.add_field(name="Approved/Denied By", value=approver.mention if approver else "N/A", inline=False)
        return embed

    @discord.ui.button(label="⬅️ Prev", style=discord.ButtonStyle.gray)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < len(self.rows) - 1:
            self.page += 1
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

# ---------- COG ----------
class LOACog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_db()

    @app_commands.command(name="loa_request", description="Request an LOA")
    @app_commands.describe(reason="Reason (required)", duration="Duration like 5D, 2W, 1M")
    async def loa_request(self, interaction: discord.Interaction, reason: str, duration: str):
        if not any(r.id in read_id_file(MODS_FILE) for r in interaction.user.roles):
            return await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)

        parsed = parse_duration(duration)
        if not parsed:
            return await interaction.response.send_message("Invalid duration format. Use 5D / 2W / 1M.", ephemeral=True)

        start_ts, end_ts = parsed
        existing = get_active_or_pending_request(interaction.user.id)
        if existing:
            _, _, _, _, e_ts, status = existing
            if status == "Pending":
                return await interaction.response.send_message("You already have a pending LOA request.", ephemeral=True)
            if status == "Approved" and e_ts > int(datetime.now(tz=timezone.utc).timestamp()):
                return await interaction.response.send_message("You are already on LOA — wait until it ends.", ephemeral=True)

        req_id = add_request(interaction.user.id, reason.strip(), start_ts, end_ts)

        embed = discord.Embed(title="Las Vegas Roleplay\nLOA Request", color=discord.Color.blurple())
        embed.add_field(
            name="📄 Staff Information",
            value=f"Staff Member: {interaction.user.mention}\n"
                  f"Top Role: {interaction.user.top_role.mention if interaction.user.top_role else 'N/A'}\n"
                  f"Past LOAs: {get_past_loas_count(interaction.user.id)}\nShift Time: 0s",
            inline=False
        )
        embed.add_field(
            name="🎫 Request Information",
            value=f"Reason: {reason}\nStarts: {format_dt(start_ts)}\nEnds: {format_dt(end_ts)}",
            inline=False
        )
        embed.add_field(name="📝 Approved By", value="Pending...", inline=False)
        embed.set_footer(text=f"Request ID: {req_id}")

        if (channel := interaction.guild.get_channel(LOA_CHANNEL_ID)):
            await channel.send(
                content=interaction.user.mention,
                embed=embed,
                view=ApproveDenyView(req_id, interaction.user.id)
            )

        await interaction.response.send_message("Your LOA request has been submitted.", ephemeral=True)

    @app_commands.command(name="loa_history", description="View LOA history of a staff member")
    async def loa_history(self, interaction: discord.Interaction, member: discord.Member):
        if not any(r.id in read_id_file(HIGHRANK_FILE) for r in interaction.user.roles):
            return await interaction.response.send_message("You are not allowed to view LOA history.", ephemeral=True)

        rows = get_history_for_user(member.id)
        pager = HistoryPager(interaction, rows)
        await interaction.response.send_message(embed=pager.make_embed(), view=pager, ephemeral=True)

async def setup(bot):
    await bot.add_cog(LOACog(bot))