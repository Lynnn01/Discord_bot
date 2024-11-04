# commands/ping_command.py

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
import discord
import logging
from src.commands.base_command import BaseCommand
from src.utils.embed_builder import EmbedBuilder  # แก้ path import

logger = logging.getLogger(__name__)


@dataclass
class StatusInfo:
    """ข้อมูลสถานะการเชื่อมต่อ"""
    status: str  # เปลี่ยนจาก color เป็น status
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
                status="success",
                emoji=self.ui.EMOJI["success"],
                description="การเชื่อมต่อดีมาก"
            ),
            200: StatusInfo(
                status="warning",
                emoji=self.ui.EMOJI["warning"],
                description="การเชื่อมต่อปานกลาง"
            ),
            float("inf"): StatusInfo(
                status="error",
                emoji=self.ui.EMOJI["error"],
                description="การเชื่อมต่อช้า"
            ),
        }

    def _get_status_info(self, latency: int) -> StatusInfo:
        """ประเมินสถานะการเชื่อมต่อ"""
        for threshold, info in self.LATENCY_THRESHOLDS.items():
            if latency <= threshold:
                return info
        return self.LATENCY_THRESHOLDS[float("inf")]

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
        """สร้าง embed สำหรับการตอบกลับ"""
        status_info = self._get_status_info(latency)
        uptime = self._format_uptime(bot_start_time)

        return (
            EmbedBuilder()
            .set_title("Pong!", emoji=self.ui.EMOJI["ping"])
            .set_description(f"{self.ui.EMOJI['stats']} ผลการตรวจสอบการเชื่อมต่อและสถานะระบบ")
            .set_color(self.ui.COLORS[status_info.status])
            .add_field(
                name="การตอบสนอง",
                value=f"`{latency}ms`",
                emoji=self.ui.EMOJI["ping"],
                inline=True
            )
            .add_field(
                name="สถานะ",
                value=f"{status_info.emoji} {status_info.description}",
                emoji=self.ui.EMOJI["info"],
                inline=True
            )
            .add_field(
                name="เวลาทำงาน",
                value=uptime,
                emoji=self.ui.EMOJI["time"],
                inline=True
            )
            .add_field(
                name="สถิติการใช้งาน",
                value=stats.format_stats(),
                emoji=self.ui.EMOJI["stats"],
                inline=False
            )
            .set_footer(
                text=f"ตรวจสอบโดย {user.name}",
                emoji=self.ui.EMOJI["search"]
            )
            .set_timestamp()
            .build()
        )
