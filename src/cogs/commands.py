import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import logging

from ..commands.ping_command import PingCommand
from ..commands.roll_command import RollCommand

logger = logging.getLogger(__name__)

class CommandsCog(commands.Cog):
    """Cog สำหรับจัดการคำสั่งทั้งหมดของบอท"""
    
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now()
        
        # สร้าง command instances
        self.ping_cmd = PingCommand(bot)
        self.roll_cmd = RollCommand(bot)
        
        # Register commands
        self._setup_commands()
        
    def _setup_commands(self):
        """ตั้งค่า commands"""
        
        # Command: ping
        async def ping_callback(interaction: discord.Interaction):
            await self.ping_cmd.execute(
                interaction,
                self.start_time,
                self.bot.stats
            )
            
        # Command: roll    
        async def roll_callback(interaction: discord.Interaction):
            await self.roll_cmd.execute(
                interaction,
                self.bot.stats
            )
            
        # สร้าง command objects
        ping_command = app_commands.Command(
            name="ping",
            description="ตรวจสอบการเชื่อมต่อและสถานะระบบ",
            callback=ping_callback
        )
        
        roll_command = app_commands.Command(
            name="roll", 
            description="ทอยลูกเต๋า D20",
            callback=roll_callback
        )
        
        # เพิ่ม commands เข้า CommandTree
        self.bot.tree.add_command(ping_command)
        self.bot.tree.add_command(roll_command)
        
        logger.info("✅ Registered all commands successfully")

async def setup(bot):
    await bot.add_cog(CommandsCog(bot))
