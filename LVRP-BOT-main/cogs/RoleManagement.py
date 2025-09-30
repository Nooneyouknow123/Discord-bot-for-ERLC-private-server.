import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

# ------------------------------
# Slash commands (Role Management without GUI confirmation)
# ------------------------------
class RoleManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # autocomplete for role search
    async def role_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=role.name, value=str(role.id))
            for role in interaction.guild.roles if current.lower() in role.name.lower()
        ][:25]

    # ------------------------------
    # Shared role validation
    # ------------------------------
    async def validate_role_action(self, interaction, member, role_id: str, action: str):
        user, bot_member = interaction.user, interaction.guild.me
        try:
            role = interaction.guild.get_role(int(role_id))
        except:
            await interaction.response.send_message("❌ Invalid role ID.", ephemeral=True)
            return None
        if not user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ You do not have permission to manage roles.", ephemeral=True)
            return None
        if not role:
            await interaction.response.send_message("❌ Role not found.", ephemeral=True)
            return None
        if role.position >= user.top_role.position or member.top_role.position >= user.top_role.position:
            await interaction.response.send_message(f"❌ You cannot {action} this role due to hierarchy.", ephemeral=True)
            return None
        if role.position >= bot_member.top_role.position:
            await interaction.response.send_message(f"❌ I cannot {action} a role higher or equal to my top role.", ephemeral=True)
            return None
        return role

    # ------------------------------
    # Add role
    # ------------------------------
    @app_commands.command(name="add_role", description="Add a role to a member")
    @app_commands.describe(member="Select the member", role="Select the role")
    @app_commands.autocomplete(role=role_autocomplete)
    async def add_role(self, interaction: discord.Interaction, member: discord.Member, role: str):
        role = await self.validate_role_action(interaction, member, role, "assign")
        if not role: return
        if role in member.roles:
            return await interaction.response.send_message(f"⚠️ {member.display_name} already has {role.name}.", ephemeral=True)

        await member.add_roles(role, reason=f"Added by {interaction.user.display_name}")
        embed = discord.Embed(
            title="Role Added ✅",
            description=f"Added **{role.name}** to **{member.display_name}**",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ------------------------------
    # Remove role
    # ------------------------------
    @app_commands.command(name="remove_role", description="Remove a role from a member")
    @app_commands.describe(member="Select the member", role="Select the role")
    @app_commands.autocomplete(role=role_autocomplete)
    async def remove_role(self, interaction: discord.Interaction, member: discord.Member, role: str):
        role = await self.validate_role_action(interaction, member, role, "remove")
        if not role: return
        if role not in member.roles:
            return await interaction.response.send_message(f"⚠️ {member.display_name} does not have {role.name}.", ephemeral=True)

        await member.remove_roles(role, reason=f"Removed by {interaction.user.display_name}")
        embed = discord.Embed(
            title="Role Removed ❌",
            description=f"Removed **{role.name}** from **{member.display_name}**",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ------------------------------
async def setup(bot):
    await bot.add_cog(RoleManagement(bot))
    
