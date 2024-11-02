# commands/ping_command.py

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
import discord
import logging
from .base_command import BaseCommand
from utils.embed_builder import EmbedBuilder

logger = logging.getLogger(__name__)


@dataclass
class StatusInfo:
    """ข้อมูลสถานะการเชื่อมต่อ"""

    color: discord.Color
    emoji: str
    description: str


@dataclass
class SystemStats:
    """สถิติของระบบ"""

    guild_count: int
    member_count: int
    total_commands: int
    command_stats: Dict[str, int]

    def format_stats(self) -> str:
        """แปลงสถิติเป็นข้อความ"""
        return (
            f"🏢 เซิร์ฟเวอร์: {self.guild_count}\n"
            f"👥 ผู้ใช้: {self.member_count:,}\n"
            f"📝 จำนวนครั้งที่ใช้คำสั่ง: {self.total_commands:,}\n"
            f"🎲 Roll: {self.command_stats['roll']:,}\n"
            f"🏓 Ping: {self.command_stats['ping']:,}"
        )


class PingCommand(BaseCommand):
    """คำสั่งสำหรับตรวจสอบการเชื่อมต่อและสถานะระบบ"""

    def __init__(self, bot):
        super().__init__(bot)
        self._setup_thresholds()

    def _setup_thresholds(self) -> None:
        """กำหนดเกณฑ์การประเมินความเร็วในการตอบสนอง"""
        self.LATENCY_THRESHOLDS = {
            100: StatusInfo(
                color=discord.Color.green(), emoji="🟢", description="การเชื่อมต่อดีมาก"
            ),
            200: StatusInfo(
                color=discord.Color.yellow(), emoji="🟡", description="การเชื่อมต่อปานกลาง"
            ),
            float("inf"): StatusInfo(
                color=discord.Color.red(), emoji="🔴", description="การเชื่อมต่อช้า"
            ),
        }

    async def execute(
        self,
        interaction: discord.Interaction,
        bot_start_time: datetime,
        command_stats: Dict[str, int],
    ) -> None:
        """
        ดำเนินการคำสั่ง ping

        Args:
            interaction: Discord interaction object
            bot_start_time: เวลาที่บอทเริ่มทำงาน
            command_stats: สถิติการใช้คำสั่งต่างๆ
        """
        try:
            command_stats["ping"] += 1
            latency = round(self.bot.latency * 1000)

            # สร้างและส่ง embed ด้วย EmbedBuilder
            embed = await self._create_response_embed(
                latency=latency,
                user=interaction.user,
                bot_start_time=bot_start_time,
                stats=self._collect_system_stats(command_stats),
            )
            await interaction.response.send_message(embed=embed)

            # บันทึกล็อก
            self._log_execution(interaction.user, latency)

        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในคำสั่ง ping: {str(e)}")
            error_embed = EmbedBuilder.create_error_embed(description=str(e))
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

    def _get_status_info(self, latency: int) -> StatusInfo:
        """หาข้อมูลสถานะจากค่า latency"""
        for threshold, info in sorted(self.LATENCY_THRESHOLDS.items()):
            if latency < threshold:
                return info
        return self.LATENCY_THRESHOLDS[float("inf")]

    def _format_uptime(self, start_time: datetime) -> str:
        """แปลงระยะเวลาทำงานเป็นข้อความ"""
        uptime = datetime.utcnow() - start_time
        components = []
        time_units = [
            ((uptime.seconds % 3600) // 60, "นาที"),
            (uptime.seconds % 60, "วินาที"),
        ]

        for value, unit in time_units:
            if value > 0 or not components:  # รวมหน่วยสุดท้ายเสมอ
                components.append(f"{value} {unit}")

        return " ".join(components)

    def _collect_system_stats(self, command_stats: Dict[str, int]) -> SystemStats:
        """รวบรวมสถิติของระบบ"""
        return SystemStats(
            guild_count=len(self.bot.guilds),
            member_count=sum(g.member_count for g in self.bot.guilds),
            total_commands=sum(command_stats.values()),
            command_stats=command_stats,
        )

    def _log_execution(self, user: discord.User, latency: int) -> None:
        """บันทึกล็อกการใช้งานคำสั่ง"""
        logger.debug(f"🏓 Ping command - Latency: {latency}ms จากผู้ใช้ {user}")

    async def _create_response_embed(
        self,
        latency: int,
        user: discord.User,
        bot_start_time: datetime,
        stats: SystemStats,
    ) -> discord.Embed:
        """สร้าง embed สำหรับการตอบกลับโดยใช้ EmbedBuilder"""
        status_info = self._get_status_info(latency)
        uptime = self._format_uptime(bot_start_time)

        # ใช้ EmbedBuilder ในการสร้าง embed
        return (
            EmbedBuilder()
            .set_title("Pong!", emoji="🏓")
            .set_description("📊 ผลการตรวจสอบการเชื่อมต่อและสถานะระบบ")
            .set_color(status_info.color)
            .add_field(
                name="การตอบสนอง", value=f"`{latency}ms`", emoji="🚀", inline=True
            )
            .add_field(
                name="สถานะ",
                value=f"{status_info.emoji} {status_info.description}",
                emoji="📡",
                inline=True,
            )
            .add_field(name="เวลาทำงาน", value=uptime, emoji="⏰", inline=True)
            .add_field(
                name="สถิติการใช้งาน", value=stats.format_stats(), emoji="📊", inline=False
            )
            .set_footer(text=f"ตรวจสอบโดย {user.name}", emoji="🔍")
            .set_timestamp()
            .build()
        )
