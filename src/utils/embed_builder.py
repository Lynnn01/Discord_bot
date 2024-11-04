# utils/embed_builder.py

from typing import Optional, Union, Any
from datetime import datetime
import discord
from src.utils.ui_constants import UIConstants  # แก้ path import


class EmbedBuilder:
    """Builder class สำหรับสร้าง Discord Embed"""
    
    def __init__(self):
        """สร้าง embed เปล่า"""
        self.embed = discord.Embed()
        self.ui = UIConstants()
    # Template Methods สำหรับ Embed ที่ใช้บ่อย
    @classmethod
    def create_welcome_embed(
        cls,
        member: Union[discord.Member, str],
        member_count: int,
        guild_name: Optional[str] = None,
        thumbnail_url: Optional[str] = None
    ) -> discord.Embed:
        """
        สร้าง embed ต้อนรับสมาชิกใหม่
        
        Args:
            member: สมาชิกที่เข้าร่วม
            member_count: จำนวนสมาชิกทั้งหมด
            guild_name: ชื่อเซิร์ฟเวอร์ (optional)
            thumbnail_url: URL รูปภาพขนาดเล็ก (optional)
        """
        member_mention = member.mention if isinstance(member, discord.Member) else member
        
        builder = (
            cls()
            .set_title("ยินดีต้อนรับสมาชิกใหม่!", emoji="👋")
            .set_description(
                f"ยินดีต้อนรับ {member_mention} "
                f"เข้าสู่{f'เซิร์ฟเวอร์ {guild_name}' if guild_name else 'เซิร์ฟเวอร์'}!"
            )
            .set_color("success")
            .add_field("สมาชิกคนที่", str(member_count), emoji="👥")
        )
        
        if thumbnail_url:
            builder.embed.set_thumbnail(url=thumbnail_url)
            
        if isinstance(member, discord.Member):
            builder.set_footer(f"User ID: {member.id}")
            
        return builder.set_timestamp().build()

    @classmethod
    def create_help_embed(
        cls,
        prefix: str,
        description: Optional[str] = None,
        user: Optional[discord.User] = None,
        command_count: Optional[int] = None
    ) -> discord.Embed:
        """
        สร้าง embed สำหรับคำสั่ง help
        
        Args:
            prefix: Prefix ของคำสั่ง
            description: คำอธิบายเพิ่มเติม (optional)
            user: ผู้ใช้ที่เรียกคำสั่ง (optional)
            command_count: จำนวนคำสั่งทั้งหมด (optional)
        """
        builder = (
            cls()
            .set_title("คำสั่งที่ใช้ได้", emoji="❔")
            .set_color("info")
            .add_field("Prefix", prefix, emoji="⌨️", inline=True)
        )
        
        if description:
            builder.set_description(description)
            
        if command_count:
            builder.add_field("จำนวนคำสั่ง", str(command_count), emoji="📜", inline=True)
            
        if user:
            builder.set_footer(f"Requested by {user.name}")
            
        return builder.set_timestamp().build()

    @classmethod
    def create_error_embed(
        cls,
        title: str = "เกิดข้อผิดพลาด",
        description: str = "เกิดข้อผิดพลาดที่ไม่คาดคิด กรุณาองใหม่อีกครั้ง",
        error_details: Optional[str] = None
    ) -> discord.Embed:
        """
        สร้าง embed สำหรับแสดงข้อผิดพลาด
        
        Args:
            title: หัวข้อข้อผิดพลาด
            description: คำอธิบายข้อผิดพลาด
            error_details: รายละเอียดข้อผิดพลาดเพิ่มเติม (optional)
        """
        builder = (
            cls()
            .set_title(title, emoji="❌")
            .set_description(description)
            .set_color("error")
        )
        
        if error_details:
            builder.add_field("รายละเอียด", error_details, emoji="ℹ️")
            
        return builder.set_timestamp().build()

    # Utility Methods
    def set_title(self, title: str, emoji: Optional[str] = None) -> "EmbedBuilder":
        """กำหนดหัวข้อของ embed"""
        self.embed.title = f"{emoji} {title}" if emoji else title
        return self

    def set_description(self, description: str) -> "EmbedBuilder":
        """กำหนดคำอธิบายของ embed"""
        self.embed.description = description
        return self

    def set_color(self, color: Union[str, discord.Color, int]) -> "EmbedBuilder":
        """กำหนดสีของ embed"""
        if isinstance(color, str):
            self.embed.color = self.ui.COLORS.get(color.lower(), self.ui.COLORS["default"])
        else:
            self.embed.color = color
        return self

    def add_field(
        self, 
        name: str, 
        value: Any, 
        emoji: Optional[str] = None,
        inline: bool = True
    ) -> "EmbedBuilder":
        """เพิ่ม field ใน embed"""
        field_name = f"{emoji} {name}" if emoji else name
        self.embed.add_field(name=field_name, value=str(value), inline=inline)
        return self

    def set_footer(self, text: str, emoji: Optional[str] = None) -> "EmbedBuilder":
        """
        กำหนด footer ของ embed
        
        Args:
            text: ข้อความใน footer
            emoji: emoji ที่จะแสดงใน footer (optional)
        """
        if emoji:
            text = f"{emoji} {text}"
        self.embed.set_footer(text=text)
        return self

    def set_timestamp(self, timestamp: Optional[datetime] = None) -> "EmbedBuilder":
        """กำหนดเวลาของ embed"""
        self.embed.timestamp = timestamp or datetime.now()
        return self

    def build(self) -> discord.Embed:
        """สร้าง embed object"""
        return self.embed
