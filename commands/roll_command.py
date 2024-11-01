from .base_command import BaseCommand
import discord
import random
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


class RollCommand(BaseCommand):
    def __init__(self, bot):
        super().__init__(bot)
        self.ROLL_COLORS = {
            20: discord.Color.gold(),
            15: discord.Color.green(),
            10: discord.Color.blue(),
            5: discord.Color.greyple(),
            1: discord.Color.red(),
        }

    async def execute(self, interaction: discord.Interaction, command_stats: dict):
        try:
            command_stats["roll"] += 1
            roll_value = random.randint(1, 20)
            emoji = self._get_roll_emoji(roll_value)
            embed = await self._create_roll_embed(roll_value, emoji, interaction.user)
            await interaction.response.send_message(embed=embed)
            logger.debug(f"🎲 ผู้ใช้ {interaction.user} ทอยได้ {roll_value}")

        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในคำสั่ง roll: {str(e)}")
            await self._send_error_message(interaction)

    @lru_cache(maxsize=128)
    def _get_roll_color(self, roll: int) -> discord.Color:
        for threshold, color in sorted(self.ROLL_COLORS.items(), reverse=True):
            if roll >= threshold:
                return color
        return discord.Color.greyple()

    def _get_roll_emoji(self, roll: int) -> str:
        emoji_map = {
            20: "🌟",
            1: "💥",
            15: "✨",
            10: "🎲",
            5: "🎯",
        }
        for threshold, emoji in sorted(emoji_map.items(), reverse=True):
            if roll >= threshold:
                return emoji
        return "🎲"

    async def _create_roll_embed(
        self, roll: int, emoji: str, user: discord.User
    ) -> discord.Embed:
        embed = discord.Embed(
            title=f"{emoji} ผลการทอยลูกเต๋า D20", color=self._get_roll_color(roll)
        )

        embed.add_field(name="🎯 ผลที่ได้", value=f"**{roll}**", inline=False)

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
