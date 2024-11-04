import discord
from discord.ext import commands
from discord import app_commands
import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import asyncio
import psutil  # สำหรับเก็บข้อมูลระบบ

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
        self.old_commands = []  # เก็บคำสั่งเก่าที่จะลบ
        self.process = psutil.Process()

        # ตั้งค่าเริ่มต้นสำหรับ stats
        if not hasattr(bot, "stats"):
            bot.stats = {
                "commands_used": 0,
                "errors_caught": 0,
                "messages_processed": 0,
            }

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
        """เรียกใช้เมื่อ Cog ���ูกโหลด"""
        logger.info("🔄 DevTools cog loading...")
        if hasattr(self.bot, "stats"):
            self.bot.stats.setdefault("commands_used", 0)
            self.bot.stats.setdefault("errors_caught", 0)
            self.bot.stats.setdefault("messages_processed", 0)
        logger.info("✅ DevTools cog loaded successfully")

    @app_commands.command(name="dev", description="คำสั่งสำหรับ Developer")
    @app_commands.describe(
        action="การดำเนินการ",
        scope="ขอบเขตการ sync (เฉพาะ sync)",
        cog="Cog ที่ต้องการ reload (เฉพาะ reload)",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Sync Commands", value="sync"),
            app_commands.Choice(name="Reload Cogs", value="reload"),
            app_commands.Choice(name="Show Status", value="status"),
            app_commands.Choice(name="Cleanup Commands", value="cleanup"),
        ],
        scope=[
            app_commands.Choice(name="Global", value="global"),
            app_commands.Choice(name="Guild", value="guild"),
        ],
    )
    @app_commands.default_permissions(administrator=True)
    async def dev_command(
        self,
        interaction: discord.Interaction,
        action: str,
        scope: Optional[str] = None,
        cog: Optional[str] = None,
    ):
        """คำสั่งรวมสำหรับ Developer"""
        # ตรวจสอบสิทธิ์ก่อนดำเนินการ
        if not await self._check_dev_permission(interaction):
            return

        try:
            await interaction.response.defer(ephemeral=True)

            # ตรวจสอบความพร้อมของระบบ
            if not self._ready and action not in ["sync", "status"]:
                await interaction.followup.send(
                    "⚠️ Bot กำลังเริ่มต้นระบบ กรุณารอสักครู่...\n"
                    "หมายเหตุ: คำสั่ง sync และ status สามารถใช้งานได้ระหว่างเริ่มต้นระบบ",
                    ephemeral=True,
                )
                return

            # เลือกฟังก์ชันจัดการตามคำสั่ง
            handlers = {
                "sync": lambda: self._handle_sync(interaction, scope or "guild"),
                "reload": lambda: self._handle_reload(interaction, cog),
                "status": lambda: self._handle_status(interaction),
                "cleanup": lambda: self._handle_cleanup(interaction),
            }

            if action in handlers:
                await handlers[action]()
                self._history.add(interaction.user, action, True)
            else:
                await interaction.followup.send("❌ Invalid action", ephemeral=True)

        except Exception as e:
            logger.error(f"Error in dev command: {e}")
            self._history.add(interaction.user, action, False)
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: {str(e)}", ephemeral=True)

    async def _handle_sync(self, interaction: discord.Interaction, scope: str):
        """จัดการการ sync commands โดยป้องกันคำสั่งซ้ำซ้อน"""
        try:
            # ตรวจสอบ scope และ guild ID
            if scope == "guild":
                dev_guild_id = os.getenv("DEV_GUILD_ID")
                if not dev_guild_id:
                    raise ValueError("ไม่พบ DEV_GUILD_ID ในการตั้งค่า")
                guild = discord.Object(id=int(dev_guild_id))
            else:
                if self.bot.dev_mode:
                    raise ValueError("ไม่สามารถ sync แบบ global ในโหมด Development")
                guild = None

            # ดึงข้อมูล commands ทั้งหมดที่มีอยู่
            current_commands = {}  # Dict เก็บ command ปัจจุบันแยกตามชื่อ
            if guild:
                for cmd in self.bot.tree.get_commands(guild=guild):
                    current_commands[cmd.name] = cmd
            else:
                for cmd in self.bot.tree.get_commands():
                    current_commands[cmd.name] = cmd

            # ลบ commands ทั้งหมดออกก่อน
            logger.info(f"Removing {len(current_commands)} existing commands...")
            for cmd_name in current_commands:
                try:
                    if guild:
                        self.bot.tree.remove_command(cmd_name, guild=guild)
                        logger.debug(f"Removed guild command: {cmd_name}")
                    else:
                        self.bot.tree.remove_command(cmd_name)
                        logger.debug(f"Removed global command: {cmd_name}")
                except Exception as e:
                    logger.warning(f"Failed to remove command {cmd_name}: {e}")

            # รอสักครู่เพื่อให้ Discord API อัพเดท
            await asyncio.sleep(2)

            # Clear command tree cache
            self.bot.tree.clear_commands(guild=guild)

            # ตรวจสอบและเตรียม commands ใหม่
            new_commands = set()  # ใช้ set เพื่อป้องกันการซ้ำ
            if guild:
                # Copy global commands ไปยัง guild โดยตรวจสอบการซ้ำ
                for cmd in self.bot.tree._global_commands.values():
                    if cmd.name not in new_commands:
                        self.bot.tree.add_command(cmd, guild=guild)
                        new_commands.add(cmd.name)
                        logger.debug(f"Added command to guild: {cmd.name}")

            # Sync commands
            try:
                if guild:
                    commands = await self.bot.tree.sync(guild=guild)
                else:
                    commands = await self.bot.tree.sync()

                # ตรวจสอบความซ้ำซ้อนหลัง sync
                command_names = [cmd.name for cmd in commands]
                duplicates = [
                    name for name in command_names if command_names.count(name) > 1
                ]

                if duplicates:
                    logger.warning(
                        f"Found duplicate commands after sync: {set(duplicates)}"
                    )
                    # ถ้าพบการซ้ำซ้อน ให้ลองลบและ sync อีกครั้ง
                    for name in set(duplicates):
                        if guild:
                            self.bot.tree.remove_command(name, guild=guild)
                        else:
                            self.bot.tree.remove_command(name)

                    # Sync อีกครั้งหลังจากลบ duplicates
                    if guild:
                        commands = await self.bot.tree.sync(guild=guild)
                    else:
                        commands = await self.bot.tree.sync()

            except Exception as e:
                logger.error(f"Error during command sync: {e}")
                raise

            # บันทึกข้อมูลการ sync
            sync_info = {
                "scope": scope,
                "old_count": len(current_commands),
                "new_count": len(commands),
                "timestamp": discord.utils.utcnow(),
            }
            self._last_sync = sync_info

            # สร้าง embed response
            response = discord.Embed(
                title="✅ Sync Commands",
                description="ซิงค์คำสั่งเสร็จสมบูรณ์",
                color=discord.Color.green(),
            )
            response.add_field(
                name="การดำเนินการ",
                value=f"```\n"
                f"คำสั่งเดิม: {len(current_commands)}\n"
                f"คำสั่งใหม่: {len(commands)}\n"
                f"```",
                inline=False,
            )
            response.add_field(name="Scope", value=scope)
            response.add_field(
                name="เวลา", value=discord.utils.format_dt(sync_info["timestamp"], "R")
            )

            # เพิ่มรายชื่อคำสั่งทั้งหมด
            command_list = "\n".join(f"• /{cmd.name}" for cmd in commands)
            if command_list:
                response.add_field(
                    name="รายการคำสั่งที่ใช้งานได้",
                    value=command_list[:1024],  # จำกัดความยาวไม่เกิน 1024 ตัวอักษร
                    inline=False,
                )

            await interaction.followup.send(embed=response, ephemeral=True)
            logger.info(
                f"Commands synced ({scope}) by {interaction.user} "
                f"[Old: {len(current_commands)}, New: {len(commands)}]"
            )

        except Exception as e:
            logger.error(f"Error in command sync: {e}")
            raise

    async def _handle_reload(
        self, interaction: discord.Interaction, cog_name: Optional[str]
    ):
        """จัดการการ reload cogs"""
        base_cogs = {
            "commands": "src.cogs.commands",
            "events": "src.cogs.event_handler",
            "dev": "src.cogs.dev_tools",
        }

        try:
            if cog_name and cog_name not in base_cogs:
                raise ValueError(f"ไม่พบ Cog '{cog_name}'")

            cogs_to_reload = [base_cogs[cog_name]] if cog_name else base_cogs.values()
            reloaded = []

            for cog in cogs_to_reload:
                await self.bot.reload_extension(cog)
                reloaded.append(cog.split(".")[-1])
                logger.info(f"Reloaded {cog}")

            response = discord.Embed(
                title="✅ Reload Cogs",
                description="\n".join(f"• {cog}" for cog in reloaded),
                color=discord.Color.green(),
            )

            await interaction.followup.send(embed=response, ephemeral=True)
            logger.info(f"Cogs reloaded by {interaction.user}")

        except Exception as e:
            logger.error(f"Error reloading cogs: {e}")
            raise

    async def _handle_status(self, interaction: discord.Interaction):
        """แสดงสถานะของระบบ"""
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
            await interaction.followup.send(embed=status_embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error showing status: {e}")
            raise

    async def _handle_cleanup(self, interaction: discord.Interaction):
        """จัดการการล้างคำสั่งเก่า"""
        try:
            if not self._ready:
                await interaction.followup.send(
                    "⚠️ กำลังรอระบบเริ่มต้น ไม่สามารถล้างคำสั่งได้ในขณะนี้",
                    ephemeral=True,
                )
                return

            await self.cleanup_old_commands()
            embed = discord.Embed(
                title="✅ Cleanup Commands",
                description="ล้างคำสั่งเก่าเรียบร้อยแล้ว",
                color=discord.Color.green(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error cleaning up commands: {e}")
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
        """ตรวจสอบสิทธิ์ developer"""
        try:
            user_id = interaction.user.id

            # ตรวจสอบ cache ก่อน
            cached_result = self._dev_cache.get(user_id)
            if cached_result is not None:
                if not cached_result:
                    await interaction.response.send_message(
                        "❌ คำสั่งนี้ใช้ได้เฉพาะ Developer เท่านั้น", ephemeral=True
                    )
                return cached_result

            # ตรวจสอบเจ้าของบอท
            is_dev = await self.bot.is_owner(interaction.user)

            # ตรวจสอบเพิ่มเติมถ้าอยู่ใน dev mode
            if not is_dev and self.bot.dev_mode:
                dev_guild_id = os.getenv("DEV_GUILD_ID")
                if dev_guild_id and str(interaction.guild_id) == dev_guild_id:
                    member = interaction.guild.get_member(user_id)
                    if member:
                        dev_roles = {"Developer", "Admin", "Owner"}
                        user_roles = {role.name for role in member.roles}
                        is_dev = bool(user_roles & dev_roles)

            # บันทึกผลลัพธ์ลง cache
            self._dev_cache.set(user_id, is_dev)

            # แจ้งเตือนถ้าไม่มีสิทธิ์
            if not is_dev:
                await interaction.response.send_message(
                    "❌ คำสั่งนี้ใช้ได้เฉพาะ Developer เท่านั้น", ephemeral=True
                )
                logger.warning(f"🚫 ผู้ใช้ {interaction.user} พยายามใช้คำสั่ง dev โดยไม่มีสิทธิ์")

            return is_dev

        except Exception as e:
            logger.error(f"❌ Error checking dev permission: {e}")
            await interaction.response.send_message(
                "❌ เกิดข้อผิดพลาดในการตรวจสอบสิทธิ์", ephemeral=True
            )
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


async def setup(bot):
    await bot.add_cog(DevTools(bot))
