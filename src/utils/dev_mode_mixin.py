from typing import Optional
import os
import discord
import logging

logger = logging.getLogger(__name__)

class DevModeMixin:
    """Mixin สำหรับจัดการ Dev Mode"""
    
    @property
    def dev_mode(self) -> bool:
        """ตรวจสอบว่าอยู่ใน Dev Mode หรือไม่"""
        return getattr(self, '_dev_mode', False)
    
    @dev_mode.setter 
    def dev_mode(self, value: bool):
        """กำหนดค่า Dev Mode"""
        self._dev_mode = value
        
    @property
    def dev_guild_id(self) -> Optional[int]:
        """ดึง Dev Guild ID จาก environment variable"""
        dev_guild_id = os.getenv("DEV_GUILD_ID")
        return int(dev_guild_id) if dev_guild_id else None
        
    async def handle_dev_mode(self, guild: discord.Guild) -> bool:
        """
        ตรวจสอบและจัดการ Dev Mode
        
        Args:
            guild: Discord guild ที่ต้องการตรวจสอบ
            
        Returns:
            bool: True ถ้าควรออกจาก guild
        """
        if not self.dev_mode:
            return False
            
        if not self.dev_guild_id:
            logger.warning("⚠️ DEV_MODE เปิดอยู่แต่ไม่พบ DEV_GUILD_ID")
            return False
            
        if guild.id != self.dev_guild_id:
            logger.info(f"👋 ออกจาก guild {guild.name} (ID: {guild.id}) เนื่องจากอยู่ใน Dev Mode")
            await guild.leave()
            return True
            
        return False

    async def validate_dev_guild(self) -> None:
        """
        ตรวจสอบความถูกต้องของ Dev Guild
        
        Raises:
            ValueError: ถ้าไม่พบ DEV_GUILD_ID ในโหมด Dev
        """
        if self.dev_mode and not self.dev_guild_id:
            raise ValueError("❌ DEV_MODE เปิดอยู่แต่ไม่พบ DEV_GUILD_ID")
