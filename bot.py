# bot.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import time
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
from logging_config import setup_logging  # นำเข้าระบบ logging ใหม่

# ตั้งค่า logger
logger = setup_logging()


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.all(),
            application_id=os.getenv("APPLICATION_ID"),
        )
        self.start_time = time.time()
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.stats: Dict[str, int] = {
            "commands_used": 0,
            "errors_caught": 0,
            "messages_processed": 0,
        }

    async def close(self):
        """Cleanup resources when bot shuts down"""
        logger.info("🔄 กำลังปิดการทำงานของบอท...")
        self.executor.shutdown(wait=False)
        await super().close()

    async def load_cogs(self) -> Dict[str, int]:
        """โหลด cogs พร้อมระบบบันทึกล็อกที่สมบูรณ์"""
        stats = {"loaded": 0, "failed": 0, "skipped": 0, "total": 0}
        skip_files = frozenset(["__init__.py", "__pycache__", "temp", "test", "draft"])

        try:
            if not os.path.exists("./cogs"):
                logger.warning("⚠️ ไม่พบโฟลเดอร์ cogs - กำลังสร้าง")
                os.makedirs("./cogs")

            for filename in os.listdir("./cogs"):
                stats["total"] += 1

                if filename in skip_files or any(
                    filename.startswith(skip) for skip in skip_files
                ):
                    logger.debug(f"⏭️ ข้าม: {filename}")
                    stats["skipped"] += 1
                    continue

                if filename.endswith(".py"):
                    await self._load_single_cog(f"cogs.{filename[:-3]}", stats)

        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในการโหลด cogs: {str(e)}")
            raise

        return stats

    async def _load_single_cog(self, extension: str, stats: Dict[str, int]) -> None:
        """โหลด cog เดี่ยวพร้อมการจัดการข้อผิดพลาด"""
        try:
            await self.load_extension(extension)
            logger.info(f"✅ โหลด {extension} สำเร็จ")
            stats["loaded"] += 1
        except Exception as e:
            logger.error(f"❌ ไม่สามารถโหลด {extension}: {str(e)}")
            stats["failed"] += 1

    async def sync_commands(self) -> Optional[List[discord.app_commands.Command]]:
        """Sync commands with enhanced logging"""
        try:
            if os.getenv("DEV_MODE") == "true":
                dev_guild_id = os.getenv("DEV_GUILD_ID")
                if not dev_guild_id:
                    raise ValueError("DEV_MODE เปิดอยู่แต่ไม่พบ DEV_GUILD_ID")

                guild = discord.Object(id=int(dev_guild_id))
                self.tree.copy_global_to(guild=guild)
                return await self.tree.sync(guild=guild)
            else:
                return await self.tree.sync()

        except discord.HTTPException as e:
            logger.error(f"❌ HTTP Error ในการ sync: {e.status} - {e.text}")
        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในการ sync: {str(e)}")
        return None

    async def setup_hook(self):
        """Setup hook with improved logging"""
        logger.info("\n=== 🚀 กำลังเริ่มต้นบอท ===")
        start_time = time.time()

        try:
            stats = await self.load_cogs()

            logger.info("\n📊 สรุปการโหลด cogs:")
            logger.info(f"   ✅ สำเร็จ: {stats['loaded']}")
            logger.info(f"   ❌ ล้มเหลว: {stats['failed']}")
            logger.info(f"   ⏭️ ข้าม: {stats['skipped']}")
            logger.info(f"   📁 ทั้งหมด: {stats['total']}")

            logger.info("\n🔄 กำลัง sync commands...")
            synced = await self.sync_commands()
            if synced:
                logger.info(f"✅ Synced {len(synced)} commands สำเร็จ")

            setup_time = round(time.time() - start_time, 2)
            logger.info(f"\n⏱️ เวลาที่ใช้ในการเริ่มต้น: {setup_time} วินาที")

        except Exception as e:
            logger.critical(f"❌ เกิดข้อผิดพลาดร้ายแรงในการเริ่มต้นบอท: {str(e)}")
            raise

    async def on_ready(self):
        """Enhanced on_ready with better logging"""
        uptime = time.time() - self.start_time
        guild_count = len(self.guilds)
        total_members = sum(guild.member_count for guild in self.guilds)

        logger.info("\n=== ✨ บอทพร้อมใช้งาน ===")
        logger.info(f"🤖 เข้าสู่ระบบในชื่อ: {self.user} (ID: {self.user.id})")
        logger.info(f"⏱️ พร้อมใช้งานใน: {uptime:.2f} วินาที")

        logger.info(f"\n📊 สถานะการเชื่อมต่อ:")
        logger.info(f"   💻 เซิร์ฟเวอร์: {guild_count}")
        logger.info(f"   👥 ผู้ใช้ทั้งหมด: {total_members}")

        guild_info = "\n".join(
            f"   • {guild.name} (ID: {guild.id}, สมาชิก: {guild.member_count})"
            for guild in self.guilds
        )
        logger.info(f"\n📡 รายชื่อเซิร์ฟเวอร์:\n{guild_info}")


async def main():
    """Main function with enhanced error handling"""
    try:
        load_dotenv()

        required_vars = {"DISCORD_TOKEN", "APPLICATION_ID"}
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            raise ValueError(f"❌ ไม่พบตัวแปรที่จำเป็น: {', '.join(missing_vars)}")

        async with MyBot() as bot:
            await bot.start(os.getenv("DISCORD_TOKEN"))

    except ValueError as e:
        logger.critical(f"❌ ข้อผิดพลาดในการตั้งค่า: {str(e)}")
        raise
    except Exception as e:
        logger.critical(f"❌ เกิดข้อผิดพลาดที่ไม่คาดคิด: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 ปิดบอทด้วยการกด Ctrl+C\n")
    except Exception as e:
        logger.critical(f"❌ เกิดข้อผิดพลาดที่ไม่คาดคิด: {str(e)}\n")
        raise
