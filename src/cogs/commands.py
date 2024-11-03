import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from typing import Optional
import logging
import os

from ..commands.ping_command import PingCommand
from ..commands.roll_command import RollCommand
from ..commands.help_command import HelpCommand

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

    async def _setup_commands(self):
        """ตั้งค่า commands"""
        try:
            # ตรวจสอบและลบคำสั่งที่มีอยู่แล้ว
            for cmd_name in ["ping", "roll", "help"]:
                existing_cmd = self.bot.tree.get_command(cmd_name)
                if existing_cmd:
                    self.bot.tree.remove_command(cmd_name)
                    logger.info(f"🔄 ลบคำสั่ง {cmd_name} ที่ซ้ำซ้อน")

            # สร้างคำสั่งใหม่
            commands = {
                "ping": self.ping_cmd.execute,
                "roll": self.roll_cmd.execute,
                "help": self.help_cmd.execute
            }

            for cmd_name, cmd_func in commands.items():
                cmd = app_commands.Command(
                    name=cmd_name,
                    description=self.command_descriptions.get(cmd_name, "ไม่มีคำอธิบาย"),
                    callback=cmd_func
                )
                self.bot.tree.add_command(cmd)
                logger.debug(f"✅ ลงทะเบียนคำสั่ง: {cmd_name}")

            # Sync commands หลังจาก ready
            self.bot.add_listener(self._sync_commands, 'on_ready')
            
        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในการตั้งค่าคำสั่ง: {str(e)}")
            raise

    async def _sync_commands(self):
        """Sync commands หลังจาก bot ready"""
        try:
            if self.bot.dev_mode:
                guild_id = int(os.getenv("DEV_GUILD_ID"))
                guild = discord.Object(id=guild_id)
                await self.bot.tree.sync(guild=guild)
            else:
                await self.bot.tree.sync()
                
            commands = self.bot.tree.get_commands()
            logger.info(f"📝 ลงทะเบียนคำสั่งสำเร็จ: {', '.join(cmd.name for cmd in commands)}")
            
        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในการ sync คำสั่ง: {str(e)}")

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


async def setup(bot):
    await bot.add_cog(CommandsCog(bot))
