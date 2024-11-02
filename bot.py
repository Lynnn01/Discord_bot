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

logger = setup_logger()


class MyBot(commands.Bot):
    def __init__(self):
        # เพิ่มการตรวจสอบ DEV_MODE
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
        try:
            # Clear existing commands first
            self.tree.clear_commands(guild=None)  # Clear global commands
            if self.dev_mode and (guild_id := os.getenv("DEV_GUILD_ID")):
                guild = discord.Object(id=int(guild_id))
                self.tree.clear_commands(guild=guild)  # Clear guild-specific commands
            
            # Load cogs
            cog_list = ["src.cogs.commands", "src.cogs.event_handler"]
            if self.dev_mode:
                cog_list.append("src.cogs.dev_tools")
                
            for cog in cog_list:
                await self.load_extension(cog)
                logger.info(f"✅ โหลด {cog} สำเร็จ")
            
            # Sync commands
            if self.dev_mode and guild_id:
                guild = discord.Object(id=int(guild_id))
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"✅ Synced commands to development guild: {guild_id}")
            else:
                await self.tree.sync()
                logger.info("✅ Synced commands globally")
                
        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในการเริ่มต้นบอท: {str(e)}")
            raise

    async def on_ready(self):
        """เมื่อบอทพร้อมใช้งาน"""
        logger.info(f"✅ Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"📊 Connected to {len(self.guilds)} guilds")

    async def _handle_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """จัดการ error ที่เกิดจาก command tree"""
        self.stats["errors_caught"] += 1
        
        error_message = "เกิดข้อผิดพลาดที่ไม่คาดคิด กรุณาลองใหม่อีกครั้ง"
        if isinstance(error, app_commands.CommandOnCooldown):
            error_message = f"กรุณารอ {error.retry_after:.1f} วินาที"
        elif isinstance(error, app_commands.MissingPermissions):
            error_message = "คุณไม่มีสิทธิ์ใช้คำสั่งนี้"
            
        try:
            await interaction.response.send_message(
                f"❌ {error_message}", ephemeral=True
            )
        except:
            if not interaction.response.is_done():
                await interaction.followup.send(
                    f"❌ {error_message}", ephemeral=True
                )
                
        logger.error(f"Command tree error: {str(error)}")
