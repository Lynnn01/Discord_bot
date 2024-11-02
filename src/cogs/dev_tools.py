import discord
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger(__name__)

class DevTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(
        name="sync",
        description="Sync slash commands (Dev only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def sync(self, interaction: discord.Interaction):
        """Sync slash commands"""
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("❌ คำสั่งนี้ใช้ได้เฉพาะ Developer เท่านั้น", ephemeral=True)
            return
            
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Sync commands
            await self.bot.tree.sync()
            
            await interaction.followup.send("✅ Synced commands successfully", ephemeral=True)
            logger.info(f"Commands synced by {interaction.user}")
            
        except Exception as e:
            logger.error(f"Error syncing commands: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @app_commands.command(
        name="reload",
        description="Reload cogs (Dev only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def reload(self, interaction: discord.Interaction):
        """Reload all cogs"""
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("❌ คำสั่งนี้ใช้ได้เฉพาะ Developer เท่านั้น", ephemeral=True)
            return
            
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Reload cogs
            for cog in ["src.cogs.commands", "src.cogs.event_handler", "src.cogs.dev_tools"]:
                await self.bot.reload_extension(cog)
                logger.info(f"Reloaded {cog}")
                
            await interaction.followup.send("✅ Reloaded all cogs successfully", ephemeral=True)
            logger.info(f"Cogs reloaded by {interaction.user}")
            
        except Exception as e:
            logger.error(f"Error reloading cogs: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(DevTools(bot)) 