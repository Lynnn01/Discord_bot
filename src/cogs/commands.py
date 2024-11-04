import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from typing import Optional
import logging

from ..commands.ping_command import PingCommand
from ..commands.roll_command import RollCommand
from ..commands.help_command import HelpCommand
from src.utils.exceptions import DevModeError

logger = logging.getLogger(__name__)


class CommandsCog(commands.Cog):
    """Cog สำหรับจัดการคำสั่งทั้งหมดของบอท"""

    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now()

        # สร้าง command instances
        self.ping_cmd = PingCommand(bot)
        self.roll_cmd = RollCommand(bot)
        self.help_cmd = HelpCommand(bot)

        # Register commands
        self._setup_commands()

    def _setup_commands(self):
        """ตั้งค่า commands"""

        # Command: ping
        @app_commands.command(name="ping", description="ตรวจสอบการเชื่อมต่อ")
        async def ping(interaction: discord.Interaction):
            await self.ping_cmd.execute(interaction, self.start_time, self.bot.stats)

        # Command: roll
        @app_commands.command(name="roll", description="ทอยลูกเต๋า")
        async def roll(interaction: discord.Interaction):
            await self.roll_cmd.execute(interaction, self.bot.stats)

        # Command: help
        @app_commands.command(name="help", description="ดูวิธีใช้คำสั่ง")
        @app_commands.describe(command="ชื่อคำสั่งที่ต้องการดูรายละเอียด")
        async def help(interaction: discord.Interaction, command: Optional[str] = None):
            await self.help_cmd.execute(
                interaction, self.bot.stats, command_name=command
            )

        # เพิ่ม commands เข้า CommandTree
        for cmd in [ping, roll, help]:
            self.bot.tree.add_command(cmd)
            logger.debug(f"✅ Registered command: {cmd.name}")

        logger.info("✅ Registered all commands successfully")

    @commands.Cog.listener()
    async def on_ready(self):
        """เรียกเมื่อ Cog พร้อมใช้งาน"""
        try:
            # sync commands กับ Discord
            await self.bot.tree.sync()

            # ตรวจสอบว่า commands ลงทะเบียนสำเร็จ
            commands = self.bot.tree.get_commands()
            logger.info(
                f"📝 Registered commands: {', '.join(cmd.name for cmd in commands)}"
            )

            # แสดงสถานะ dev mode
            if self.bot.dev_mode:
                logger.info("⚠️ Running in development mode")

        except Exception as e:
            logger.error(f"❌ Error in CommandsCog on_ready: {str(e)}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """จัดการ error จากคำสั่งปกติ"""
        await self.bot.error_handler.handle_error(ctx, error)
        
    @commands.Cog.listener()
    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ):
        """จัดการ error จาก slash commands"""
        await self.bot.error_handler.handle_error(interaction, error)


async def setup(bot):
    await bot.add_cog(CommandsCog(bot))
