import discord
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseCommand(ABC):
    def __init__(self, bot):
        self.bot = bot

    @abstractmethod
    async def execute(self, interaction: discord.Interaction, *args, **kwargs):
        pass

    async def _send_error_message(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "❌ เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง", ephemeral=True
        )
