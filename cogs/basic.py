# cogs/basic.py
import discord
from discord import app_commands
from discord.ext import commands


class Basic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="test", description="ทดสอบคำสั่ง slash command")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.send_message("คำสั่งทำงานแล้ว!")

    @app_commands.command(name="ping", description="เช็คการตอบสนองของบอท")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! ({latency}ms)")


async def setup(bot: commands.Bot):
    await bot.add_cog(Basic(bot))
