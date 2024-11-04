from typing import Optional, Union, Any
import discord
from discord.ext import commands
from discord import app_commands
import traceback
import logging
from .constants import ERROR_MESSAGES

logger = logging.getLogger(__name__)

class GlobalErrorHandler:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, bot=None):
        if not hasattr(self, 'initialized'):
            self.bot = bot
            self.initialized = True
    
    async def create_error_embed(
        self,
        error: Exception,
        command_name: Optional[str],
        user: Union[discord.User, discord.Member],
        guild: Optional[discord.Guild],
        include_traceback: bool = False
    ) -> discord.Embed:
        """สร้าง Error Embed"""
        error_type = type(error)
        error_message = ERROR_MESSAGES.get(
            error_type, "เกิดข้อผิดพลาดที่ไม่คาดคิด กรุณาลองใหม่อีกครั้ง"
        )
        
        if isinstance(error, commands.CommandOnCooldown):
            error_message = f"กรุณารอ {error.retry_after:.1f} วินาที"
            
        embed = discord.Embed(
            title="⚠️ เกิดข้อผิดพลาด",
            description=error_message,
            color=discord.Color.red()
        )
        
        embed.add_field(name="คำสั่ง", value=command_name or "Unknown")
        embed.add_field(name="ผู้ใช้", value=f"{user} ({user.id})")
        
        if guild:
            embed.add_field(name="เซิร์ฟเวอร์", value=guild.name)
            
        if include_traceback and hasattr(error, "__traceback__"):
            tb = "".join(traceback.format_tb(error.__traceback__))
            if tb:
                embed.add_field(
                    name="Traceback",
                    value=f"```py\n{tb[:1000]}```",
                    inline=False
                )
                
        return embed

    async def handle_error(
        self,
        ctx_or_interaction: Union[commands.Context, discord.Interaction],
        error: Exception,
        ephemeral: bool = True,
        include_traceback: bool = False
    ) -> None:
        """จัดการ error ทั้งหมด"""
        if self.bot:
            self.bot.stats["errors_caught"] += 1

        try:
            is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
            
            command_name = None
            user = None
            guild = None
            
            if is_interaction:
                command_name = ctx_or_interaction.command.name if ctx_or_interaction.command else None
                user = ctx_or_interaction.user
                guild = ctx_or_interaction.guild
            else:
                command_name = ctx_or_interaction.command.name if ctx_or_interaction.command else None
                user = ctx_or_interaction.author
                guild = ctx_or_interaction.guild
                
            embed = await self.create_error_embed(
                error, command_name, user, guild, include_traceback
            )
            
            if is_interaction:
                if ctx_or_interaction.response.is_done():
                    await ctx_or_interaction.followup.send(embed=embed, ephemeral=ephemeral)
                else:
                    await ctx_or_interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            else:
                await ctx_or_interaction.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error sending error message: {e}")
            
        logger.error(f"Command error: {str(error)}")
