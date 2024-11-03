import discord
from discord.ext import commands
from discord import app_commands
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class DevTools(commands.Cog):
    """Cog สำหรับเครื่องมือพัฒนา"""

    def __init__(self, bot):
        self.bot = bot
        self.base_cogs = {
            "commands": "src.cogs.commands",
            "events": "src.cogs.event_handler",
            "dev": "src.cogs.dev_tools",
        }

    async def cog_load(self):
        """ตรวจสอบและลบคำสั่งซ้ำเมื่อโหลด cog"""
        try:
            # เช็คว่ามีคำสั่ง dev อยู่แล้วหรือไม่
            existing_command = self.bot.tree.get_command("dev")
            if existing_command:
                self.bot.tree.remove_command("dev")
                logger.info("🔄 Removed duplicate dev command")

                # Sync การเปลี่ยนแปลงทันที
                if self.bot.dev_mode and (dev_guild_id := os.getenv("DEV_GUILD_ID")):
                    guild = discord.Object(id=int(dev_guild_id))
                    await self.bot.tree.sync(guild=guild)
                else:
                    await self.bot.tree.sync()

            logger.info("✅ DevTools cog loaded")
        except Exception as e:
            logger.error(f"❌ Error during cog load: {e}")

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
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ คำสั่งนี้ใช้ได้เฉพาะ Developer เท่านั้น", ephemeral=True
            )
            return

        try:
            await interaction.response.defer(ephemeral=True)

            if action == "sync":
                await self._handle_sync(interaction, scope or "guild")
            elif action == "reload":
                await self._handle_reload(interaction, cog)

        except Exception as e:
            logger.error(f"Error in dev command: {e}")
            if not interaction.response.is_done():
                await interaction.followup.send(
                    f"❌ เกิดข้อผิดพลาด: {str(e)}", ephemeral=True
                )

    async def _handle_sync(self, interaction: discord.Interaction, scope: str):
        """จัดการการ sync commands"""
        try:
            if scope == "guild":
                dev_guild_id = os.getenv("DEV_GUILD_ID")
                if not dev_guild_id:
                    raise ValueError("ไม่พบ DEV_GUILD_ID ในการตั้งค่า")

                guild = discord.Object(id=int(dev_guild_id))

                # ล้าง commands เก่าก่อน
                self.bot.tree.clear_commands(guild=guild)
                # Copy global commands มาที่ guild
                self.bot.tree.copy_global_to(guild=guild)
                # Sync commands
                commands = await self.bot.tree.sync(guild=guild)

                logger.info(
                    f"🔄 Synced {len(commands)} commands to guild {dev_guild_id}"
                )

            else:  # global scope
                if self.bot.dev_mode:
                    raise ValueError("ไม่สามารถ sync แบบ global ในโหมด Development")

                # ล้างและ sync commands global
                self.bot.tree.clear_commands()
                commands = await self.bot.tree.sync()
                logger.info(f"🔄 Synced {len(commands)} commands globally")

            await interaction.followup.send(
                f"✅ Sync {len(commands)} commands สำเร็จ\n" f"📍 Scope: {scope}",
                ephemeral=True,
            )

        except Exception as e:
            logger.error(f"Error syncing commands: {e}")
            raise

    async def _handle_reload(
        self, interaction: discord.Interaction, cog_name: Optional[str]
    ):
        """จัดการการ reload cogs"""
        try:
            if cog_name:
                if cog_name not in self.base_cogs:
                    raise ValueError(f"ไม่พบ Cog '{cog_name}'")
                cogs_to_reload = [self.base_cogs[cog_name]]
            else:
                cogs_to_reload = list(self.base_cogs.values())

            reloaded = []
            for cog in cogs_to_reload:
                try:
                    await self.bot.reload_extension(cog)
                    reloaded.append(cog.split(".")[-1])
                    logger.info(f"🔄 Reloaded {cog}")
                except Exception as e:
                    logger.error(f"❌ Failed to reload {cog}: {e}")
                    raise

            await interaction.followup.send(
                f"✅ Reloaded successfully:\n"
                + "\n".join(f"• {cog}" for cog in reloaded),
                ephemeral=True,
            )

        except Exception as e:
            logger.error(f"Error reloading cogs: {e}")
            raise


async def setup(bot):
    await bot.add_cog(DevTools(bot))
