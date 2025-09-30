import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

class PromotionSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # These need to be passed from main.py or loaded differently
        from main import promotionauth, modadmin_roles  # Import from main file
        self.promotion_auth_roles = promotionauth
        self.mod_roles = modadmin_roles

    # ------------------------------
    # Autocomplete for staff (mod_roles only)
    # ------------------------------
    async def staff_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=m.display_name, value=str(m.id))
            for m in interaction.guild.members
            if any(r.id in self.mod_roles for r in m.roles) and current.lower() in m.display_name.lower()
        ][:25]

    # ------------------------------
    # Autocomplete for role selection
    # ------------------------------
    async def role_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=r.name, value=str(r.id))
            for r in interaction.guild.roles
            if current.lower() in r.name.lower()
        ][:25]

    # ------------------------------
    # /promote command
    # ------------------------------
    @app_commands.command(name="promote", description="Promote a staff member to a new rank")
    @app_commands.describe(staff="Select the staff member to promote", role="Select the new role")
    async def promote(self, interaction: discord.Interaction, staff: str, role: str):
        try:
            user, guild, bot_member = interaction.user, interaction.guild, interaction.guild.me

            # Permission check
            if not any(r.id in self.promotion_auth_roles for r in user.roles):
                return await interaction.response.send_message("❌ You are not authorized to promote staff members.", ephemeral=True)
            if user.id == staff_member.id:
                return await interaction.response.send_message("❌ You cannot promote yourself.", ephemeral=True)
            # Get staff member
            staff_member = guild.get_member(int(staff))
            if not staff_member:
                return await interaction.response.send_message("❌ Staff member not found.", ephemeral=True)
            if not any(r.id in self.mod_roles for r in staff_member.roles):
                return await interaction.response.send_message("❌ This member is not eligible for promotion.", ephemeral=True)

            # Get new role
            new_role = guild.get_role(int(role))
            if not new_role:
                return await interaction.response.send_message("❌ Role not found.", ephemeral=True)
            if new_role in staff_member.roles:
                return await interaction.response.send_message(f"❌ {staff_member.display_name} already has the role {new_role.name}.", ephemeral=True)
            if new_role.position >= bot_member.top_role.position:
                return await interaction.response.send_message("❌ I cannot assign a role higher or equal to my top role.", ephemeral=True)

            # Add role
            await staff_member.add_roles(new_role, reason=f"Promoted by {user.display_name}")

            # Announcement embed
            embed = discord.Embed(
                title="Las Vegas Roleplay",
                description=f"** 🎉 Promotion Announcement** \nCongratulations **{staff_member.mention}**! You have been promoted to **{new_role.name}**. We appreciate your hard work.",
                color=discord.Color(0x8000FF),
                timestamp=datetime.now()
            ).add_field(name="Member", value=staff_member.mention, inline=True)\
             .add_field(name="Promoted to", value=new_role.mention, inline=True)\
             .add_field(name="Done by", value=user.mention, inline=True)

            for cid in [1055321675924774913, 1398046281762476193]:
                if (ch := guild.get_channel(cid)):
                    await ch.send(content=staff_member.mention, embed=embed)

            await interaction.response.send_message(f"✅ {staff_member.display_name} has been promoted to {new_role.name}.", ephemeral=True)

        except Exception as e:
            await interaction.followup.send("❌ Failed to promote staff.", ephemeral=True)
            print("Promotion error:", e)

    # ------------------------------
    # Register autocomplete hooks
    # ------------------------------
    @promote.autocomplete('staff')
    async def staff_autocomplete_hook(self, i: discord.Interaction, c: str): 
        return await self.staff_autocomplete(i, c)

    @promote.autocomplete('role')
    async def role_autocomplete_hook(self, i: discord.Interaction, c: str): 
        return await self.role_autocomplete(i, c)

async def setup(bot):
    await bot.add_cog(PromotionSystem(bot))