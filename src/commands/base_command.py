# commands/base_command.py

import discord
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Union
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseCommand(ABC):
    """
    คลาสพื้นฐานสำหรับทุกคำสั่ง
    มี functionality พื้นฐานที่ทุกคำสั่งควรมี
    """

    def __init__(self, bot):
        self.bot = bot
        self._setup_logger()
        self._setup_constants()

    def _setup_logger(self) -> None:
        """ตั้งค่า logger สำหรับคำสั่ง"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _setup_constants(self) -> None:
        """ตั้งค่าค่าคงที่สำหรับคำสั่ง"""
        self.COLORS = {
            "success": discord.Color.green(),
            "error": discord.Color.red(),
            "warning": discord.Color.yellow(),
            "info": discord.Color.blue(),
        }

        self.EMOJI = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "loading": "⏳",
            "done": "✨",
        }

    @abstractmethod
    async def execute(
        self, interaction: discord.Interaction, *args: Any, **kwargs: Any
    ) -> None:
        """
        Method หลักสำหรับการทำงานของคำสั่ง

        Args:
            interaction: Discord interaction object
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        pass

    async def _send_error_message(
        self,
        interaction: discord.Interaction,
        error_message: Optional[str] = None,
        ephemeral: bool = True,
    ) -> None:
        """
        ส่งข้อความ error ไปยังผู้ใช้

        Args:
            interaction: Discord interaction
            error_message: ข้อความ error (ถ้าไม่ระบุจะใช้ข้อความ default)
            ephemeral: แสดงข้อความแค่ผู้ใช้คนเดียวเห็นหรือไม่
        """
        embed = await self._create_base_embed(
            title=f"{self.EMOJI['error']} เกิดข้อผิดพลาด",
            description=error_message or "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง",
            color=self.COLORS["error"],
        )
        await self._safe_respond(interaction, embed=embed, ephemeral=ephemeral)

    async def _create_base_embed(
        self, title: str, description: str, color: discord.Color
    ) -> discord.Embed:
        """
        สร้าง embed พื้นฐาน

        Args:
            title: หัวข้อของ embed
            description: คำอธิบายของ embed
            color: สีของ embed

        Returns:
            discord.Embed: Embed ที่สร้างขึ้น
        """
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow(),
        )
        return embed

    async def _safe_respond(
        self, interaction: discord.Interaction, **kwargs: Any
    ) -> None:
        """
        ส่งข้อความตอบกลับอย่างปลอดภัย

        Args:
            interaction: Discord interaction
            **kwargs: พารามิเตอร์สำหรับการส่งข้อความ
        """
        try:
            if interaction.response.is_done():
                await interaction.followup.send(**kwargs)
            else:
                await interaction.response.send_message(**kwargs)
        except Exception as e:
            self.logger.error(f"Error sending response: {str(e)}")

    def _validate_permissions(
        self, interaction: discord.Interaction, required_permissions: Dict[str, bool]
    ) -> bool:
        """
        ตรวจสอบ permissions ของผู้ใช้

        Args:
            interaction: Discord interaction
            required_permissions: Permissions ที่ต้องการ

        Returns:
            bool: True ถ้ามี permissions ครบ
        """
        if not interaction.guild:
            return False

        user_permissions = interaction.user.guild_permissions
        return all(
            getattr(user_permissions, perm, False) == value
            for perm, value in required_permissions.items()
        )

    async def _handle_missing_permissions(
        self, interaction: discord.Interaction, missing_perms: Union[str, list]
    ) -> None:
        """
        จัดการกรณีผู้ใช้ไม่มี permissions ที่จำเป็น

        Args:
            interaction: Discord interaction
            missing_perms: Permissions ที่ขาด
        """
        if isinstance(missing_perms, list):
            missing_perms = ", ".join(missing_perms)

        embed = await self._create_base_embed(
            title=f"{self.EMOJI['error']} ไม่มีสิทธิ์",
            description=f"คุณไม่มีสิทธิ์ที่จำเป็น: {missing_perms}",
            color=self.COLORS["error"],
        )
        await self._safe_respond(interaction, embed=embed, ephemeral=True)

    async def _show_loading(
        self, interaction: discord.Interaction, message: str = "กำลังดำเนินการ..."
    ) -> None:
        """
        แสดงข้อความ loading

        Args:
            interaction: Discord interaction
            message: ข้อความที่จะแสดง
        """
        embed = await self._create_base_embed(
            title=f"{self.EMOJI['loading']} กำลังดำเนินการ",
            description=message,
            color=self.COLORS["info"],
        )
        await self._safe_respond(interaction, embed=embed, ephemeral=True)
