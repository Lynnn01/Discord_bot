from typing import Dict
import discord
import random
import logging
from .base_command import BaseCommand
from src.utils.embed_builder import EmbedBuilder

logger = logging.getLogger(__name__)

class RollCommand(BaseCommand):
    """คำสั่งสำหรับทอยลูกเต๋า"""

    async def execute(
        self,
        interaction: discord.Interaction,
        stats: Dict[str, int]
    ) -> None:
        """ดำเนินการคำสั่งทอยลูกเต๋า"""
        try:
            # ทอยลูกเต๋า
            roll = random.randint(1, 6)
            is_max = roll == 6
            
            # อัพเดทสถิติ
            stats["roll"] = stats.get("roll", 0) + 1
            
            # สร้าง embed
            if is_max:
                embed = (
                    EmbedBuilder()
                    .set_title("ทอยได้เลขสูงสุด!", emoji="🎯")
                    .set_description(f"คุณทอยได้ **{roll}** !")
                    .set_color("success")
                    .set_footer(f"ทอยโดย {interaction.user.display_name}", emoji="🎲")
                    .build()
                )
            else:
                embed = (
                    EmbedBuilder()
                    .set_title("ผลการทอยลูกเต๋า", emoji="🎲")
                    .set_description(f"คุณทอยได้ {roll}")
                    .set_color("primary")
                    .set_footer(f"ทอยโดย {interaction.user.display_name}", emoji="🎲")
                    .build()
                )

            # ส่งผลลัพธ์
            await interaction.response.send_message(embed=embed)
            logger.debug(f"🎲 ผู้ใช้ {interaction.user} ทอยได้ {roll}")

        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในคำสั่ง roll: {str(e)}")
            await self.handle_error(interaction, e)