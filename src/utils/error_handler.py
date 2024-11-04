from typing import Union, Optional, Dict, Type
import discord
from discord.ext import commands
from discord import app_commands
import traceback
import logging
from datetime import datetime

from .exceptions import BotError, UserError, DevModeError, PermissionError
from .embed_builder import EmbedBuilder
from .constants import ERROR_MESSAGES

logger = logging.getLogger(__name__)

class ErrorData:
    """Class เก็บข้อมูล Error"""
    def __init__(
        self,
        title: str,
        description: str,
        color: str = "error",
        show_traceback: bool = False,
        ephemeral: bool = True,
        log_level: int = logging.ERROR
    ):
        self.title = title
        self.description = description
        self.color = color
        self.show_traceback = show_traceback
        self.ephemeral = ephemeral
        self.log_level = log_level

class GlobalErrorHandler:
    """จัดการ Error แบบรวมศูนย์"""
    
    def __init__(self, bot):
        self.bot = bot
        self._setup_error_mappings()
        
    def _setup_error_mappings(self):
        """กำหนด mapping ระหว่าง Exception และวิธีจัดการ"""
        self.error_mappings: Dict[Type[Exception], ErrorData] = {
            # Bot Custom Errors
            UserError: ErrorData(
                "⚠️ เกิดข้อผิดพลาด",
                "{error}",
                color="warning",
                log_level=logging.WARNING
            ),
            DevModeError: ErrorData(
                title="⚠️ โหมดพัฒนา",
                description="{error}",
                color=discord.Color.yellow(),
                log_level=logging.WARNING,
                show_traceback=False
            ),
            PermissionError: ErrorData(
                "🔒 ไม่มีสิทธิ์",
                "คุณไม่มีสิทธิ์ที่จำเป็น: {missing_perms}"
            ),
            
            # Discord.py Errors
            commands.MissingPermissions: ErrorData(
                "🔒 ไม่มีสิทธิ์",
                "คุณไม่มีสิทธิ์ในการใช้คำสั่งนี้"
            ),
            commands.BotMissingPermissions: ErrorData(
                "🔒 บอทไม่มีสิทธิ์",
                "บอทไม่มีสิทธิ์ที่จำเป็น"
            ),
            app_commands.CommandOnCooldown: ErrorData(
                "⏳ คำสั่งยังไม่พร้อมใช้งาน",
                "กรุณารอ {retry_after:.1f} วินาที",
                color="warning"
            ),
        }
        
    async def handle_error(
        self,
        ctx: Union[commands.Context, discord.Interaction],
        error: Exception,
        **kwargs
    ) -> None:
        """
        จัดการ error หลัก
        
        Args:
            ctx: Context หรือ Interaction ที่เกิด error
            error: Exception ที่เกิดขึ้น
            **kwargs: ข้อมูลเพิ่มเติมสำหรับการจัดการ error
        """
        try:
            # Unwrap error จริง
            error = getattr(error, 'original', error)
            
            # หา error data จาก mapping
            error_data = self._get_error_data(error)
            
            # สร้าง error message
            error_message = self._format_error_message(error_data, error, **kwargs)
            
            # Log error
            self._log_error(error, error_data, ctx)
            
            # สร้างและส่ง error embed
            embed = await self._create_error_embed(error_data, error_message)
            await self._send_error_response(ctx, embed, error_data.ephemeral)
            
        except Exception as e:
            logger.error(f"Error in error handler: {e}\n{traceback.format_exc()}")
            
    def _get_error_data(self, error: Exception) -> ErrorData:
        """หา ErrorData ที่เหมาะสมสำหรับ error"""
        for error_type, data in self.error_mappings.items():
            if isinstance(error, error_type):
                return data
                
        # Default error data
        return ErrorData(
            "❌ เกิดข้อผิดพลาด",
            "เกิดข้อผิดพลาดที่ไม่คาดคิด กรุณาลองใหม่อีกครั้ง"
        )
        
    def _format_error_message(
        self,
        error_data: ErrorData,
        error: Exception,
        **kwargs
    ) -> str:
        """จัดรูปแบบข้อความ error"""
        try:
            return error_data.description.format(
                error=str(error),
                **{k: v for k, v in kwargs.items() if isinstance(v, (str, int, float))}
            )
        except:
            return str(error)
            
    def _log_error(
        self,
        error: Exception,
        error_data: ErrorData,
        ctx: Union[commands.Context, discord.Interaction]
    ) -> None:
        """บันทึก error ลง log"""
        log_message = self._create_log_message(error, ctx)
        
        if error_data.show_traceback:
            log_message += f"\n{traceback.format_exc()}"
            
        logger.log(error_data.log_level, log_message)
        
    async def _create_error_embed(
        self,
        error_data: ErrorData,
        error_message: str
    ) -> discord.Embed:
        """สร้าง error embed"""
        return (
            EmbedBuilder()
            .set_title(error_data.title)
            .set_description(error_message)
            .set_color(error_data.color)
            .set_timestamp()
            .build()
        )
        
    async def _send_error_response(
        self,
        ctx: Union[commands.Context, discord.Interaction],
        embed: discord.Embed,
        ephemeral: bool
    ) -> None:
        """ส่ง error response ไปยังผู้ใช้"""
        try:
            if isinstance(ctx, discord.Interaction):
                if ctx.response.is_done():
                    await ctx.followup.send(embed=embed, ephemeral=ephemeral)
                else:
                    await ctx.response.send_message(embed=embed, ephemeral=ephemeral)
            else:
                await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error sending error response: {e}")

    def _create_log_message(
        self,
        error: Exception,
        ctx: Union[commands.Context, discord.Interaction]
    ) -> str:
        """สร้างข้อความ log สำหรับ error
        
        Args:
            error: Exception ที่เกิดขึ้น
            ctx: Context หรือ Interaction ที่เกิด error
            
        Returns:
            str: ข้อความ log ที่จัดรูปแบบแล้ว
        """
        # ดึงข้อมูลผู้ใช้และ guild
        if isinstance(ctx, discord.Interaction):
            user = ctx.user
            guild = ctx.guild
            command = ctx.command.name if ctx.command else "Unknown"
        else:
            user = ctx.author
            guild = ctx.guild
            command = ctx.command.name if ctx.command else "Unknown"
            
        # สร้างข้อความ log
        log_parts = [
            f"Error in command '{command}'",
            f"User: {user} (ID: {user.id})",
        ]
        
        if guild:
            log_parts.append(f"Guild: {guild.name} (ID: {guild.id})")
        else:
            log_parts.append("Guild: DM")
            
        log_parts.append(f"Error: {str(error)}")
        
        return " | ".join(log_parts)
