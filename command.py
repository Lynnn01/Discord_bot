import discord
from discord import app_commands
from discord.ext import commands
from bot import MyBot


bot = MyBot()


@bot.tree.command(name="test", description="ทดสอบคำสั่ง slash command")
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("คำสั่งทำงานแล้ว!")


@bot.tree.command(name="ping", description="เช็คการตอบสนองของบอท")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong! ({latency}ms)")
