import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to Python path
current_dir = Path(__file__).parent
src_path = current_dir / "src"
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(src_path))

from src.utils.logging_config import setup_logger
from bot import MyBot

logger = setup_logger()


async def main():
    try:
        # Load .env
        load_dotenv()

        # Check required vars
        required_vars = {"DISCORD_TOKEN", "APPLICATION_ID"}
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            raise ValueError(f"❌ ไม่พบตัวแปรที่จำเป็น: {', '.join(missing_vars)}")

        async with MyBot() as bot:
            await bot.start(os.getenv("DISCORD_TOKEN"))

    except Exception as e:
        logger.critical(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 ปิดบอทด้วยการกด Ctrl+C")
    except Exception as e:
        logger.critical(f"❌ เกิดข้อผิดพลาดที่ไม่คาดคิด: {str(e)}")
