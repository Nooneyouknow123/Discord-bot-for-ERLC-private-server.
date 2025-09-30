import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from datetime import datetime

DB_FILE = "infractions.db"
SUSPENSION_ROLE_ID = 1107840548263436389

class InfractionSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # These need to be passed from main.py or loaded differently
        from main import infract_staff_roles, infract_remove_roles  # Import from main file
        self.infract_staff_roles = infract_staff_roles
        self.infract_remove_roles = infract_remove_roles

        # Init DB
        self.conn = sqlite3.connect(DB_FILE)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS infractions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            moderator_id INTEGER,
            type TEXT,
            doc_link TEXT,
            appealable TEXT,
            timestamp TEXT
        )
        """)
        self.conn.commit()

    # ------------------------------
    # Autocomplete for type
    # ------------------------------
    async def type_autocomplete(self, interaction: discord.Interaction, current: str):
        types = ["Warning", "Strike", "Suspension", "Demotion", "Termination", "Blacklist"]
        return [
            app_commands.Choice(name=t, value=t)
            for t in types if current.lower() in t.lower()
        ][:25]

    # ------------------------------
    # /infract command
    # ------------------------------
    @app_commands.command(name="infract", description="Issue an infraction to a member")
    @app_commands.describe(
        user="Select the user to infract",
        type="Infraction type",
        doc_link="Document link (e.g. Google Doc, Drive, etc.)",
        appealable="Is this appealable? True/False"
    )
    @app_commands.autocomplete(type=type_autocomplete)
    async def infract(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        type: str,
        doc_link: str,
        appealable: str
    ):
        try:
            moderator = interaction.user
            guild = interaction.guild

            # Self-check
            if user.id == moderator.id:
                return await interaction.response.send_message("❌ You cannot infract yourself.", ephemeral=True)

            # Permission check
            if not any(r.id in self.infract_staff_roles for r in moderator.roles):
                return await interaction.response.send_message(
                    "❌ You are not authorized to issue infractions.", ephemeral=True
                )

            # Hierarchy check
            if user.top_role >= moderator.top_role:
                return await interaction.response.send_message(
                    "❌ You cannot infract someone with equal or higher role than you.", ephemeral=True
                )

            # Save to DB
            timestamp = datetime.now().isoformat()
            self.cursor.execute("""
                INSERT INTO infractions (user_id, moderator_id, type, doc_link, appealable, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user.id, moderator.id, type, doc_link, appealable, timestamp))
            self.conn.commit()

            # Role removals for Termination/Suspension
            if type in {"Termination", "Suspension"}:
                roles_to_remove = [
                    guild.get_role(rid) for rid in self.infract_remove_roles
                    if guild.get_role(rid) in user.roles
                ]
                if roles_to_remove:
                    await user.remove_roles(*roles_to_remove, reason=f"{type} infraction issued")

            # Add suspension role
            if type == "Suspension":
                suspension_role = guild.get_role(SUSPENSION_ROLE_ID)
                if suspension_role and suspension_role not in user.roles:
                    await user.add_roles(suspension_role, reason="Suspension infraction issued")

            # Embed
            embed = discord.Embed(
                title="Infraction Issued",
                description=f"**{type}** issued to {user.mention}",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Member", value=user.mention, inline=True)
            embed.add_field(name="Type", value=type, inline=True)
            embed.add_field(name="Document", value=f"[Click Here]({doc_link})", inline=True)
            embed.add_field(name="Appealable", value=appealable, inline=True)
            embed.add_field(name="Issued by", value=moderator.mention, inline=True)

            log_channel = guild.get_channel(1071876961674199040)  # Logs channel
            if log_channel:
                await log_channel.send(content=user.mention, embed=embed)

            await interaction.response.send_message(f"✅ Infraction logged for {user.mention}.", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message("❌ Failed to issue infraction.", ephemeral=True)
            print("Infraction error:", e)

    # ------------------------------
    # /infraction_history command
    # ------------------------------
    @app_commands.command(name="infraction_history", description="View a user's infractions")
    @app_commands.describe(user="Select the user")
    async def infraction_history(self, interaction: discord.Interaction, user: discord.Member):
        try:
            self.cursor.execute(
                "SELECT type, doc_link, appealable, moderator_id, timestamp FROM infractions WHERE user_id = ?",
                (user.id,)
            )
            rows = self.cursor.fetchall()

            if not rows:
                return await interaction.response.send_message("✅ No infractions found for this user.", ephemeral=True)

            for type, doc_link, appealable, moderator_id, timestamp in rows:
                moderator = interaction.guild.get_member(moderator_id)
                embed = discord.Embed(
                    title="Infraction History",
                    color=discord.Color.orange(),
                    timestamp=datetime.fromisoformat(timestamp)
                )
                embed.add_field(name="Member", value=user.mention, inline=True)
                embed.add_field(name="Type", value=type, inline=True)
                embed.add_field(name="Document", value=f"[Click Here]({doc_link})", inline=True)
                embed.add_field(name="Appealable", value=appealable, inline=True)
                embed.add_field(
                    name="Issued by",
                    value=moderator.mention if moderator else f"<@{moderator_id}>",
                    inline=True
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message("❌ Failed to fetch infractions.", ephemeral=True)
            print("History error:", e)

async def setup(bot):
    await bot.add_cog(InfractionSystem(bot))