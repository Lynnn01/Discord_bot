from .base_command import BaseCommand
import discord
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


@dataclass
class StatusInfo:
    color: discord.Color
    emoji: str
    description: str


class PingCommand(BaseCommand):
    def __init__(self, bot):
        super().__init__(bot)
        self.LATENCY_THRESHOLDS = {
            100: StatusInfo(discord.Color.green(), "🟢", "การเชื่อมต่อดีมาก"),
            200: StatusInfo(discord.Color.yellow(), "🟡", "การเชื่อมต่อปานกลาง"),
            float("inf"): StatusInfo(discord.Color.red(), "🔴", "การเชื่อมต่อช้า"),
        }

    async def execute(
        self,
        interaction: discord.Interaction,
        bot_start_time: datetime,
        command_stats: Dict[str, int],
    ):
        """จัดการคำสั่ง ping"""
        try:
            # เพิ่มสถิติและเตรียมข้อมูล
            command_stats["ping"] += 1
            latency = round(self.bot.latency * 1000)

            # สร้าง embed และส่งผลลัพธ์
            embed = await self._create_ping_embed(
                latency, interaction.user, bot_start_time, command_stats
            )
            await interaction.response.send_message(embed=embed)

            # บันทึกล็อก
            self._log_ping_execution(interaction.user, latency)

        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในคำสั่ง ping: {str(e)}")
            await self._send_error_message(interaction)

    def _get_status_info(self, latency: int) -> StatusInfo:
        """หาข้อมูลสถานะจากค่า latency"""
        for threshold, info in sorted(self.LATENCY_THRESHOLDS.items()):
            if latency < threshold:
                return info
        return self.LATENCY_THRESHOLDS[float("inf")]

    def _get_uptime_parts(self, bot_start_time: datetime) -> Tuple[int, int, int, int]:
        """คำนวณส่วนประกอบของ uptime"""
        uptime = datetime.utcnow() - bot_start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return days, hours, minutes, seconds

    def _format_uptime(self, bot_start_time: datetime) -> str:
        """แปลงเวลา uptime เป็นข้อความภาษาไทย"""
        days, hours, minutes, seconds = self._get_uptime_parts(bot_start_time)

        parts = []
        if days > 0:
            parts.append(f"{days} วัน")
        if hours > 0:
            parts.append(f"{hours} ชั่วโมง")
        if minutes > 0:
            parts.append(f"{minutes} นาที")
        parts.append(f"{seconds} วินาที")

        return " ".join(parts)

    def _get_guild_stats(self) -> Tuple[int, int]:
        """คำนวณสถิติของ guild และจำนวนสมาชิก"""
        guild_count = len(self.bot.guilds)
        member_count = sum(g.member_count for g in self.bot.guilds)
        return guild_count, member_count

    def _get_bot_stats(self, command_stats: Dict[str, int]) -> str:
        """รวบรวมสถิติของบอท"""
        guild_count, member_count = self._get_guild_stats()
        total_commands = sum(command_stats.values())

        return (
            f"🏢 เซิร์ฟเวอร์: {guild_count}\n"
            f"👥 ผู้ใช้: {member_count:,}\n"
            f"📝 จำนวนครั้งที่ใช้คำสั่ง: {total_commands:,}\n"
            f"🎲 Roll: {command_stats['roll']:,}\n"
            f"🏓 Ping: {command_stats['ping']:,}"
        )

    def _log_ping_execution(self, user: discord.User, latency: int) -> None:
        """บันทึกล็อกการใช้งานคำสั่ง ping"""
        logger.debug(f"🏓 Ping command - Latency: {latency}ms จากผู้ใช้ {user}")

    async def _create_ping_embed(
        self,
        latency: int,
        user: discord.User,
        bot_start_time: datetime,
        command_stats: Dict[str, int],
    ) -> discord.Embed:
        """สร้าง embed สำหรับคำสั่ง ping"""
        status_info = self._get_status_info(latency)
        uptime = self._format_uptime(bot_start_time)

        # สร้าง embed หลัก
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
        stats = self._get_bot_stats(command_stats)
        embed.add_field(name="📊 สถิติการใช้งาน", value=stats, inline=False)

        # เพิ่ม timestamp และ footer
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text=f"🔍 ตรวจสอบโดย {user.name}")

        return embed
