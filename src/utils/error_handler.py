from typing import Optional, Union, Any
import discord
from discord.ext import commands
from discord import app_commands
import traceback
import logging
from .constants import ERROR_MESSAGES
from .embed_builder import EmbedBuilder

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
    
    async def handle_error(
        self,
        ctx: Union[commands.Context, discord.Interaction],
        error: Exception
    ):
        """จัดการ error แบบรวมศูนย์"""
        try:
            # แปลง error เป็นข้อความที่เข้าใจง่าย
            error_title = "เกิดข้อผิดพลาด"
            error_description = ERROR_MESSAGES.get(
                type(error), 
                "เกิดข้อผิดพลาดที่ไม่คาดคิด กรุณาลองใหม่อีกครั้ง"
            )
            
            # สร้าง error embed
            embed = EmbedBuilder.create_error_embed(
                title=error_title,
                description=error_description,
                error_details=str(error) if self.bot.dev_mode else None
            )

            # ส่ง response
            if isinstance(ctx, discord.Interaction):
                if ctx.response.is_done():
                    await ctx.followup.send(embed=embed, ephemeral=True)
                else:
                    await ctx.response.send_message(embed=embed, ephemeral=True)
            else:
                await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in error handler: {e}")
