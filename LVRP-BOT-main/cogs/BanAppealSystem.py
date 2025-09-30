import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from datetime import datetime

# Constants
BAN_APPEAL_CHANNEL_ID = 1352990510800699473
BAN_APPEAL_REVIEW_CHANNEL_ID = 1269339090378035363

# Database setup
def init_ban_appeal_db():
    conn = sqlite3.connect("ban_appeals.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS ban_appeals (
                appeal_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                appeal_text TEXT NOT NULL,
                evidence_text TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                reviewer_id INTEGER,
                denial_reason TEXT,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
    
    # Create table for tracking the appeal message
    c.execute("""CREATE TABLE IF NOT EXISTS appeal_messages (
                channel_id INTEGER PRIMARY KEY,
                message_id INTEGER NOT NULL
            )""")
    conn.commit()
    conn.close()

# Initialize the DB when bot starts
init_ban_appeal_db()

class SubmitAppealButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Submit Appeal",
            style=discord.ButtonStyle.primary,
            custom_id="submit_appeal_button"
        )
    
    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_modal(SubmitAppealModal())
        except Exception as e:
            print(f"Button callback error: {e}")
            await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)

class SubmitAppealModal(discord.ui.Modal, title="Ban Appeal Submission"):
    def __init__(self):
        super().__init__(timeout=None)
        
    appeal_reason = discord.ui.TextInput(
        label="Appeal Reason",
        placeholder="Explain why you should be unbanned...",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )
    
    evidence = discord.ui.TextInput(
        label="Evidence (Optional)",
        placeholder="Provide any evidence or additional information...",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Generate unique appeal ID
            appeal_id = f"APPEAL_{interaction.user.id}_{int(datetime.now().timestamp())}"
            
            # Save to database
            conn = sqlite3.connect("ban_appeals.db")
            c = conn.cursor()
            c.execute("""
                INSERT INTO ban_appeals (appeal_id, user_id, username, appeal_text, evidence_text)
                VALUES (?, ?, ?, ?, ?)
            """, (appeal_id, interaction.user.id, str(interaction.user), self.appeal_reason.value, self.evidence.value or "No evidence provided"))
            conn.commit()
            conn.close()
            
            # Send to review channel
            await self.send_to_review_channel(interaction, appeal_id)
            
            await interaction.response.send_message(
                "✅ Your ban appeal has been submitted successfully! We will review it shortly.",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"Modal submit error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while submitting your appeal. Please try again later.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ An error occurred while submitting your appeal. Please try again later.",
                    ephemeral=True
                )

    async def send_to_review_channel(self, interaction: discord.Interaction, appeal_id: str):
        """Send the appeal to the review channel"""
        try:
            channel = interaction.guild.get_channel(BAN_APPEAL_REVIEW_CHANNEL_ID)
            if not channel:
                print("❌ Review channel not found")
                return

            embed = discord.Embed(
                title="Las Vegas Roleplay",
                description=":ticket: Ban Appeal Submitted",
                color=discord.Color.orange()
            ) 
            
            embed.add_field(
                name="User:",
                value=f"<@{interaction.user.id}>",
                inline=False
            )
            
            embed.add_field(
                name="Why they should be unbanned:",
                value=self.appeal_reason.value,
                inline=False
            )
            
            embed.add_field(
                name="Evidence:",
                value=self.evidence.value or "No evidence provided",
                inline=False
            )
            
            embed.add_field(
                name="Additional Information:",
                value=f"• Discord ID: {interaction.user.id}\n• Submitted: <t:{int(datetime.now().timestamp())}:F>",
                inline=False
            )
            
            embed.set_footer(text=f"Appeal ID: {appeal_id}")

            view = AppealReviewView(appeal_id, interaction.user.id)
            await channel.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"Error sending to review channel: {e}")

class AppealReviewView(discord.ui.View):
    def __init__(self, appeal_id: str, user_id: int):
        super().__init__(timeout=None)
        self.appeal_id = appeal_id
        self.user_id = user_id

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, custom_id="accept_appeal")
    async def accept_appeal(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has highrank role
        from main import highrank  # Import from main file
        if not any(role.id in highrank for role in interaction.user.roles):
            await interaction.response.send_message("❌ You don't have permission to review appeals.", ephemeral=True)
            return

        # Update database
        conn = sqlite3.connect("ban_appeals.db")
        c = conn.cursor()
        c.execute("""
            UPDATE ban_appeals SET status = 'accepted', reviewer_id = ? WHERE appeal_id = ?
        """, (interaction.user.id, self.appeal_id))
        conn.commit()
        conn.close()

        # Send DM to user
        await self.send_acceptance_dm(interaction)

        # Update the embed
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(
            name="Status:",
            value=f"✅ Accepted by {interaction.user.mention}",
            inline=False
        )
        
        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)
        
        await interaction.followup.send("✅ Appeal accepted successfully!", ephemeral=True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, custom_id="deny_appeal")
    async def deny_appeal(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has highrank role
        from main import highrank  # Import from main file
        if not any(role.id in highrank for role in interaction.user.roles):
            await interaction.response.send_message("❌ You don't have permission to review appeals.", ephemeral=True)
            return

        # Send modal for denial reason
        await interaction.response.send_modal(DenialReasonModal(self.appeal_id, self.user_id))

    async def send_acceptance_dm(self, interaction: discord.Interaction):
        """Send acceptance DM to the user"""
        try:
            user = await interaction.guild.fetch_member(self.user_id)
            embed = discord.Embed(
                title="Ban Appeal Accepted",
                description="Congratulations! Your ban appeal is accepted.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Message:",
                value="We hope you will abide the rules and have a nice role play with us!",
                inline=False
            )
            await user.send(embed=embed)
        except Exception as e:
            print(f"Error sending acceptance DM: {e}")

class DenialReasonModal(discord.ui.Modal, title="Appeal Denial Reason"):
    def __init__(self, appeal_id: str, user_id: int):
        super().__init__(timeout=None)
        self.appeal_id = appeal_id
        self.user_id = user_id
        
    denial_reason = discord.ui.TextInput(
        label="Reason for denial:",
        placeholder="Provide the reason for denying this appeal...",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Update database
            conn = sqlite3.connect("ban_appeals.db")
            c = conn.cursor()
            c.execute("""
                UPDATE ban_appeals SET status = 'denied', reviewer_id = ?, denial_reason = ? WHERE appeal_id = ?
            """, (interaction.user.id, self.denial_reason.value, self.appeal_id))
            conn.commit()
            conn.close()

            # Send DM to user
            await self.send_denial_dm(interaction)

            # Find and update the original message
            channel = interaction.guild.get_channel(BAN_APPEAL_REVIEW_CHANNEL_ID)
            if channel:
                async for message in channel.history(limit=100):
                    if message.embeds and self.appeal_id in message.embeds[0].footer.text:
                        embed = message.embeds[0]
                        embed.color = discord.Color.red()
                        embed.add_field(
                            name="Status:",
                            value=f"❌ Denied by {interaction.user.mention}",
                            inline=False
                        )
                        embed.add_field(
                            name="Denial Reason:",
                            value=self.denial_reason.value,
                            inline=False
                        )
                        
                        view = discord.ui.View(timeout=None)
                        await message.edit(embed=embed, view=view)
                        break

            await interaction.response.send_message("✅ Appeal denied successfully!", ephemeral=True)
        except Exception as e:
            print(f"Denial modal error: {e}")
            await interaction.response.send_message("❌ Error denying appeal.", ephemeral=True)

    async def send_denial_dm(self, interaction: discord.Interaction):
        """Send denial DM to the user"""
        try:
            user = await interaction.guild.fetch_member(self.user_id)
            embed = discord.Embed(
                title="Ban Appeal Denied",
                description="We are regretted to inform you that your ban appeal is denied.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Reason:",
                value=self.denial_reason.value,
                inline=False
            )
            embed.add_field(
                name="Message:",
                value="Have a nice day!",
                inline=False
            )
            await user.send(embed=embed)
        except Exception as e:
            print(f"Error sending denial DM: {e}")

class PersistentAppealView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SubmitAppealButton())

class BanAppealSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Import from main file
        from main import highrank
        self.highrank_roles = highrank

    async def cog_load(self):
        # Register persistent view
        self.bot.add_view(PersistentAppealView())

        # Wait until the bot is fully ready
        await self.bot.wait_until_ready()

        # Now send the ban appeal message
        await self.send_ban_appeal_message()


    async def send_ban_appeal_message(self):
        """Send the ban appeal embed message to the designated channel"""
        try:
            channel = self.bot.get_channel(BAN_APPEAL_CHANNEL_ID)
            if not channel:
                print("❌ Ban appeal channel not found")
                return

            # Check if message already exists in database
            conn = sqlite3.connect("ban_appeals.db")
            c = conn.cursor()
            c.execute("SELECT message_id FROM appeal_messages WHERE channel_id = ?", (BAN_APPEAL_CHANNEL_ID,))
            result = c.fetchone()
            conn.close()

            if result:
                # Check if message still exists in channel
                try:
                    message_id = result[0]
                    await channel.fetch_message(message_id)
                    print("✅ Ban appeal message already exists")
                    return  # Message exists, don't send another
                except discord.NotFound:
                    # Message was deleted, continue to send new one
                    pass

            embed = discord.Embed(
                title="Las Vegas Roleplay Ban Appeals",
                description="<:e7_banhammer:1096238831151358073> **Las Vegas Roleplay — Ban Appeals**\nIf you have been banned from Las Vegas Roleplay, this is where you can appeal.",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="<:tool:1230261893353046037> Requirements:",
                value="• Your ban reason must not be severe.\n• You do not have other recent bans.\n• You must wait 3 days before you can appeal your ban or appeal again.\n\nWe reserve the right to deny any appeal without explanation.\nMultiple appeals for the same ban will result in moderation.",
                inline=False
            )
            
            embed.set_image(url="https://cdn.discordapp.com/attachments/1018311287505162300/1396153024371495063/lvrplogo.png?ex=68d8ac94&is=68d75b14&hm=44dc4aeccda9dc1af623048bb10acc2c7f65f1be111b724a40489b56c0262321")
            embed.set_footer(text="Las Vegas Roleplay • Ban Appeals System")

            view = PersistentAppealView()
            
            message = await channel.send(embed=embed, view=view)
            
            # Save message ID to database
            conn = sqlite3.connect("ban_appeals.db")
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO appeal_messages (channel_id, message_id) VALUES (?, ?)", 
                     (BAN_APPEAL_CHANNEL_ID, message.id))
            conn.commit()
            conn.close()
            
            print("✅ Ban appeal message sent successfully")
            
        except Exception as e:
            print(f"❌ Error sending ban appeal message: {e}")

    def is_highrank(self, user: discord.Member) -> bool:
        """Check if user has highrank role"""
        return any(role.id in self.highrank_roles for role in user.roles)

async def setup(bot):
    await bot.add_cog(BanAppealSystem(bot))