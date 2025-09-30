import discord
from discord import app_commands
from discord.ext import commands
import asyncio

class Priority(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Load roles directly from file instead of importing from main
        self.STAFF_ROLES = self.load_roles_from_file("Roles/mods.txt")
        self.PRIORITY_CHANNEL_ID = 1266988746541105274

    def load_roles_from_file(self, filename):
        """Load role IDs from a file"""
        try:
            with open(filename, "r") as f:
                return [int(line.strip()) for line in f if line.strip().isdigit()]
        except FileNotFoundError:
            print(f"⚠️ {filename} not found. Using empty list.")
            return []
        except Exception as e:
            print(f"⚠️ Error loading {filename}: {e}")
            return []

    @app_commands.command(
        name="priority",
        description="Send a priority notification (checkpoint or roadwork)."
    )
    @app_commands.describe(
        user="The user this priority applies to.",
        type="Type of priority (checkpoint or roadwork).",
        location="Location of the priority.",
        duration="Duration in minutes."
    )
    async def priority(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        type: str,
        location: str,
        duration: int  # in minutes
    ):
        # Check staff permission
        if not any(role.id in self.STAFF_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message(
                "❌ You don't have permission to use this command.", ephemeral=True
            )

        # Target channel
        channel = interaction.guild.get_channel(self.PRIORITY_CHANNEL_ID)
        if not channel:
            return await interaction.response.send_message(
                "⚠️ Could not find the priority channel.", ephemeral=True
            )

        # Initial embed
        embed = discord.Embed(
            title="🚨 Priority Notification",
            color=discord.Color.orange()
        )
        embed.add_field(name="Permission given by", value=interaction.user.mention, inline=False)
        embed.add_field(name="User", value=user.mention, inline=False)
        embed.add_field(name="Type", value=type.capitalize(), inline=False)
        embed.add_field(name="Location", value=location, inline=False)
        embed.add_field(name="Duration", value=f"{duration}m left", inline=False)
        embed.set_footer(text="Priority issued by staff")

        # Send initial embed
        message = await channel.send(embed=embed)
        await interaction.response.send_message("✅ Priority notification sent.", ephemeral=True)

        # Countdown loop
        for remaining in range(duration - 1, -1, -1):
            await asyncio.sleep(60)  # wait 1 minute
            try:
                new_embed = discord.Embed(
                    title="🚨 Priority Notification",
                    color=discord.Color.orange()
                )
                new_embed.add_field(name="Permission given by", value=interaction.user.mention, inline=False)
                new_embed.add_field(name="User", value=user.mention, inline=False)
                new_embed.add_field(name="Type", value=type.capitalize(), inline=False)
                new_embed.add_field(name="Location", value=location, inline=False)
                new_embed.add_field(name="Duration", value=f"{remaining}m left", inline=False)
                new_embed.set_footer(text="Priority issued by staff")

                await message.edit(embed=new_embed)
            except discord.NotFound:
                # Message deleted manually
                break
            except discord.HTTPException:
                # Couldn't edit, skip
                continue

        # Final update when countdown ends
        try:
            final_embed = discord.Embed(
                title="🚨 Priority Notification",
                color=discord.Color.red()
            )
            final_embed.add_field(name="Permission given by", value=interaction.user.mention, inline=False)
            final_embed.add_field(name="User", value=user.mention, inline=False)
            final_embed.add_field(name="Type", value=type.capitalize(), inline=False)
            final_embed.add_field(name="Location", value=location, inline=False)
            final_embed.add_field(name="Duration", value="⏰ Time's up!", inline=False)
            final_embed.set_footer(text="Priority issued by staff")

            await message.edit(embed=final_embed)
        except:
            pass

async def setup(bot):
    await bot.add_cog(Priority(bot))
