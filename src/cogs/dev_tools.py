# Standard library imports
import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Third-party imports
import discord
from discord import app_commands
from discord.ext import commands
import psutil

# Local imports
from ..utils.decorators import dev_command_error_handler
from ..utils.exceptions import DevModeError, PermissionError

logger = logging.getLogger(__name__)

# Command choices
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


class DevCache:
    """จัดการ Cache สำหรับตรวจสอบสิทธิ์ Developer"""
    def __init__(self, timeout_minutes: int = 5):
        self._cache: Dict[int, tuple[datetime, bool]] = {}
        self._timeout = timedelta(minutes=timeout_minutes)

    def get(self, user_id: int) -> Optional[bool]:
        if user_id in self._cache:
            timestamp, is_dev = self._cache[user_id]
            if datetime.utcnow() - timestamp < self._timeout:
                return is_dev
        return None

    def set(self, user_id: int, is_dev: bool) -> None:
        self._cache[user_id] = (datetime.utcnow(), is_dev)

    def clear_expired(self) -> None:
        current_time = datetime.utcnow()
        self._cache = {
            user_id: (timestamp, is_dev)
            for user_id, (timestamp, is_dev) in self._cache.items()
            if current_time - timestamp < self._timeout
        }

    def count_active_devs(self) -> int:
        current_time = datetime.utcnow()
        return sum(
            1
            for _, (timestamp, is_dev) in self._cache.items()
            if current_time - timestamp < self._timeout and is_dev
        )

    def clear(self) -> None:
        self._cache.clear()

class CommandHistory:
    """จัดการประวัติการใช้คำสั่ง"""
    def __init__(self, max_entries: int = 10):
        self._history: List[Dict[str, Any]] = []
        self._max_entries = max_entries

    def add(self, user: discord.User, action: str, success: bool) -> None:
        try:
            entry = {
                "user": f"{user.name}#{user.discriminator}",
                "user_id": user.id,
                "action": action,
                "success": success,
                "timestamp": datetime.utcnow(),
            }
            self._history.append(entry)

            if len(self._history) > self._max_entries:
                self._history.pop(0)
        except Exception as e:
            logger.error(f"Error adding command history: {e}")

    def get_recent(self, count: int = 5) -> List[Dict[str, Any]]:
        return list(reversed(self._history[-count:]))

    def clear(self) -> None:
        self._history.clear()

class DevTools(commands.Cog):
    """Cog สำหรับเครื่องมือพัฒนา"""

    def __init__(self, bot):
        self.bot = bot
        self._last_sync = None
        self._ready = False
        self._startup_commands = {"sync", "status"}  # คำสั่งที่ใช้ได้ระหว่างเริ่มต้น
        self._dev_cache = DevCache()
        self._history = CommandHistory()
        self.old_commands = set()
        self.process = psutil.Process()
        self.available_cogs = []

        # ตั้งค่าค่าคงที่
        self.COLORS = {
            "success": discord.Color.green(),
            "error": discord.Color.red(),
            "warning": discord.Color.yellow(),
            "info": discord.Color.blue(),
        }

        self.EMOJI = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "loading": "⏳",
            "done": "✨",
        }

        self._update_available_cogs()

    async def _create_base_embed(
        self, title: str, description: str, color: discord.Color
    ) -> discord.Embed:
        """สร้าง embed พื้นฐาน"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow(),
        )
        return embed

    async def _safe_respond(
        self, interaction: discord.Interaction, **kwargs: Any
    ) -> None:
        """ส่งข้อความตอบกลับอย่างปลอดภัย"""
        try:
            if interaction.response.is_done():
                await interaction.followup.send(**kwargs)
            else:
                await interaction.response.send_message(**kwargs)
        except Exception as e:
            logger.error(f"Error sending response: {str(e)}")

    async def _show_loading(
        self, interaction: discord.Interaction, message: str = "กำลังดำเนินการ..."
    ) -> None:
        """แสดงข้อความ loading"""
        embed = await self._create_base_embed(
            title=f"{self.EMOJI['loading']} กำลังดำเนินการ",
            description=message,
            color=self.COLORS["info"],
        )
        await self._safe_respond(interaction, embed=embed, ephemeral=True)

    async def handle_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """จัดการข้อผิดพลาด"""
        await self.bot.error_handler.handle_error(interaction, error)

    def _update_available_cogs(self):
        """อัพเดทรายชื่อ cogs ที่มีอยู่"""
        try:
            self.available_cogs = [
                app_commands.Choice(name=f"📦 {name}", value=name)
                for name in self.bot.cogs.keys()
            ]
        except Exception as e:
            self.logger.error(f"Error updating available cogs: {e}")
            self.available_cogs = []

    @app_commands.command(name="dev", description="🛠️ Developer commands for managing the bot")
    @app_commands.choices(action=DEV_ACTIONS)
    @app_commands.describe(
        action="เลือกการดำเนินการ",
        scope="ขอบเขตการ sync (เฉพาะคำสั่ง sync)",
        cog="เลือก cog ที่ต้องการ reload (เฉพาะคำสั่ง reload)"
    )
    @dev_command_error_handler()
    async def execute(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        scope: Optional[str] = None,
        cog: Optional[str] = None
    ):
        """คำสั่งสำหรับ developer"""
        try:
            # ตรวจสอบสิทธิ์ developer
            if not await self._check_dev_permission(interaction):
                return

            await interaction.response.defer(ephemeral=True)
            
            if not self._ready and action.value not in ["sync", "status"]:
                raise DevModeError(
                    "⚠️ Bot กำลังเริ่มต้นระบบ กรุณารอสักครู่...\n"
                    "หมายเหตุ: คำสั่ง sync และ status สามารถใช้งานได้ร��หว่างเริ่มต้นระบบ"
                )

            # เพิ่มสถิติการใช้งาน
            self._history.add(interaction.user, action.value, True)

            # ดำเนินการตามคำสั่งที่เลือก
            match action.value:
                case "sync":
                    await self._handle_sync(interaction, scope or "guild")
                case "reload":
                    await self._handle_reload(interaction, cog)
                case "status":
                    await self._handle_status(interaction)
                case "cleanup":
                    await self._handle_cleanup(interaction)
                case _:
                    raise ValueError("Invalid action")

        except Exception as e:
            await self.handle_error(interaction, e)

    @execute.autocomplete('scope')
    async def scope_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """แสดงตัวเลือกสำหรับ scope"""
        return SYNC_SCOPES

    @execute.autocomplete('cog')
    async def cog_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """แสดงตัวเลือกสำหรับ cog"""
        self._update_available_cogs()
        return self.available_cogs

    async def _handle_sync(self, interaction: discord.Interaction, scope: str) -> None:
        """จัดการคำสั่ง sync"""
        if scope not in ["guild", "global"]:
            raise ValueError("Scope must be 'guild' or 'global'")

        await self._show_loading(interaction, "กำลัง sync commands...")

        if scope == "guild":
            self.bot.tree.copy_global_to(guild=interaction.guild)
            commands = await self.bot.tree.sync(guild=interaction.guild)
            self._last_sync = {
                "scope": "guild",
                "count": len(commands),
                "timestamp": datetime.utcnow()
            }
            embed = await self._create_base_embed(
                title=f"{self.EMOJI['success']} Sync สำเร็จ",
                description=f"Synced {len(commands)} guild commands",
                color=self.COLORS["success"]
            )
        else:
            commands = await self.bot.tree.sync()
            self._last_sync = {
                "scope": "global",
                "count": len(commands),
                "timestamp": datetime.utcnow()
            }
            embed = await self._create_base_embed(
                title=f"{self.EMOJI['success']} Sync สำเร็จ",
                description=f"Synced {len(commands)} global commands",
                color=self.COLORS["success"]
            )

        await self._safe_respond(interaction, embed=embed)

    async def _handle_reload(self, interaction: discord.Interaction, cog_name: Optional[str]) -> None:
        """จัดการคำสั่ง reload"""
        if not cog_name:
            raise ValueError("Please specify a cog name")

        await self._show_loading(interaction, f"กำลัง reload {cog_name}...")

        try:
            await self.bot.reload_extension(f"cogs.{cog_name}")
            embed = await self._create_base_embed(
                title=f"{self.EMOJI['success']} Reload สำเร็จ",
                description=f"Reloaded {cog_name}",
                color=self.COLORS["success"]
            )
        except Exception as e:
            raise DevModeError(f"Failed to reload {cog_name}: {str(e)}")

        await self._safe_respond(interaction, embed=embed)

    async def _handle_status(self, interaction: discord.Interaction) -> None:
        """จัดการคำสั่ง status"""
        await self._show_loading(interaction, "กำลังรวบรวมข้อมูลสถานะ...")
        status_embed = await self._create_status_embed()
        await self._safe_respond(interaction, embed=status_embed)

    async def _handle_cleanup(self, interaction: discord.Interaction) -> None:
        """จัดการคำสั่ง cleanup"""
        await self._show_loading(interaction, "กำลังล้างคำสั่งเก่า...")
        await self.cleanup_old_commands()
        
        embed = await self._create_base_embed(
            title=f"{self.EMOJI['success']} Cleanup สำเร็จ",
            description="ล้างคำสั่งเก่าเรียบร้อยแล้ว",
            color=self.COLORS["success"]
        )
        await self._safe_respond(interaction, embed=embed)

    async def _check_dev_permission(self, interaction: discord.Interaction) -> bool:
        """ตรวจสอบสิทธิ์ dev"""
        try:
            if not await self.bot.is_owner(interaction.user):
                raise PermissionError("คำสั่งนี้ใช้ได้เฉพาะ developer เท่านั้น")
            return True
        except Exception as e:
            await self.handle_error(interaction, e)
            return False

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

    async def _create_status_embed(self) -> discord.Embed:
        """สร้าง embed สำหรับแสดงสถานะของระบบ"""
        try:
            # คำนวณ uptime
            uptime = None
            if hasattr(self.bot, "start_time"):
                if isinstance(self.bot.start_time, (int, float)):
                    start_datetime = datetime.fromtimestamp(self.bot.start_time)
                    uptime = datetime.now() - start_datetime
                elif isinstance(self.bot.start_time, datetime):
                    uptime = datetime.now() - self.bot.start_time

            uptime_text = str(uptime).split(".")[0] if uptime else "N/A"

            status_embed = await self._create_base_embed(
                title=f"{self.EMOJI['info']} สถานะระบบ",
                description="ข้อมูลการทำงานของระบบ",
                color=self.COLORS["info"]
            )

            # Bot Info
            status_embed.add_field(
                name=f"{self.EMOJI['info']} ข้อมูลบอท",
                value=f"```\n"
                f"โหมด: {'Development' if self.bot.dev_mode else 'Production'}\n"
                f"เซิร์ฟเวอร์: {len(self.bot.guilds)}\n"
                f"คำสั่ง: {len(self.bot.tree.get_commands())}\n"
                f"เวลาทำงาน: {uptime_text}\n"
                f"```",
                inline=False,
            )

            # Last Sync Info
            if self._last_sync:
                sync_time = discord.utils.format_dt(self._last_sync["timestamp"], "R")
                status_embed.add_field(
                    name=f"{self.EMOJI['loading']} Sync ล่าสุด",
                    value=f"```\n"
                    f"ขอบเขต: {self._last_sync['scope']}\n"
                    f"จำนวนคำสั่ง: {self._last_sync['count']}\n"
                    f"เวลา: {sync_time}\n"
                    f"```",
                    inline=False,
                )

            # System Stats
            process_stats = await self._get_bot_process_info()
            if process_stats:
                status_embed.add_field(
                    name=f"{self.EMOJI['done']} สถิติระบบ",
                    value=f"```\n"
                    f"หน่วยความจำ: {process_stats['memory_mb']:.1f} MB\n"
                    f"CPU: {process_stats['cpu_percent']}%\n"
                    f"Threads: {process_stats['threads']}\n"
                    f"คำสั่งที่ใช้: {self.bot.stats['commands_used']}\n"
                    f"ข้อผิดพลาด: {self.bot.stats['errors_caught']}\n"
                    f"ข้อความที่ประมวลผล: {self.bot.stats['messages_processed']}\n"
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
                    name=f"{self.EMOJI['info']} กิจกรรมล่าสุด", 
                    value=activity_text, 
                    inline=False
                )

            # Developer Cache Info
            cached_devs = self._dev_cache.count_active_devs()
            status_embed.set_footer(
                text=f"🔑 จำนวน Developer ในแคช: {cached_devs}"
            )

            return status_embed

        except Exception as e:
            self.logger.error(f"Error creating status embed: {e}")
            raise

    async def _get_bot_process_info(self) -> Dict[str, Any]:
        """รวบรวมข้อมูลการทำงานของบอท"""
        try:
            with self.process.oneshot():
                cpu_percent = self.process.cpu_percent()
                memory_info = self.process.memory_info()
                threads = self.process.num_threads()

            return {
                "cpu_percent": cpu_percent,
                "memory_mb": memory_info.rss / 1024 / 1024,
                "threads": threads
            }
        except Exception as e:
            self.logger.error(f"Error getting process info: {e}")
            return {}

    async def _check_startup_state(self, interaction: discord.Interaction, action: str) -> None:
        """ตรวจสอบสถานะการเริ่มต้นของบอท"""
        if not self._ready and action.lower() not in self._startup_commands:
            raise DevModeError(
                "⚠️ Bot กำลังเริ่มต้นระบบ กรุณารอสักครู่...\n"
                f"หมายเหตุ: คำสั่ง {', '.join(self._startup_commands)} "
                "สามารถใช้งานได้ระหว่างเริ่มต้นระบบ"
            )

    @commands.Cog.listener()
    async def on_ready(self):
        """เมื่อบอทพร้อมใช้งาน"""
        self._ready = True
        logger.info("✅ DevTools พร้อมใช้งานแล้ว")


async def setup(bot):
    await bot.add_cog(DevTools(bot))
