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
from ..utils.embed_builder import EmbedBuilder

logger = logging.getLogger(__name__)

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


class DevTools(commands.GroupCog, group_name="dev"):
    """Developer tools for managing the bot"""

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
        super().__init__()

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
            color=self.COLORS["info"]
        )
        await self._safe_respond(interaction, embed=embed, ephemeral=True)

    def _update_available_cogs(self):
        """อัพเดทรายชื่อ cogs ที่มีอยู่"""
        try:
            self.available_cogs = [
                app_commands.Choice(name=f"📦 {name}", value=name)
                for name in self.bot.cogs.keys()
            ]
        except Exception as e:
            logger.error(f"Error updating available cogs: {e}")
            self.available_cogs = []

    async def handle_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """จัดการข้อผิดพลาด"""
        await self.bot.error_handler.handle_error(interaction, error)

    @app_commands.command(name="help", description="❓ แสดงวิธีใช้คำสั่ง Developer")
    async def dev_help(self, interaction: discord.Interaction):
        """แสดงวิธีใช้คำสั่ง developer ทั้งหมด"""
        try:
            if not await self._check_dev_permission(interaction):
                return

            embed = (
                EmbedBuilder()
                .set_title("🛠️ Developer Commands", emoji="❓")
                .set_description("คำสั่งสำหรับจัดการระบบ")
                .add_field(
                    "🔄 /dev sync [scope]",
                    "Sync application commands\n`scope`: guild/global",
                    inline=False
                )
                .add_field(
                    "♻️ /dev reload [cog]",
                    "Reload cogs\n`cog`: ชื่อ cog หรือ 'all' สำหรับ reload ทั้งหมด",
                    inline=False
                )
                .add_field(
                    "📊 /dev status",
                    "แสดงสถานะของระบบ",
                    inline=False
                )
                .add_field(
                    "🧹 /dev cleanup",
                    "ล้างคำสั่งเก่า",
                    inline=False
                )
                .set_color("info")
                .set_footer(f"Requested by {interaction.user}")
                .build()
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await self.handle_error(interaction, e)

    @app_commands.command(name="sync", description="🔄 Sync application commands")
    @app_commands.describe(scope="ขอบเขตการ sync commands")
    @app_commands.choices(scope=[
        app_commands.Choice(name="🏠 Guild Only", value="guild"),
        app_commands.Choice(name="🌐 Global", value="global")
    ])
    async def sync(self, interaction: discord.Interaction, scope: str = "guild"):
        """Sync application commands"""
        try:
            if not await self._check_dev_permission(interaction):
                return
                
            await self._handle_sync(interaction, scope)
        except Exception as e:
            await self.handle_error(interaction, e)

    @app_commands.command(name="reload", description="♻️ Reload cogs")
    @app_commands.describe(cog="Cog ที่ต้องการ reload (ใช้ all เพื่อ reload ทั้งหมด)")
    async def reload(self, interaction: discord.Interaction, cog: str):
        """Reload cogs"""
        try:
            if not await self._check_dev_permission(interaction):
                return
                
            await self._handle_reload(interaction, cog)
        except Exception as e:
            await self.handle_error(interaction, e)

    @reload.autocomplete('cog')
    async def reload_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for reload command"""
        self._update_available_cogs()
        choices = [app_commands.Choice(name="📦 All Cogs", value="all")]
        choices.extend(self.available_cogs)
        return choices

    @app_commands.command(name="status", description="📊 Show bot status")
    async def status(self, interaction: discord.Interaction):
        """Show bot status"""
        try:
            if not await self._check_dev_permission(interaction):
                return
                
            await self._handle_status(interaction)
        except Exception as e:
            await self.handle_error(interaction, e)

    @app_commands.command(name="cleanup", description="🧹 Cleanup old commands")
    async def cleanup(self, interaction: discord.Interaction):
        """Cleanup old commands"""
        try:
            if not await self._check_dev_permission(interaction):
                return
                
            await self._handle_cleanup(interaction)
        except Exception as e:
            await self.handle_error(interaction, e)

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

    async def _handle_reload(self, interaction: discord.Interaction, cog_name: Optional[str] = None) -> None:
        """จัดการคำสั่ง reload cogs"""
        if not cog_name:
            raise ValueError("กรุณาระบุชื่อ cog ที่ต้องการ reload\nตัวอย่าง: `dev reload commands`")
            
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Map of cog display names to actual paths
            cog_paths = {
                "all": None,  # Special case for reloading all
                "commands": "src.cogs.commands",
                "events": "src.cogs.event_handler",
                "dev": "src.cogs.dev_tools",
                # เพิ่ม cogs อื่นๆ ตามต้องการ
            }
            
            if cog_name.lower() == "all":
                # Reload ทุก cog
                reloaded = []
                failed = []
                
                for cog_display, cog_path in cog_paths.items():
                    if cog_display == "all":  # ข้าม key "all"
                        continue
                    try:
                        await self.bot.reload_extension(cog_path)
                        reloaded.append(cog_display)
                    except Exception as e:
                        failed.append(f"{cog_display} ({str(e)})")
                        
                status = "✅ Reload ทุก cog สำเร็จ" if not failed else "⚠️ Reload บาง cog ไม่สำเร็จ"
                description = []
                if reloaded:
                    description.append(f"**สำเร็จ ({len(reloaded)})**: {', '.join(reloaded)}")
                if failed:
                    description.append(f"**ไม่สำเร็จ ({len(failed)})**: {', '.join(failed)}")
                    
            else:
                # Reload cog เดียว
                cog_path = cog_paths.get(cog_name.lower())
                if not cog_path:
                    raise ValueError(f"ไม่พบ cog ชื่อ '{cog_name}'\nCogs ที่มี: {', '.join(k for k in cog_paths.keys() if k != 'all')}")
                
                await self.bot.reload_extension(cog_path)
                status = f"✅ Reload {cog_name} สำเร็จ"
                description = [f"Reload cog: `{cog_path}`"]
                
            embed = (
                EmbedBuilder()
                .set_title("🔄 Reload Cogs", emoji=status.split()[0])
                .set_description("\n".join(description))
                .set_color("success" if "สำเร็จ" in status else "warning")
                .set_footer(f"Requested by {interaction.user}")
                .build()
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"🔄 {status}")
            
        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดใน reload: {str(e)}")
            raise

    @reload.autocomplete('cog')
    async def reload_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for reload command"""
        choices = [
            app_commands.Choice(name="📦 All Cogs", value="all"),
            app_commands.Choice(name="🎮 Commands", value="commands"),
            app_commands.Choice(name="🎯 Events", value="events"),
            app_commands.Choice(name="🛠️ Developer Tools", value="dev"),
            # เพิ่ม cogs อื่นๆ ตามต้องการ
        ]
        return choices

    async def _handle_status(self, interaction: discord.Interaction) -> None:
        """จัดการคำสั่ง status"""
        await self._show_loading(interaction, "กำลังรวบรวมข้อมูลสถานะ...")
        status_embed = await self._create_status_embed()
        await self._safe_respond(interaction, embed=status_embed)

    async def _handle_cleanup(self, interaction: discord.Interaction) -> None:
        """จัดการคำสั่ง cleanup"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            old_count = len(self.bot.tree.get_commands())
            
# ลบคำสั่งเก่า
            self.bot.tree.clear_commands(guild=interaction.guild)
            await self.bot.tree.sync(guild=interaction.guild)
            
            new_count = len(self.bot.tree.get_commands())
            deleted = old_count - new_count
            
            embed = (
                EmbedBuilder()
                .set_title("ลบคำสั่งเก่า", emoji="✅")
                .set_description(f"ลบคำสั่งเก่าแล้ว {deleted} คำสั่ง")
                .set_color("success")
                .set_footer(f"จำนวนคำสั่งปัจจุบัน: {new_count}")
                .build()
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"🧹 ลบคำสั่งเก่าแล้ว {deleted} คำสั่ง")
            
        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในการลบคำสั่งเก่า: {str(e)}")
            raise

    async def _check_dev_permission(self, interaction: discord.Interaction) -> bool:
        """ตรวจสอบสิทธิ์ dev"""
        try:
            if not await self.bot.is_owner(interaction.user):
                raise PermissionError("คำสั่งนี้ใช้ได้เฉพาะ developer เท่านั้น")
            return True
        except Exception as e:
            await self.handle_error(interaction, e)
            return False

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

    @commands.Cog.listener()
    async def on_ready(self):
        """เมื่อบอทพร้อมใช้งาน"""
        self._ready = True
        logger.info("✅ DevTools พร้อมใช้งานแล้ว")

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