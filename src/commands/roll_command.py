# commands/roll_command.py

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import discord
import random
import logging
from functools import lru_cache
from .base_command import BaseCommand
from utils.embed_builder import EmbedBuilder

logger = logging.getLogger(__name__)


@dataclass
class DiceResult:
    """ผลลัพธ์การทอยลูกเต๋า"""

    value: int
    color: discord.Color
    emoji: str
    message: Optional[str] = None
    is_critical: bool = False


@dataclass
class RollThresholds:
    """เกณฑ์การประเมินผลการทอย"""

    COLORS: Dict[int, discord.Color]
    EMOJIS: Dict[int, str]
    MESSAGES: Dict[int, str]
    CRITICAL_VALUES: Tuple[int, ...]


class RollCommand(BaseCommand):
    """
    คำสั่งสำหรับทอยลูกเต๋า D20
    มีระบบแสดงผลพิเศษสำหรับการทอยได้ค่าพิเศษต่างๆ
    """

    def __init__(self, bot):
        super().__init__(bot)
        self.thresholds = self._setup_thresholds()
        self.dice_cache = {}

    def _setup_thresholds(self) -> RollThresholds:
        """กำหนดเกณฑ์ต่างๆ สำหรับการประเมินผลการทอย"""
        return RollThresholds(
            COLORS={
                20: discord.Color.gold(),  # Critical Success
                15: discord.Color.green(),  # Great Roll
                10: discord.Color.blue(),  # Good Roll
                5: discord.Color.greyple(),  # Normal Roll
                1: discord.Color.red(),  # Critical Fail
            },
            EMOJIS={
                20: "🌟",  # Critical Success
                15: "✨",  # Great Roll
                10: "🎲",  # Good Roll
                5: "🎯",  # Normal Roll
                1: "💥",  # Critical Fail
            },
            MESSAGES={
                20: "ทอยได้ค่าสูงสุด! โชคดีมาก!",
                15: "ทอยได้ค่าสูง!",
                10: "ทอยได้ค่าปานกลาง",
                5: "ทอยได้ค่าทั่วไป",
                1: "ทอยได้ค่าต่ำสุด! โชคร้ายจัง!",
            },
            CRITICAL_VALUES=(1, 20),
        )

    async def execute(self, interaction: discord.Interaction, command_stats: dict):
        """ดำเนินการคำสั่ง roll"""
        try:
            command_stats["roll"] += 1
            roll_value = self._roll_d20()
            result = self._evaluate_roll(roll_value)

            embed = await self._create_roll_embed(result, interaction.user)
            await interaction.response.send_message(embed=embed)

            self._log_roll(interaction.user, result)

        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในคำสั่ง roll: {str(e)}")
            error_embed = EmbedBuilder.create_error_embed(
                title="เกิดข้อผิดพลาดในการทอยลูกเต๋า", description=str(e)
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

    def _roll_d20(self) -> int:
        """ทอยลูกเต๋า D20"""
        return random.randint(1, 20)

    @lru_cache(maxsize=20)
    def _get_roll_color(self, roll: int) -> discord.Color:
        """หาสีที่เหมาะสมกับค่าที่ทอยได้"""
        for threshold, color in sorted(self.thresholds.COLORS.items(), reverse=True):
            if roll >= threshold:
                return color
        return discord.Color.greyple()

    def _get_roll_emoji(self, roll: int) -> str:
        """หา emoji ที่เหมาะสมกับค่าที่ทอยได้"""
        for threshold, emoji in sorted(self.thresholds.EMOJIS.items(), reverse=True):
            if roll >= threshold:
                return emoji
        return "🎲"

    def _evaluate_roll(self, roll: int) -> DiceResult:
        """ประเมินผลการทอยและสร้าง DiceResult"""
        return DiceResult(
            value=roll,
            color=self._get_roll_color(roll),
            emoji=self._get_roll_emoji(roll),
            message=self._get_roll_message(roll),
            is_critical=roll in self.thresholds.CRITICAL_VALUES,
        )

    def _get_roll_message(self, roll: int) -> Optional[str]:
        """หาข้อความที่เหมาะสมกับค่าที่ทอยได้"""
        for threshold, message in sorted(
            self.thresholds.MESSAGES.items(), reverse=True
        ):
            if roll >= threshold:
                return message
        return None

    def _log_roll(self, user: discord.User, result: DiceResult) -> None:
        """บันทึกล็อกผลการทอย"""
        status = "Critical!" if result.is_critical else "Normal"
        logger.debug(f"🎲 ผู้ใช้ {user} ทอยได้ {result.value} ({status})")

    def _get_roll_title(self, result: DiceResult) -> str:
        """กำหนดหัวข้อตามผลการทอย"""
        if result.value == 20:
            return "Critical Success!"
        elif result.value == 1:
            return "Critical Fail!"
        elif result.value >= 15:
            return "Great Roll!"
        else:
            return "ผลการทอย"

    async def _create_roll_embed(
        self, result: DiceResult, user: discord.User
    ) -> discord.Embed:
        """สร้าง embed สำหรับแสดงผลการทอยด้วย EmbedBuilder"""
        builder = EmbedBuilder()

        # สร้าง embed พื้นฐาน
        builder.set_title("ผลการทอยลูกเต๋า D20", emoji=result.emoji).set_color(
            result.color
        )

        # เพิ่มผลการทอย
        builder.add_field(
            name="ผลที่ได้", value=f"**{result.value}**", emoji="🎯", inline=False
        )

        # เพิ่มข้อความพิเศษ (ถ้ามี)
        if result.message:
            builder.add_field(
                name=self._get_roll_title(result),
                value=result.message,
                emoji=(
                    "📝"
                    if not result.is_critical
                    else "🎉" if result.value == 20 else "💔"
                ),
                inline=False,
            )

        # เพิ่ม footer และ timestamp
        builder.set_footer(text=f"ทอยโดย {user.name}", emoji="🎲").set_timestamp()

        return builder.build()

    def _create_themed_embed(self, result: DiceResult) -> EmbedBuilder:
        """สร้าง embed ตามธีมของผลลัพธ์"""
        if result.value == 20:
            return (
                EmbedBuilder()
                .set_title("Critical Success!", emoji="🌟")
                .set_color("gold")
                .set_description("ทอยได้ค่าสูงสุด! โชคดีมาก!")
            )
        elif result.value == 1:
            return (
                EmbedBuilder()
                .set_title("Critical Fail!", emoji="💥")
                .set_color("error")
                .set_description("ทอยได้ค่าต่ำสุด! โชคร้ายจัง!")
            )
        else:
            return EmbedBuilder().set_title("Roll Result", emoji="🎲").set_color("info")
