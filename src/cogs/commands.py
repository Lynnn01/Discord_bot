import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from typing import Dict

from src.commands.ping_command import PingCommand
from src.commands.roll_command import RollCommand

class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now()
        
        # สร้าง command instances
        self.ping_cmd = PingCommand(bot)
        self.roll_cmd = RollCommand(bot)
        
        # Register slash commands
        self.register_commands()
        
    def register_commands(self):
        @self.bot.tree.command(
            name="ping",
            description="ตรวจสอบการเชื่อมต่อและสถานะระบบ"
        )
        async def ping(interaction: discord.Interaction):
            await self.ping_cmd.execute(
                interaction,
                self.start_time,
                self.bot.stats
            )
            
        @self.bot.tree.command(
            name="roll",
            description="ทอยลูกเต๋า D20"
        )
        async def roll(interaction: discord.Interaction):
            await self.roll_cmd.execute(
                interaction,
                self.bot.stats
            )

async def setup(bot):
    await bot.add_cog(CommandsCog(bot))
