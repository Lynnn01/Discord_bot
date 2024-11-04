import asyncio
import os
import sys
from pathlib import Path
from typing import Set, Dict, Optional
from dotenv import load_dotenv
import signal

# Add src to Python path
current_dir = Path(__file__).parent
src_path = current_dir / "src"
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(src_path))

from src.utils.logging_config import setup_logger
from bot import MyBot

# ตั้งค่า logger
logger = setup_logger()


class BotManager:
    """จัดการการทำงานของบอท"""

    def __init__(self):
        self.bot: Optional[MyBot] = None
        self.required_vars: Set[str] = {
            "DISCORD_TOKEN",
            "APPLICATION_ID",
            "DEV_MODE",
            "DEV_GUILD_ID",
        }
        self.shutdown_flag = False

    def validate_env(self) -> Dict[str, str]:
        """ตรวจสอบและโหลดตัวแปรสภาพแวดล้อม"""
        # โหลด .env
        load_dotenv()

        # ตรวจสอบตัวแปรที่จำเป็น
        env_vars = {}
        missing_vars = []

        for var in self.required_vars:
            value = os.getenv(var)
            if var in ["DISCORD_TOKEN", "APPLICATION_ID"] and not value:
                missing_vars.append(var)
            env_vars[var] = value

        if missing_vars:
            raise ValueError(f"❌ ไม่พบตัวแปรที่จำเป็น: {', '.join(missing_vars)}")

        # ตรวจสอบ DEV_MODE และ DEV_GUILD_ID ผ่าน DevModeMixin
        if env_vars.get("DEV_MODE", "").lower() == "true":
            if not env_vars.get("DEV_GUILD_ID"):
                raise ValueError("❌ DEV_MODE เปิดอยู่แต่ไม่พบ DEV_GUILD_ID")

        return env_vars

    def setup_signal_handlers(self):
        """ตั้งค่าตัวจัดการสัญญาณระบบ"""

        def handle_shutdown(signum, frame):
            signame = signal.Signals(signum).name
            logger.info(f"🛑 ได้รับสัญญาณ {signame}")
            self.shutdown_flag = True
            if self.bot:
                logger.info("⏳ กำลังปิดบอทอย่างปลอดภัย...")
                asyncio.create_task(self.shutdown())

        # รองรับทั้ง SIGINT (Ctrl+C) และ SIGTERM
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

    async def shutdown(self):
        """ปิดบอทอย่างปลอดภัย"""
        if self.bot:
            try:
                await self.bot.close()
                logger.info("👋 ปิดบอทเรียบร้อยแล้ว")
            except Exception as e:
                logger.error(f"❌ เกิดข้อผิดพลาดในการปิดบอท: {e}")

    async def startup_checks(self) -> bool:
        """
        ตรวจสอบระบบก่อนเริ่มบอท

        Returns:
            bool: True ถ้าผ่านการตรวจสอบทั้งหมด
        """
        try:
            # ตรวจสอบโฟลเดอร์ที่จำเป็น
            required_folders = ["cogs", "commands", "utils"]
            for folder in required_folders:
                folder_path = src_path / folder
                if not folder_path.exists():
                    logger.warning(f"⚠️ ไม่พบโฟลเดอร์ {folder}")
                    folder_path.mkdir(parents=True)
                    logger.info(f"✅ สร้างโฟลเดอร์ {folder} แล้ว")

            # ตรวจสอบการเชื่อมต่อเครือข่าย

            return True

        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในการตรวจสอบระบบ: {e}")
            return False

    async def run(self):
        """เริ่มการทำงานของบอท"""
        try:
            # ตั้งค่าตัวจัดการสัญญาณ
            self.setup_signal_handlers()

            # ตรวจสอบตัวแปรสภาพแวดล้อม
            env_vars = self.validate_env()

            # ตรวจสอบระบบ
            if not await self.startup_checks():
                raise RuntimeError("❌ ไม่ผ่านการตรวจสอบระบบ")

            logger.info("🚀 เริ่มต้นบอท...")

            # สร้างและเริ่มบอท
            async with MyBot() as self.bot:
                await self.bot.start(env_vars["DISCORD_TOKEN"])

        except Exception as e:
            logger.critical(f"❌ เกิดข้อผิดพลาดในการเริ่มบอท: {str(e)}")
            raise


def run_bot():
    """ฟังก์ชันหลักสำหรับเริ่มบอท"""
    try:
        manager = BotManager()
        asyncio.run(manager.run())
    except KeyboardInterrupt:
        logger.info("👋 ปิดบอทด้วยการกด Ctrl+C")
    except Exception as e:
        logger.critical(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    run_bot()
