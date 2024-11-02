# utils/embed_builder.py

from typing import Optional, Dict, Any, Union
import discord
from datetime import datetime


class EmbedBuilder:
    """
    คลาสสำหรับสร้าง Discord Embed แบบ Builder pattern
    รองรับการสร้าง embed ที่ซับซ้อนได้ง่าย
    """

    def __init__(self):
        """สร้าง embed เปล่า"""
        self.embed = discord.Embed()
        self._setup_constants()

    def _setup_constants(self) -> None:
        """ตั้งค่าค่าคงที่ที่ใช้บ่อย"""
        self.COLORS = {
            "default": discord.Color.blurple(),
            "success": discord.Color.green(),
            "error": discord.Color.red(),
            "warning": discord.Color.yellow(),
            "info": discord.Color.blue(),
            "gold": discord.Color.gold(),
            "special": discord.Color.purple(),
        }

        self.EMOJIS = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "special": "✨",
            "arrow": "➡️",
            "gear": "⚙️",
            "time": "⏰",
            "user": "👤",
            "stats": "📊",
            "note": "📝",
        }

    def set_title(
        self, title: str, url: Optional[str] = None, emoji: Optional[str] = None
    ) -> "EmbedBuilder":
        """
        กำหนดหัวข้อของ embed

        Args:
            title: หัวข้อหลัก
            url: ลิงก์ที่จะเชื่อมกับหัวข้อ (optional)
            emoji: emoji ที่จะแสดงหน้าหัวข้อ (optional)
        """
        if emoji:
            title = f"{emoji} {title}"
        self.embed.title = title
        if url:
            self.embed.url = url
        return self

    def set_description(
        self, description: str, emoji: Optional[str] = None
    ) -> "EmbedBuilder":
        """
        กำหนดคำอธิบายของ embed

        Args:
            description: คำอธิบาย
            emoji: emoji ที่จะแสดงหน้าคำอธิบาย (optional)
        """
        if emoji:
            description = f"{emoji} {description}"
        self.embed.description = description
        return self

    def set_color(self, color: Union[str, discord.Color, int]) -> "EmbedBuilder":
        """
        กำหนดสีของ embed

        Args:
            color: สีที่ต้องการ (ใช้ชื่อจาก COLORS หรือ discord.Color หรือค่า RGB)
        """
        if isinstance(color, str):
            self.embed.color = self.COLORS.get(color, self.COLORS["default"])
        else:
            self.embed.color = color
        return self

    def add_field(
        self, name: str, value: Any, inline: bool = True, emoji: Optional[str] = None
    ) -> "EmbedBuilder":
        """
        เพิ่ม field ใน embed

        Args:
            name: ชื่อ field
            value: ค่าใน field
            inline: จัดเรียงแนวนอน (True) หรือแนวตั้ง (False)
            emoji: emoji ที่จะแสดงหน้าชื่อ field (optional)
        """
        if emoji:
            name = f"{emoji} {name}"
        self.embed.add_field(name=name, value=str(value), inline=inline)
        return self

    def add_fields(self, fields: Dict[str, Any], inline: bool = True) -> "EmbedBuilder":
        """
        เพิ่มหลาย fields พร้อมกัน

        Args:
            fields: dictionary ของ fields ที่จะเพิ่ม {name: value}
            inline: จัดเรียงแนวนอน (True) หรือแนวตั้ง (False)
        """
        for name, value in fields.items():
            self.add_field(name=name, value=value, inline=inline)
        return self

    def set_author(
        self, name: str, url: Optional[str] = None, icon_url: Optional[str] = None
    ) -> "EmbedBuilder":
        """
        กำหนดข้อมูลผู้สร้าง

        Args:
            name: ชื่อผู้สร้าง
            url: ลิงก์ที่จะเชื่อมกับชื่อ (optional)
            icon_url: URL ของไอคอน (optional)
        """
        self.embed.set_author(name=name, url=url, icon_url=icon_url)
        return self

    def set_thumbnail(self, url: str) -> "EmbedBuilder":
        """
        กำหนดรูปขนาดเล็ก

        Args:
            url: URL ของรูป
        """
        self.embed.set_thumbnail(url=url)
        return self

    def set_image(self, url: str) -> "EmbedBuilder":
        """
        กำหนดรูปขนาดใหญ่

        Args:
            url: URL ของรูป
        """
        self.embed.set_image(url=url)
        return self

    def set_footer(
        self, text: str, icon_url: Optional[str] = None, emoji: Optional[str] = None
    ) -> "EmbedBuilder":
        """
        กำหนด footer

        Args:
            text: ข้อความใน footer
            icon_url: URL ของไอคอน (optional)
            emoji: emoji ที่จะแสดงหน้าข้อความ (optional)
        """
        if emoji:
            text = f"{emoji} {text}"
        self.embed.set_footer(text=text, icon_url=icon_url)
        return self

    def set_timestamp(self, timestamp: Optional[datetime] = None) -> "EmbedBuilder":
        """
        กำหนดเวลา

        Args:
            timestamp: เวลาที่ต้องการ (ถ้าไม่ระบุจะใช้เวลาปัจจุบัน)
        """
        self.embed.timestamp = timestamp or discord.utils.utcnow()
        return self

    def build(self) -> discord.Embed:
        """
        สร้าง embed

        Returns:
            discord.Embed: Embed ที่สร้างเสร็จแล้ว
        """
        return self.embed

    @classmethod
    def create_simple_embed(
        cls, title: str, description: str, color: Union[str, discord.Color] = "default"
    ) -> discord.Embed:
        """
        สร้าง embed อย่างง่าย

        Args:
            title: หัวข้อ
            description: คำอธิบาย
            color: สี (default: blurple)

        Returns:
            discord.Embed: Embed ที่สร้างเสร็จแล้ว
        """
        return (
            cls()
            .set_title(title)
            .set_description(description)
            .set_color(color)
            .set_timestamp()
            .build()
        )

    @classmethod
    def create_error_embed(
        cls, title: str = "เกิดข้อผิดพลาด", description: str = "กรุณาลองใหม่อีกครั้ง"
    ) -> discord.Embed:
        """
        สร้าง embed สำหรับแสดงข้อผิดพลาด

        Args:
            title: หัวข้อ
            description: คำอธิบาย

        Returns:
            discord.Embed: Embed ข้อผิดพลาด
        """
        return (
            cls()
            .set_title(title, emoji="❌")
            .set_description(description)
            .set_color("error")
            .set_timestamp()
            .build()
        )


# ตัวอย่างการใช้งาน
if __name__ == "__main__":
    # สร้าง embed แบบละเอียด
    embed = (
        EmbedBuilder()
        .set_title("ยินดีต้อนรับ", emoji="👋")
        .set_description("ระบบพร้อมใช้งาน")
        .set_color("success")
        .add_field("สถานะ", "ออนไลน์", emoji="🟢")
        .add_field("เวลาทำงาน", "2 ชั่วโมง", emoji="⏰")
        .set_footer("พัฒนาโดย Bot Team", emoji="🤖")
        .set_timestamp()
        .build()
    )

    # สร้าง embed อย่างง่าย
    simple_embed = EmbedBuilder.create_simple_embed(
        title="แจ้งเตือน", description="มีการอัพเดทใหม่", color="info"
    )

    # สร้าง embed แสดงข้อผิดพลาด
    error_embed = EmbedBuilder.create_error_embed(
        title="ไม่สามารถดำเนินการได้", description="ไม่พบข้อมูลที่ต้องการ"
    )
