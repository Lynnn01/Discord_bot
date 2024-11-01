import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import logging
from typing import Dict
from commands.roll_command import RollCommand
from commands.ping_command import PingCommand

logger = logging.getLogger(__name__)


class Basic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot_start_time = datetime.utcnow()
        self._command_stats: Dict[str, int] = {"roll": 0, "ping": 0}

        # สร้าง instance ของแต่ละคำสั่ง
        self.roll_command = RollCommand(bot)
        self.ping_command = PingCommand(bot)

    async def cog_load(self) -> None:
        logger.info("✅ Basic cog ถูกโหลดและพร้อมใช้งาน")

    async def cog_unload(self) -> None:
        logger.info(f"🔄 Basic cog ถูกยกเลิกการโหลด - สถิติการใช้งาน: {self._command_stats}")

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        error_messages = {
            app_commands.CommandOnCooldown: f"⏳ กรุณารอ {error.retry_after:.1f} วินาที",
            app_commands.MissingPermissions: "🚫 คุณไม่มีสิทธิ์ใช้คำสั่งนี้",
            app_commands.BotMissingPermissions: "⚠️ บอทไม่มีสิทธิ์ที่จำเป็น",
            app_commands.CommandNotFound: "❓ ไม่พบคำสั่งนี้",
        }

        response = error_messages.get(type(error), "❌ เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง")
        await interaction.response.send_message(response, ephemeral=True)
        logger.error(f"🐛 เกิดข้อผิดพลาดในคำสั่ง {interaction.command.name}: {str(error)}")

    @app_commands.command(name="roll", description="🎲 ทอยลูกเต๋า D20")
    @app_commands.checks.cooldown(1, 3.0)
    async def roll(self, interaction: discord.Interaction):
        """ทอยลูกเต๋า D20 พร้อมเอฟเฟกต์พิเศษ"""
        await self.roll_command.execute(interaction, self._command_stats)

    # เพิ่มคำสั่ง ping
    @app_commands.command(name="ping", description="🏓 เช็คการตอบสนองของบอท")
    @app_commands.checks.cooldown(1, 5.0)
    async def ping(self, interaction: discord.Interaction):
        """แสดงข้อมูลการตอบสนองและสถานะของบอท"""
        await self.ping_command.execute(
            interaction, self.bot_start_time, self._command_stats
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Basic(bot))
