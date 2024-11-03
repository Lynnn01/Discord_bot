import discord
from discord.ext import commands
from discord import app_commands
import logging
import os
from typing import Literal, Optional, List, Dict
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)


class DevTools(commands.Cog):
    """Cog สำหรับเครื่องมือพัฒนา"""

    def __init__(self, bot):
        self.bot = bot
        self._last_sync = None
        self.old_commands = []  # เอาคำสั่ง sync และ reload ออก
        self._command_history = []
        self._max_history = 10
        self._dev_cache = {}
        self._dev_cache_timeout = timedelta(minutes=5)
        self._ready = False  # เพิ่มตัวแปรเช็คความพร้อม

    async def cleanup_old_commands(self):
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
                    except:
                        pass

                # ลบคำสั่ง global
                if not self.bot.dev_mode:
                    try:
                        cmd = self.bot.tree.get_command(cmd_name)
                        if cmd:
                            self.bot.tree.remove_command(cmd_name)
                            logger.info(f"✅ ลบคำสั่ง {cmd_name} global เรียบร้อย")
                    except:
                        pass

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
            self._ready = True
            await asyncio.sleep(1)  # รอให้ระบบพร้อมใช้งาน
            await self.cleanup_old_commands()
            logger.info("✅ DevTools ready and cleaned up old commands")

    async def cog_load(self):
        """เรียกใช้เมื่อ Cog ถูกโหลด"""
        logger.info("🔄 DevTools cog loaded")
        # ไม่ต้อง cleanup ที่นี่ จะทำใน on_ready แทน

    @app_commands.command(name="dev", description="คำสั่งสำหรับ Developer")
    @app_commands.describe(
        action="การดำเนินการ",
        scope="ขอบเขตการ sync (เฉพาะ sync)",
        cog="Cog ที่ต้องการ reload (เฉพ��ะ reload)",
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
        if not await self._check_dev_permission(interaction):
            return

        try:
            await interaction.response.defer(ephemeral=True)

            if not self._ready:
                await interaction.followup.send(
                    "⚠️ Bot is not ready yet. Please try again in a moment.",
                    ephemeral=True,
                )
                return

            if action == "sync":
                await self._handle_sync(interaction, scope or "guild")
            elif action == "reload":
                await self._handle_reload(interaction, cog)
            elif action == "status":
                await self._handle_status(interaction)
            elif action == "cleanup":
                await self.cleanup_old_commands()
                await interaction.followup.send(
                    "✅ Cleaned up old commands", ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in dev command: {e}")
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: {str(e)}", ephemeral=True)

    async def _handle_sync(self, interaction: discord.Interaction, scope: str):
        """จัดการการ sync commands"""
        try:
            if scope == "guild":
                dev_guild_id = os.getenv("DEV_GUILD_ID")
                if not dev_guild_id:
                    raise ValueError("ไม่พบ DEV_GUILD_ID ในการตั้งค่า")

                guild = discord.Object(id=int(dev_guild_id))
                self.bot.tree.copy_global_to(guild=guild)
                commands = await self.bot.tree.sync(guild=guild)

                sync_info = {
                    "scope": "guild",
                    "guild_id": dev_guild_id,
                    "count": len(commands),
                    "timestamp": discord.utils.utcnow(),
                }
            else:
                if self.bot.dev_mode:
                    raise ValueError("ไม่สามารถ sync แบบ global ในโหมด Development")

                commands = await self.bot.tree.sync()
                sync_info = {
                    "scope": "global",
                    "count": len(commands),
                    "timestamp": discord.utils.utcnow(),
                }

            self._last_sync = sync_info

            # สร้างข้อความตอบกลับ
            response = [
                f"✅ Sync {len(commands)} commands successfully",
                f"📍 Scope: {scope}",
                f"⏰ Time: {discord.utils.format_dt(sync_info['timestamp'], 'R')}",
            ]
            if scope == "guild":
                response.append(f"🏢 Guild ID: {dev_guild_id}")

            await interaction.followup.send("\n".join(response), ephemeral=True)
            logger.info(f"Commands synced ({scope}) by {interaction.user}")

        except Exception as e:
            logger.error(f"Error syncing commands: {e}")
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
            if cog_name:
                if cog_name not in base_cogs:
                    raise ValueError(f"ไม่พบ Cog '{cog_name}'")
                cogs_to_reload = [base_cogs[cog_name]]
            else:
                cogs_to_reload = base_cogs.values()

            # Reload cogs
            reloaded = []
            for cog in cogs_to_reload:
                await self.bot.reload_extension(cog)
                reloaded.append(cog.split(".")[-1])
                logger.info(f"Reloaded {cog}")

            await interaction.followup.send(
                f"✅ Reloaded successfully:\n"
                + "\n".join(f"• {cog}" for cog in reloaded),
                ephemeral=True,
            )
            logger.info(f"Cogs reloaded by {interaction.user}")

        except Exception as e:
            logger.error(f"Error reloading cogs: {e}")
            raise

    async def _handle_status(self, interaction: discord.Interaction):
        """แสดงสถานะของระบบ"""
        status_embed = discord.Embed(
            title="🛠️ Developer Status", color=discord.Color.blue()
        )

        # Bot Info
        uptime = (
            datetime.utcnow() - self.bot.start_time
            if hasattr(self.bot, "start_time")
            else None
        )
        status_embed.add_field(
            name="🤖 Bot Info",
            value=f"```\n"
            f"Mode: {'Development' if self.bot.dev_mode else 'Production'}\n"
            f"Guilds: {len(self.bot.guilds)}\n"
            f"Commands: {len(self.bot.tree.get_commands())}\n"
            f"Uptime: {str(uptime).split('.')[0] if uptime else 'N/A'}\n"
            f"```",
            inline=False,
        )

        # Last Sync
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
        memory_usage = self.bot.process.memory_info().rss / 1024 / 1024  # Convert to MB
        status_embed.add_field(
            name="💻 System Stats",
            value=f"```\n"
            f"Memory Usage: {memory_usage:.1f} MB\n"
            f"Commands Used: {self.bot.stats['commands_used']}\n"
            f"Errors Caught: {self.bot.stats['errors_caught']}\n"
            f"Messages Processed: {self.bot.stats['messages_processed']}\n"
            f"```",
            inline=False,
        )

        # Recent Activity
        if self._command_history:
            recent_commands = "\n".join(
                f"• {entry['user']}: {entry['action']} "
                f"({discord.utils.format_dt(entry['timestamp'], 'R')})"
                for entry in reversed(self._command_history[-5:])  # แสดง 5 รายการล่าสุด
            )
            status_embed.add_field(
                name="📝 Recent Activity", value=recent_commands, inline=False
            )

        # Dev Permissions Cache
        cached_devs = sum(
            1
            for _, (time, is_dev) in self._dev_cache.items()
            if datetime.utcnow() - time < self._dev_cache_timeout and is_dev
        )
        status_embed.set_footer(text=f"🔑 Cached Dev Permissions: {cached_devs}")
        await interaction.followup.send(embed=status_embed, ephemeral=True)

    async def _get_bot_process_info(self) -> Dict:
        """รวบรวมข้อมูลการทำงานของบอท"""
        try:
            process = self.bot.process
            with process.oneshot():
                cpu_percent = process.cpu_percent(interval=0.1)
                memory_info = process.memory_info()
                threads = process.num_threads()

            return {
                "cpu_percent": cpu_percent,
                "memory_mb": memory_info.rss / 1024 / 1024,
                "threads": threads,
                "pid": process.pid,
            }
        except Exception as e:
            logger.error(f"Error getting process info: {e}")
            return {}

    async def _clear_dev_cache(self):
        """ล้าง cache การตรวจสอบ developer ที่หมดอายุ"""
        current_time = datetime.utcnow()
        expired_keys = [
            user_id
            for user_id, (cache_time, _) in self._dev_cache.items()
            if current_time - cache_time >= self._dev_cache_timeout
        ]
        for user_id in expired_keys:
            del self._dev_cache[user_id]

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """จัดการเมื่อมีการใช้งาน interaction"""
        if interaction.command:
            # เพิ่มสถิติการใช้คำสั่ง
            self.bot.stats["commands_used"] += 1

            # ล้าง cache ที่หมดอายุ
            await self._clear_dev_cache()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """จัดการมื่อบอทถูกเชิญเข้า guild ใหม่"""
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
            # บันทึกข้อมูลที่สำคัญก่อน unload
            logger.info("💾 Saving important data before unload...")

            # ล้าง cache
            self._dev_cache.clear()
            self._command_history.clear()

            logger.info("👋 DevTools cog unloaded successfully")

        except Exception as e:
            logger.error(f"❌ Error during cog unload: {e}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """จัดการข้อผิดพลาดของคำสั่ง"""
        self.bot.stats["errors_caught"] += 1

        if isinstance(error, commands.errors.CommandInvokeError):
            error = error.original

        # บันทึกข้อผิดพลาด
        logger.error(f"Command error: {str(error)}", exc_info=error)

        # แจ้งข้อผิดพลาดให้ developer ทราบถ้าอยู่ใน dev mode
        if self.bot.dev_mode:
            dev_guild_id = os.getenv("DEV_GUILD_ID")
            if dev_guild_id:
                try:
                    dev_guild = self.bot.get_guild(int(dev_guild_id))
                    if dev_guild:
                        # สร้าง embed แจ้งข้อผิดพลาด
                        error_embed = discord.Embed(
                            title="⚠️ Command Error",
                            description=f"```py\n{str(error)}\n```",
                            color=discord.Color.red(),
                        )
                        error_embed.add_field(
                            name="Command",
                            value=f"`{ctx.command.name if ctx.command else 'Unknown'}`",
                        )
                        error_embed.add_field(
                            name="User", value=f"{ctx.author} ({ctx.author.id})"
                        )
                        error_embed.add_field(
                            name="Guild",
                            value=f"{ctx.guild.name if ctx.guild else 'DM'}",
                        )

                        # หาช่องสำหรับส่งข้อผิดพลาด
                        error_channel = discord.utils.get(
                            dev_guild.text_channels, name="bot-errors"
                        )
                        if error_channel:
                            await error_channel.send(embed=error_embed)

                except Exception as e:
                    logger.error(f"Error sending error notification: {e}")

    async def _check_dev_permission(self, interaction: discord.Interaction) -> bool:
        """
        ตรวจสอบสิทธิ์ developer

        Args:
            interaction: Discord interaction object

        Returns:
            bool: True ถ้ามีสิทธิ์ developer
        """
        try:
            user_id = interaction.user.id
            current_time = datetime.utcnow()

            # ตรวจสอบ cache
            if user_id in self._dev_cache:
                cache_time, is_dev = self._dev_cache[user_id]
                if current_time - cache_time < self._dev_cache_timeout:
                    return is_dev

            # ตรวจสอบเจ้าของบอท
            is_dev = await self.bot.is_owner(interaction.user)

            # ถ้าไม่ใช่เจ้าของ ให้ตรวจสอบเพิ่มเติม
            if not is_dev and self.bot.dev_mode:
                dev_guild_id = os.getenv("DEV_GUILD_ID")
                if dev_guild_id and str(interaction.guild_id) == dev_guild_id:
                    # ตรวจสอบบทบาท Developer
                    dev_roles = {"Developer", "Admin", "Owner"}
                    member = interaction.guild.get_member(user_id)
                    if member:
                        user_roles = {role.name for role in member.roles}
                        is_dev = bool(user_roles & dev_roles)

            # เก็บผลลัพธ์ใน cache
            self._dev_cache[user_id] = (current_time, is_dev)

            # แจ้งเตือนถ้าไม่มีสิทธิ์
            if not is_dev:
                await interaction.response.send_message(
                    "❌ คำสั่งนี้ใช้ได้เฉพาะ Developer เ���่านั้น", ephemeral=True
                )
                logger.warning(f"🚫 ผู้ใช้ {interaction.user} พยายามใช้คำสั่ง dev โดยไม่มีสิทธิ์")
            else:
                # บันทึกประวัติถ้ามีสิทธิ์
                self._add_command_history(
                    interaction.user, "dev permission check", True
                )

            return is_dev

        except Exception as e:
            logger.error(f"❌ Error checking dev permission: {e}")
            await interaction.response.send_message(
                "❌ เกิดข้อผิดพลาดในการตรวจสอบสิทธิ์", ephemeral=True
            )
            return False

    def _add_command_history(self, user: discord.User, action: str, success: bool):
        """เพิ่มประวัติการใช้คำสั่ง"""
        try:
            self._command_history.append(
                {
                    "user": f"{user.name}#{user.discriminator}",
                    "user_id": user.id,
                    "action": action,
                    "success": success,
                    "timestamp": datetime.utcnow(),
                }
            )

            # จำกัดขนาดประวัติ
            if len(self._command_history) > self._max_history:
                self._command_history.pop(0)
        except Exception as e:
            logger.error(f"❌ Error adding command history: {e}")


async def setup(bot):
    await bot.add_cog(DevTools(bot))
