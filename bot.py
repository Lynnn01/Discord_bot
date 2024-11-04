import discord
from discord.ext import commands
import os
import sys
from pathlib import Path
import time
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor
from discord import app_commands

# Add src to Python path
current_dir = Path(__file__).parent
src_path = current_dir / "src"
sys.path.insert(0, str(src_path))

from src.utils.logging_config import setup_logger
from src.utils.error_handler import GlobalErrorHandler
from src.utils.dev_mode_mixin import DevModeMixin

logger = setup_logger()


class MyBot(commands.Bot, DevModeMixin):
    def __init__(self):
        # ตั้งค่า dev_mode จาก environment variable
        self.dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"

        intents = discord.Intents.all()
        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=os.getenv("APPLICATION_ID"),
        )
        # เพิ่มการตั้งค่า command tree
        self.tree.on_error = self._handle_tree_error

        # กำหนดค่า base_dir
        self.base_dir = Path(__file__).parent / "src"

        self.start_time = time.time()
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.stats: Dict[str, int] = {
            "commands_used": 0,
            "errors_caught": 0,
            "messages_processed": 0,
            "ping": 0,
            "roll": 0,
        }

        # สร้างโครงสร้างไฟล์เมื่อเริ่มต้น
        self.ensure_directory_structure()

        self.error_handler = GlobalErrorHandler(self)

    def ensure_directory_structure(self):
        """สร้างและตรวจสอบโครงสร้างโฟลเดอร์"""
        try:
            required_folders = [
                self.base_dir / "cogs",
                self.base_dir / "commands",
                self.base_dir / "utils",
            ]

            if self.dev_mode:
                required_folders.append(self.base_dir / "dev_tools")

            for folder in required_folders:
                folder.mkdir(parents=True, exist_ok=True)
                logger.info(f"✅ ตรวจสอบโฟลเดอร์ {folder.relative_to(self.base_dir)}")

                init_file = folder / "__init__.py"
                if not init_file.exists():
                    init_file.touch()
                    logger.info(f"✅ สร้างไฟล์ {init_file.relative_to(self.base_dir)}")

        except PermissionError:
            logger.error("❌ ไม่มีสิทธิ์ในการสร้างโฟลเดอร์")
            raise
        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในการสร้างโครงสร้างไฟล์: {str(e)}")
            raise

    async def setup_hook(self):
        """ฟังก์ชันที่จะทำงานหลังจาก bot พร้อมทำงาน"""
        try:
            # ตรวจสอบ Dev Mode
            await self.validate_dev_guild()
            
            if self.dev_mode:
                # ออกจาก guild อื่นๆ ทั้งหมดยกเว้น dev guild
                for guild in self.guilds:
                    await self.handle_dev_mode(guild)
                    
                logger.info(f"🔒 Dev Mode: จำกัดการทำงานเฉพาะใน guild {self.dev_guild_id}")

            # โหลด cogs
            cog_list = ["src.cogs.commands", "src.cogs.event_handler"]
            if self.dev_mode:
                cog_list.append("src.cogs.dev_tools")

            for cog in cog_list:
                await self.load_extension(cog)
                logger.info(f"✅ โหลด {cog} สำเร็จ")

        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดใน setup_hook: {str(e)}")
            raise

    async def on_guild_join(self, guild: discord.Guild):
        """จัดการเมื่อบอทถูกเชิญเข้า guild ใหม่"""
        if self.dev_mode:
            dev_guild_id = int(os.getenv("DEV_GUILD_ID", "0"))
            if guild.id != dev_guild_id:
                logger.info(f"👋 ปฏิเสธการเข้าร่วม guild {guild.name} (Dev Mode)")
                await guild.leave()
                return

        logger.info(f"✨ เข้าร่วม guild {guild.name} ({guild.id}) สำเร็จ")

    async def on_ready(self):
        """เมื่อบอทพร้อมใช้งาน"""
        logger.info(f"✅ Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"📊 Connected to {len(self.guilds)} guilds")

    async def _handle_tree_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ):
        await self.error_handler.handle_error(interaction, error)
