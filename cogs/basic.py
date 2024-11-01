import discord
from discord import app_commands
from discord.ext import commands
import random
from datetime import datetime
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from functools import lru_cache

# ใช้ logger จากระบบใหม่
logger = logging.getLogger(__name__)


@dataclass
class StatusInfo:
    """Class สำหรับเก็บข้อมูลสถานะ"""

    color: discord.Color
    emoji: str
    description: str


class Basic(commands.Cog):
    """Cog สำหรับคำสั่งพื้นฐาน เช่น roll และ ping"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot_start_time = datetime.utcnow()
        self._command_stats: Dict[str, int] = {"roll": 0, "ping": 0}

        # ค่าคงที่สำหรับสถานะการเชื่อมต่อ
        self.LATENCY_THRESHOLDS = {
            100: StatusInfo(discord.Color.green(), "🟢", "การเชื่อมต่อดีมาก"),
            200: StatusInfo(discord.Color.yellow(), "🟡", "การเชื่อมต่อปานกลาง"),
            float("inf"): StatusInfo(discord.Color.red(), "🔴", "การเชื่อมต่อช้า"),
        }

        # สีสำหรับผลการทอยลูกเต๋า
        self.ROLL_COLORS = {
            20: discord.Color.gold(),  # Critical success
            15: discord.Color.green(),  # High roll
            10: discord.Color.blue(),  # Medium roll
            5: discord.Color.greyple(),  # Low roll
            1: discord.Color.red(),  # Critical fail
        }

    async def cog_load(self) -> None:
        """เรียกเมื่อ cog ถูกโหลด"""
        logger.info("✅ Basic cog ถูกโหลดและพร้อมใช้งาน")

    async def cog_unload(self) -> None:
        """เรียกเมื่อ cog ถูกยกเลิกการโหลด"""
        logger.info(f"🔄 Basic cog ถูกยกเลิกการโหลด - สถิติการใช้งาน: {self._command_stats}")

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        """จัดการข้อผิดพลาดของ slash commands ที่ดีขึ้น"""
        error_messages = {
            app_commands.CommandOnCooldown: f"⏳ กรุณารอ {error.retry_after:.1f} วินาที",
            app_commands.MissingPermissions: "🚫 คุณไม่มีสิทธิ์ใช้คำสั่งนี้",
            app_commands.BotMissingPermissions: "⚠️ บอทไม่มีสิทธิ์ที่จำเป็น",
            app_commands.CommandNotFound: "❓ ไม่พบคำสั่งนี้",
        }

        response = error_messages.get(type(error), "❌ เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง")

        # ส่งข้อความแจ้งเตือน
        await interaction.response.send_message(response, ephemeral=True)

        # บันทึกข้อผิดพลาดสำหรับการแก้ไข
        logger.error(f"🐛 เกิดข้อผิดพลาดในคำสั่ง {interaction.command.name}: {str(error)}")

        # เพิ่มสถิติข้อผิดพลาด
        if hasattr(self.bot, "stats"):
            self.bot.stats["errors_caught"] += 1

    @app_commands.command(name="roll", description="🎲 ทอยลูกเต๋า D20")
    @app_commands.checks.cooldown(1, 3.0)
    async def roll(self, interaction: discord.Interaction):
        """ทอยลูกเต๋า D20 พร้อมเอฟเฟกต์พิเศษ"""
        try:
            # เพิ่มสถิติการใช้งาน
            self._command_stats["roll"] += 1

            # ทอยลูกเต๋า
            roll_value = random.randint(1, 20)

            # สร้าง embed
            emoji = self._get_roll_emoji(roll_value)
            embed = await self._create_roll_embed(roll_value, emoji, interaction.user)

            # ส่งผลลัพธ์
            await interaction.response.send_message(embed=embed)

            # บันทึกล็อก
            logger.debug(f"🎲 ผู้ใช้ {interaction.user} ทอยได้ {roll_value}")

        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในคำสั่ง roll: {str(e)}")
            await self._send_error_message(interaction)

    @app_commands.command(name="ping", description="🏓 เช็คการตอบสนองของบอท")
    @app_commands.checks.cooldown(1, 5.0)
    async def ping(self, interaction: discord.Interaction):
        """แสดงข้อมูลการตอบสนองและสถานะของบอท"""
        try:
            # เพิ่มสถิติการใช้งาน
            self._command_stats["ping"] += 1

            # คำนวณ latency
            latency = round(self.bot.latency * 1000)

            # สร้างและส่ง embed
            embed = await self._create_ping_embed(latency, interaction.user)
            await interaction.response.send_message(embed=embed)

            # บันทึกล็อก
            logger.debug(
                f"🏓 Ping command - Latency: {latency}ms จากผู้ใช้ {interaction.user}"
            )

        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในคำสั่ง ping: {str(e)}")
            await self._send_error_message(interaction)

    @lru_cache(maxsize=128)
    def _get_roll_color(self, roll: int) -> discord.Color:
        """คำนวณสีตามค่าที่ทอยได้ (cached)"""
        for threshold, color in sorted(self.ROLL_COLORS.items(), reverse=True):
            if roll >= threshold:
                return color
        return discord.Color.greyple()

    def _get_roll_emoji(self, roll: int) -> str:
        """กำหนด emoji ตามค่าที่ทอยได้"""
        emoji_map = {
            20: "🌟",  # Critical success
            1: "💥",  # Critical fail
            15: "✨",  # High roll
            10: "🎲",  # Medium roll
            5: "🎯",  # Low roll
        }
        for threshold, emoji in sorted(emoji_map.items(), reverse=True):
            if roll >= threshold:
                return emoji
        return "🎲"

    def _get_status_info(self, latency: int) -> StatusInfo:
        """หาข้อมูลสถานะจากค่า latency"""
        for threshold, info in sorted(self.LATENCY_THRESHOLDS.items()):
            if latency < threshold:
                return info
        return self.LATENCY_THRESHOLDS[float("inf")]

    async def _create_roll_embed(
        self, roll: int, emoji: str, user: discord.User
    ) -> discord.Embed:
        """สร้าง embed สำหรับคำสั่ง roll"""
        embed = discord.Embed(
            title=f"{emoji} ผลการทอยลูกเต๋า D20", color=self._get_roll_color(roll)
        )

        # เพิ่มผลการทอย
        embed.add_field(name="🎯 ผลที่ได้", value=f"**{roll}**", inline=False)

        # เพิ่มข้อความพิเศษ
        if roll == 20:
            embed.add_field(
                name="🎉 Critical Success!", value="ทอยได้ค่าสูงสุด! โชคดีมาก!", inline=False
            )
        elif roll == 1:
            embed.add_field(
                name="💔 Critical Fail!", value="ทอยได้ค่าต่ำสุด! โชคร้ายจัง!", inline=False
            )
        elif roll >= 15:
            embed.add_field(name="✨ Great Roll!", value="ทอยได้ค่าสูง!", inline=False)

        embed.set_footer(text=f"🎲 ทอยโดย {user.name}")
        embed.timestamp = discord.utils.utcnow()

        return embed

    async def _create_ping_embed(
        self, latency: int, user: discord.User
    ) -> discord.Embed:
        """สร้าง embed สำหรับคำสั่ง ping"""
        status_info = self._get_status_info(latency)
        uptime = self._format_uptime()

        embed = discord.Embed(
            title="🏓 Pong!",
            description="📊 ผลการตรวจสอบการเชื่อมต่อและสถานะระบบ",
            color=status_info.color,
        )

        # เพิ่มข้อมูลหลัก
        embed.add_field(name="🚀 การตอบสนอง", value=f"`{latency}ms`", inline=True)
        embed.add_field(
            name="📡 สถานะ",
            value=f"{status_info.emoji} {status_info.description}",
            inline=True,
        )
        embed.add_field(name="⏰ เวลาทำงาน", value=uptime, inline=True)

        # เพิ่มสถิติ
        stats = self._get_bot_stats()
        embed.add_field(name="📊 สถิติการใช้งาน", value=stats, inline=False)

        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text=f"🔍 ตรวจสอบโดย {user.name}")

        return embed

    def _format_uptime(self) -> str:
        """แปลงเวลา uptime เป็นข้อความภาษาไทย"""
        uptime = datetime.utcnow() - self.bot_start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days} วัน")
        if hours > 0:
            parts.append(f"{hours} ชั่วโมง")
        if minutes > 0:
            parts.append(f"{minutes} นาที")
        parts.append(f"{seconds} วินาที")

        return " ".join(parts)

    def _get_bot_stats(self) -> str:
        """รวบรวมสถิติของบอท"""
        guild_count = len(self.bot.guilds)
        member_count = sum(g.member_count for g in self.bot.guilds)
        total_commands = sum(self._command_stats.values())

        return (
            f"🏢 เซิร์ฟเวอร์: {guild_count}\n"
            f"👥 ผู้ใช้: {member_count:,}\n"
            f"📝 จำนวนครั้งที่ใช้คำสั่ง: {total_commands:,}\n"
            f"🎲 Roll: {self._command_stats['roll']:,}\n"
            f"🏓 Ping: {self._command_stats['ping']:,}"
        )

    async def _send_error_message(self, interaction: discord.Interaction) -> None:
        """ส่งข้อความแจ้งเตือนเมื่อเกิดข้อผิดพลาด"""
        await interaction.response.send_message(
            "❌ เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง", ephemeral=True
        )


async def setup(bot: commands.Bot):
    """ฟังก์ชันสำหรับเพิ่ม cog เข้าไปในบอท"""
    await bot.add_cog(Basic(bot))
