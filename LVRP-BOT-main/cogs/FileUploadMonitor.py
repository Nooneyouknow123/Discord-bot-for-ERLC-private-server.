import discord
from discord.ext import commands

FILE_UPLOAD_CATEGORY_IDS = (1198061580156420196, 1048746986247045150)

class FileUploadMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore bot messages and DMs
        if message.author.bot or not message.guild:
            return
        
        # Only act in the target categories
        if message.channel.category_id not in FILE_UPLOAD_CATEGORY_IDS:
            return
        
        # Skip messages without attachments
        if not message.attachments:
            return
        
        # File types that should be blocked
        blocked_extensions = ('.mp4', '.mov', '.avi', '.wmv', '.flv', '.webm', '.mkv', '.m4v')
        
        # Check if any attachment is blocked
        has_blocked = any(
            attachment.filename.lower().endswith(blocked_extensions)
            for attachment in message.attachments
        )
        
        if has_blocked:
            try:
                await message.delete()

                embed = discord.Embed(
                    title="🚫 Direct File Upload Blocked",
                    description=(
                        "We don't allow direct video file uploads.\n\n"
                        "**Please upload your video on one of these platforms instead:**\n"
                        "• YouTube\n"
                        "• Medal.tv\n"
                        "• Streamable\n"
                        "• Or any similar video platform"
                    ),
                    color=discord.Color.red()
                )
                embed.set_footer(text="Your cooperation helps keep the server organized.")

                await message.channel.send(
                    content=f"{message.author.mention}",
                    embed=embed,
                    delete_after=20
                )
            except Exception:
                # Prevent breaking other bot functions
                pass

async def setup(bot):
    await bot.add_cog(FileUploadMonitor(bot))
