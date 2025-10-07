import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import sqlite3
import random
import string

# Database setup inside the cog
def setup_database():
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
    return conn, c

def generate_review_id():
    return "".join(random.choices(string.digits, k=16))

REVIEWER_ROLE_ID =   # Put a role that everyone have like "member" or "verified", people with these roles can do staff reviews, they cannot manage them so do not worry :)

class ReviewSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn, self.c = setup_database()
        
        # These need to be passed from main.py or loaded differently
        from main import modadmin_roles, highrank  # Import from main file
        self.mod_roles = modadmin_roles
        self.highauth_roles = highrank

    # -------------------
    # /review
    # -------------------
    @app_commands.command(name="review", description="Submit a review for a staff member")
    @app_commands.describe(
        staff="Select the staff member to review",
        rating="Choose a rating between 0 and 5",
        feedback="Your feedback message (required)"
    )
    async def review(self, interaction: discord.Interaction, staff: discord.Member,
                     rating: app_commands.Range[int, 0, 5], feedback: str):
        try:
            reviewer = interaction.user

            # Runtime permission check
            if REVIEWER_ROLE_ID not in [role.id for role in reviewer.roles]:
                return await interaction.response.send_message(
                    "❌ You are not allowed to submit reviews.", ephemeral=True
                )

            if staff.id == reviewer.id:
                return await interaction.response.send_message("❌ You cannot review yourself.", ephemeral=True)

            if any(role.id in self.mod_roles for role in reviewer.roles):
                return await interaction.response.send_message(
                    "❌ Staff members cannot review other staff.", ephemeral=True
                )

            if not any(role.id in self.mod_roles for role in staff.roles):
                return await interaction.response.send_message(
                    "❌ You can only review staff members.", ephemeral=True
                )

            if not feedback.strip():
                return await interaction.response.send_message("❌ Feedback cannot be empty.", ephemeral=True)

            # Insert review into DB
            review_id = generate_review_id()
            self.c.execute("INSERT INTO reviews VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (review_id, staff.id, staff.display_name,
                       reviewer.id, reviewer.display_name, rating, feedback))
            self.conn.commit()

            embed = discord.Embed(
                title="✅ Review Submitted",
                description=(f"**Staff:** {staff.display_name}\n"
                             f"**Rating:** {rating} ⭐\n"
                             f"**Reviewer:** {reviewer.display_name}\n"
                             f"**Review ID:** `{review_id}`\n\n"
                             f"**Feedback:** {feedback}"),
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message("❌ Failed to submit review.", ephemeral=True)
            print("Review error:", e)

    # -------------------
    # /myreviews
    # -------------------
    @app_commands.command(name="myreviews", description="View reviews submitted about you (staff only)")
    async def myreviews(self, interaction: discord.Interaction):
        try:
            staff = interaction.user

            if not any(role.id in self.mod_roles for role in staff.roles):
                return await interaction.response.send_message(
                    "❌ Only staff members can view reviews about themselves.", ephemeral=True
                )

            self.c.execute("SELECT id, reviewer_name, rating, feedback FROM reviews WHERE staff_id=?", (staff.id,))
            rows = self.c.fetchall()
            if not rows:
                return await interaction.response.send_message("📭 No reviews have been submitted about you yet.", ephemeral=True)

            current_index = 0

            def make_embed(index: int):
                review_id, reviewer_name, rating, feedback = rows[index]
                embed = discord.Embed(title=f"📝 Reviews for {staff.display_name}", color=discord.Color.orange())
                embed.add_field(name="Review by", value=reviewer_name, inline=True)
                embed.add_field(name="Rating", value=f"{rating} ⭐", inline=True)
                embed.add_field(name="Feedback", value=feedback, inline=False)
                embed.add_field(name="Review ID", value=f"`{review_id}`", inline=False)
                embed.set_footer(text=f"Review {index+1}/{len(rows)} • Only visible to you")
                return embed

            class ReviewPagination(View):
                def __init__(self):
                    super().__init__(timeout=120)

                @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.secondary)
                async def previous(self, interaction2: discord.Interaction, button: Button):
                    nonlocal current_index
                    if interaction2.user.id != staff.id:
                        return await interaction2.response.send_message("❌ Not your session.", ephemeral=True)
                    current_index = (current_index - 1) % len(rows)
                    await interaction2.response.edit_message(embed=make_embed(current_index), view=self)

                @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.secondary)
                async def next(self, interaction2: discord.Interaction, button: Button):
                    nonlocal current_index
                    if interaction2.user.id != staff.id:
                        return await interaction2.response.send_message("❌ Not your session.", ephemeral=True)
                    current_index = (current_index + 1) % len(rows)
                    await interaction2.response.edit_message(embed=make_embed(current_index), view=self)

            await interaction.response.send_message(embed=make_embed(current_index), view=ReviewPagination(), ephemeral=True)

        except Exception as e:
            await interaction.response.send_message("❌ Failed to fetch reviews about you.", ephemeral=True)
            print("MyReviews error:", e)

    # -------------------
    # /viewreview
    # -------------------
    @app_commands.command(name="viewreview", description="(HR only) View reviews submitted about a staff member")
    @app_commands.describe(staff="The staff member whose reviews you want to view")
    async def viewreview(self, interaction: discord.Interaction, staff: discord.Member):
        try:
            requester = interaction.user

            if not any(role.id in self.highauth_roles for role in requester.roles):
                return await interaction.response.send_message(
                    "❌ You are not authorized to view other staff members' reviews.", ephemeral=True
                )

            if not any(role.id in self.mod_roles for role in staff.roles):
                return await interaction.response.send_message("❌ That member is not a staff member.", ephemeral=True)

            self.c.execute("SELECT id, reviewer_name, rating, feedback FROM reviews WHERE staff_id=?", (staff.id,))
            rows = self.c.fetchall()
            if not rows:
                return await interaction.response.send_message(f"📭 No reviews have been submitted about {staff.display_name}.", ephemeral=True)

            current_index = 0

            def make_embed(index: int):
                review_id, reviewer_name, rating, feedback = rows[index]
                embed = discord.Embed(title=f"📝 Reviews for {staff.display_name}", color=discord.Color.purple())
                embed.add_field(name="Review by", value=reviewer_name, inline=True)
                embed.add_field(name="Rating", value=f"{rating} ⭐", inline=True)
                embed.add_field(name="Feedback", value=feedback, inline=False)
                embed.add_field(name="Review ID", value=f"`{review_id}`", inline=False)
                embed.set_footer(text=f"Review {index+1}/{len(rows)} • Visible only to HR")
                return embed

            class ReviewPagination(View):
                def __init__(self):
                    super().__init__(timeout=180)

                @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.secondary)
                async def previous(self, interaction2: discord.Interaction, button: Button):
                    nonlocal current_index
                    if interaction2.user.id != requester.id:
                        return await interaction2.response.send_message("❌ Not your session.", ephemeral=True)
                    current_index = (current_index - 1) % len(rows)
                    await interaction2.response.edit_message(embed=make_embed(current_index), view=self)

                @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.secondary)
                async def next(self, interaction2: discord.Interaction, button: Button):
                    nonlocal current_index
                    if interaction2.user.id != requester.id:
                        return await interaction2.response.send_message("❌ Not your session.", ephemeral=True)
                    current_index = (current_index + 1) % len(rows)
                    await interaction2.response.edit_message(embed=make_embed(current_index), view=self)

            await interaction.response.send_message(embed=make_embed(current_index), view=ReviewPagination(), ephemeral=True)

        except Exception as e:
            await interaction.response.send_message("❌ Failed to fetch reviews.", ephemeral=True)
            print("ViewReview error:", e)

    # -------------------
    # /deletereview
    # -------------------
    @app_commands.command(name="deletereview", description="Delete a review by ID (HR only)")
    @app_commands.describe(staff="Staff member whose review you want to delete", review_id="The unique review ID")
    async def deletereview(self, interaction: discord.Interaction, staff: discord.Member, review_id: str):
        try:
            if not any(role.id in self.highauth_roles for role in interaction.user.roles):
                return await interaction.response.send_message("❌ You are not authorized to delete reviews.", ephemeral=True)

            self.c.execute("DELETE FROM reviews WHERE staff_id=? AND id=?", (staff.id, review_id))
            if self.c.rowcount == 0:
                return await interaction.response.send_message("⚠️ Review not found.", ephemeral=True)
            self.conn.commit()

            await interaction.response.send_message(f"✅ Review `{review_id}` for {staff.display_name} deleted.", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message("❌ Failed to delete review.", ephemeral=True)
            print("Delete review error:", e)

async def setup(bot):

    await bot.add_cog(ReviewSystem(bot))
