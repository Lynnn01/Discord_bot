import discord
from discord.ext import commands
from discord import app_commands
import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import asyncio
import psutil  # สำหรับเก็บข้อมูลระบบ

from ..utils.decorators import dev_command_error_handler
from ..utils.exceptions import DevModeError

# เพิ่มตัวเลือกสำหรับคำสั่ง
DEV_ACTIONS = [
    app_commands.Choice(name="🔄 Sync Commands", value="sync"),
    app_commands.Choice(name="♻️ Reload Cog", value="reload"),
    app_commands.Choice(name="📊 Show Status", value="status"),
    app_commands.Choice(name="🧹 Cleanup Old Commands", value="cleanup")
]

SYNC_SCOPES = [
    app_commands.Choice(name="🏠 Guild Only", value="guild"),
    app_commands.Choice(name="🌐 Global", value="global")
]

logger = logging.getLogger(__name__)


class DevCache:
    """จัดการ Cache สำหรับตรวจสอบสิทธิ์ Developer"""

    def __init__(self, timeout_minutes: int = 5):
        self._cache: Dict[int, tuple[datetime, bool]] = {}
        self._timeout = timedelta(minutes=timeout_minutes)

    def get(self, user_id: int) -> Optional[bool]:
        """ดึงสถานะ dev จาก cache"""
        if user_id in self._cache:
            timestamp, is_dev = self._cache[user_id]
            if datetime.utcnow() - timestamp < self._timeout:
                return is_dev
        return None

    def set(self, user_id: int, is_dev: bool) -> None:
        """บันทึกสถานะ dev ลง cache"""
        self._cache[user_id] = (datetime.utcnow(), is_dev)

    def clear_expired(self) -> None:
        """ลบ cache ที่หมดอายุ"""
        current_time = datetime.utcnow()
        self._cache = {
            user_id: (timestamp, is_dev)
            for user_id, (timestamp, is_dev) in self._cache.items()
            if current_time - timestamp < self._timeout
        }

    def count_active_devs(self) -> int:
        """นับจำนวน dev ที่ยังไม่หมดอายุ"""
        current_time = datetime.utcnow()
        return sum(
            1
            for _, (timestamp, is_dev) in self._cache.items()
            if current_time - timestamp < self._timeout and is_dev
        )

    def clear(self) -> None:
        """ล้าง cache ทั้งหมด"""
        self._cache.clear()


class CommandHistory:
    """จัดการประวัติการใช้คำสั่ง"""

    def __init__(self, max_entries: int = 10):
        self._history: List[Dict[str, Any]] = []
        self._max_entries = max_entries

    def add(self, user: discord.User, action: str, success: bool) -> None:
        """เพิ่มรายการประวัติใหม่"""
        try:
            entry = {
                "user": f"{user.name}#{user.discriminator}",
                "user_id": user.id,
                "action": action,
                "success": success,
                "timestamp": datetime.utcnow(),
            }
            self._history.append(entry)

            # จำกัดขนาดประวัติ
            if len(self._history) > self._max_entries:
                self._history.pop(0)
        except Exception as e:
            logger.error(f"❌ Error adding command history: {e}")

    def get_recent(self, count: int = 5) -> List[Dict[str, Any]]:
        """ดึงประวัติล่าสุดตามจำนวนที่ระบุ"""
        return list(reversed(self._history[-count:]))

    def clear(self) -> None:
        """ล้างประวัติทั้งหมด"""
        self._history.clear()


class DevTools(commands.Cog):
    """Cog สำหรับเครื่องมือพัฒนา"""

    def __init__(self, bot):
        self.bot = bot
        self._last_sync = None
        self._ready = False
        self._dev_cache = DevCache()
        self._history = CommandHistory()
        self.old_commands = set()
        self.process = psutil.Process()
        self.available_cogs = []
        self._update_available_cogs()

        # ตั้งค่าเริ่มต้นสำหรับ stats
        if not hasattr(bot, "stats"):
            bot.stats = {
                "commands_used": 0,
                "errors_caught": 0,
                "messages_processed": 0,
            }
    
    def _update_available_cogs(self):
        """อัพเดทรายชื่อ cogs ที่มีอยู่"""
        try:
            # สร้างรายการ cogs ที่โหลดอยู่
            self.available_cogs = [
                app_commands.Choice(name=f"📦 {name}", value=name)
                for name in self.bot.cogs.keys()
            ]
        except Exception as e:
            logger.error(f"Error updating available cogs: {e}")
            self.available_cogs = []
    
    

    def get_uptime(self) -> Optional[timedelta]:
        """คำนวณเวลาที่ bot ทำงาน"""
        try:
            if hasattr(self.bot, "start_time"):
                if isinstance(self.bot.start_time, (int, float)):
                    # ถ้าเป็น timestamp
                    start_datetime = datetime.fromtimestamp(self.bot.start_time)
                    return datetime.now() - start_datetime
                elif isinstance(self.bot.start_time, datetime):
                    # ถ้าเป็น datetime
                    return datetime.now() - self.bot.start_time
            return None
        except Exception as e:
            logger.error(f"Error calculating uptime: {e}")
            return None

    async def _init_bot(self):
        """เริ่มต้นการทำงานของ bot"""
        try:
            logger.info("⌛ Initializing DevTools...")
            await asyncio.sleep(1)  # รอให้ระบบพร้อมใช้งาน
            await self.cleanup_old_commands()
            logger.info("✅ DevTools initialization complete")
            return True
        except Exception as e:
            logger.error(f"❌ Error during initialization: {e}")
            return False

    async def cleanup_old_commands(self) -> None:
        """ลบคำสั่งเก่าที่ไม่ได้ใช้งาน"""
        try:
            if not self.bot or not self.bot.tree:
                logger.error("❌ Bot หรือ command tree ยังไม่พร้อมใช้งาน")
                return

            dev_guild_id = os.getenv("DEV_GUILD_ID")

            # ลบคำสั่งเก่าออกจาก command tree
            for cmd_name in self.old_commands:
                # ลบคำสั่งใน guild
                if dev_guild_id:
                    guild = discord.Object(id=int(dev_guild_id))
                    try:
                        cmd = self.bot.tree.get_command(cmd_name, guild=guild)
                        if cmd:
                            self.bot.tree.remove_command(cmd_name, guild=guild)
                            logger.info(f"✅ ลบคำสั่ง {cmd_name} ใน guild เรียบร้อย")
                    except Exception as e:
                        logger.error(f"Error removing guild command {cmd_name}: {e}")

                # ลบคำสั่ง global
                if not self.bot.dev_mode:
                    try:
                        cmd = self.bot.tree.get_command(cmd_name)
                        if cmd:
                            self.bot.tree.remove_command(cmd_name)
                            logger.info(f"✅ ลบคำสั่ง {cmd_name} global เรียบร้อย")
                    except Exception as e:
                        logger.error(f"Error removing global command {cmd_name}: {e}")

            # Sync การเปลี่ยนแปลง
            if dev_guild_id:
                guild = discord.Object(id=int(dev_guild_id))
                await self.bot.tree.sync(guild=guild)

            if not self.bot.dev_mode:
                await self.bot.tree.sync()

        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในการล้างคำสั่ง: {str(e)}")

    @commands.Cog.listener()
    async def on_ready(self):
        """เรียกใช้เมื่อบอทพร้อมทำงาน"""
        if not self._ready:
            self._ready = await self._init_bot()

    async def cog_load(self):
        """เรียกใช้เมื่อ Cog ูกโหลด"""
        logger.info("🔄 DevTools cog loading...")
        if hasattr(self.bot, "stats"):
            self.bot.stats.setdefault("commands_used", 0)
            self.bot.stats.setdefault("errors_caught", 0)
            self.bot.stats.setdefault("messages_processed", 0)
        logger.info("✅ DevTools cog loaded successfully")

    @app_commands.command(name="dev", description="🛠️ Developer commands for managing the bot")
    @app_commands.choices(action=DEV_ACTIONS)
    @app_commands.describe(
        action="เลือกการดำเนินการ",
        scope="ขอบเขตการ sync (เฉพาะคำสั่ง sync)",
        cog="เลือก cog ที่ต้องการ reload (เฉพาะคำสั่ง reload)"
    )
    @dev_command_error_handler()
    async def dev_command(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        scope: Optional[str] = None,
        cog: Optional[str] = None
    ):
        """คำสั่งสำหรับ developer"""
        if not await self._check_dev_permission(interaction):
            return

        await interaction.response.defer(ephemeral=True)
        
        if not self._ready and action.value not in ["sync", "status"]:
            await interaction.followup.send(
                "⚠️ Bot กำลังเริ่มต้นระบบ กรุณารอสักครู่...\n"
                "หมายเหตุ: คำสั่ง sync และ status สามารถใช้งานได้ระหว่างเริ่มต้นระบบ",
                ephemeral=True
            )
            return

        handlers = {
            "sync": lambda: self._handle_sync(interaction, scope or "guild"),
            "reload": lambda: self._handle_reload(interaction, cog),
            "status": lambda: self._handle_status(interaction),
            "cleanup": lambda: self._handle_cleanup(interaction)
        }

        if action.value in handlers:
            await handlers[action.value]()
            self._history.add(interaction.user, action.value, True)
        else:
            await interaction.followup.send("❌ Invalid action", ephemeral=True)

    @dev_command.autocomplete('scope')
    async def scope_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """แสดงตัวเลือกสำหรับ scope"""
        return SYNC_SCOPES

    @dev_command.autocomplete('cog')
    async def cog_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """แสดงตัวเลือกสำหรับ cog"""
        self._update_available_cogs()
        return self.available_cogs


    @dev_command_error_handler()
    async def _handle_sync(self, interaction: discord.Interaction, scope: str) -> None:
        """จัดการคำสั่ง sync"""
        if scope not in ["guild", "global"]:
            raise ValueError("Scope must be 'guild' or 'global'")

        if scope == "guild":
            self.bot.tree.copy_global_to(guild=interaction.guild)
            await self.bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send("✅ Synced guild commands", ephemeral=True)
        else:
            await self.bot.tree.sync()
            await interaction.followup.send("✅ Synced global commands", ephemeral=True)

    @dev_command_error_handler()
    async def _handle_reload(self, interaction: discord.Interaction, cog_name: Optional[str]) -> None:
        """จัดการคำสั่ง reload"""
        if not cog_name:
            raise ValueError("Please specify a cog name")

        try:
            await self.bot.reload_extension(f"cogs.{cog_name}")
            await interaction.followup.send(f"✅ Reloaded {cog_name}", ephemeral=True)
        except Exception as e:
            raise DevModeError(f"Failed to reload {cog_name}: {str(e)}")

    @dev_command_error_handler()
    async def _handle_status(self, interaction: discord.Interaction) -> None:
        """จัดการคำสั่ง status"""
        status_embed = await self._create_status_embed()
        await interaction.followup.send(embed=status_embed, ephemeral=True)

    @dev_command_error_handler()
    async def _handle_cleanup(self, interaction: discord.Interaction) -> None:
        """จัดการคำสั่ง cleanup"""
        await self.cleanup_old_commands()
        await interaction.followup.send("✅ Cleaned up old commands", ephemeral=True)

    async def _create_status_embed(self) -> discord.Embed:
        """สร้าง embed สำหรับแสดงสถานะของระบบ"""
        try:
            # ใช้ฟังก์ชันใหม่ในการคำนวณ uptime
            uptime = self.get_uptime()
            uptime_text = str(uptime).split(".")[0] if uptime else "N/A"

            status_embed = discord.Embed(
                title="🛠️ Developer Status", color=discord.Color.blue()
            )

            # Bot Info
            status_embed.add_field(
                name="🤖 Bot Info",
                value=f"```\n"
                f"Mode: {'Development' if self.bot.dev_mode else 'Production'}\n"
                f"Guilds: {len(self.bot.guilds)}\n"
                f"Commands: {len(self.bot.tree.get_commands())}\n"
                f"Uptime: {uptime_text}\n"
                f"```",
                inline=False,
            )

            # Last Sync Info
            if self._last_sync:
                sync_time = discord.utils.format_dt(self._last_sync["timestamp"], "R")
                status_embed.add_field(
                    name="🔄 Last Sync",
                    value=f"```\n"
                    f"Scope: {self._last_sync['scope']}\n"
                    f"Commands: {self._last_sync['count']}\n"
                    f"Time: {sync_time}\n"
                    f"```",
                    inline=False,
                )

            # System Stats
            process_info = await self._get_bot_process_info()
            if process_info:
                status_embed.add_field(
                    name="💻 System Stats",
                    value=f"```\n"
                    f"Memory: {process_info['memory_mb']:.1f} MB\n"
                    f"CPU: {process_info['cpu_percent']}%\n"
                    f"Threads: {process_info['threads']}\n"
                    f"Guilds: {len(self.bot.guilds)}\n"
                    f"Commands Used: {self.bot.stats['commands_used']}\n"
                    f"Errors Caught: {self.bot.stats['errors_caught']}\n"
                    f"Messages Processed: {self.bot.stats['messages_processed']}\n"
                    f"```",
                    inline=False,
                )

            # Recent Activity
            recent_commands = self._history.get_recent(5)
            if recent_commands:
                activity_text = "\n".join(
                    f"• {entry['user']}: {entry['action']} "
                    f"({discord.utils.format_dt(entry['timestamp'], 'R')})"
                    for entry in recent_commands
                )
                status_embed.add_field(
                    name="📝 Recent Activity", value=activity_text, inline=False
                )

            # Dev Cache Info
            cached_devs = self._dev_cache.count_active_devs()
            status_embed.set_footer(text=f"🔑 Cached Dev Permissions: {cached_devs}")
            return status_embed

        except Exception as e:
            logger.error(f"Error creating status embed: {e}")
            raise

    async def _get_bot_process_info(self) -> Dict[str, Any]:
        """รวบรวมข้อมูลการทำงานของบอท"""
        try:
            with self.process.oneshot():
                cpu_percent = self.process.cpu_percent()
                memory_info = self.process.memory_info()
                threads = self.process.num_threads()
                io_counters = self.process.io_counters()

            return {
                "cpu_percent": cpu_percent,
                "memory_mb": memory_info.rss / 1024 / 1024,
                "threads": threads,
                "pid": self.process.pid,
                "read_bytes": io_counters.read_bytes,
                "write_bytes": io_counters.write_bytes,
            }
        except Exception as e:
            logger.error(f"Error getting process info: {e}")
            return {}

    async def _check_dev_permission(self, interaction: discord.Interaction) -> bool:
        """ตรวจสอบสิทธิ์ dev"""
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ คำสั่งนี้ใช้ได้เฉพาะ developer เท่านั้น",
                ephemeral=True
            )
            return False
        return True

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """จัดการเมื่อมีการใช้งาน interaction"""
        if interaction.command:
            self.bot.stats["commands_used"] += 1
            self._dev_cache.clear_expired()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """จัดการเมื่อบอทถูกเชิญเข้า guild ใหม่"""
        if self.bot.dev_mode:
            dev_guild_id = os.getenv("DEV_GUILD_ID")
            if str(guild.id) != dev_guild_id:
                logger.warning(f"🚫 Leaving non-dev guild in dev mode: {guild.name}")
                await guild.leave()
                return
        logger.info(f"✅ Joined guild: {guild.name} (ID: {guild.id})")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        await self.bot.error_handler.handle_error(
            ctx, error, include_traceback=self.bot.dev_mode
        )

    async def cog_unload(self):
        """เรียกใช้เมื่อ Cog ถูก unload"""
        try:
            logger.info("💾 Saving important data before unload...")
            self._dev_cache.clear()
            self._history.clear()
            logger.info("👋 DevTools cog unloaded successfully")
        except Exception as e:
            logger.error(f"❌ Error during cog unload: {e}")


async def setup(bot):
    await bot.add_cog(DevTools(bot))
