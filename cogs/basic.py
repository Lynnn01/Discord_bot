# cogs/basic.py
import discord
from discord import app_commands
from discord.ext import commands
import random


class Basic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="roll", description="ทอยลูกเต๋า D20")
    async def test(self, interaction: discord.Interaction):
        roll = random().randint(1, 20)
        await interaction.response.send_message(f"🎲 คุณทอยได้: {roll}")

    @app_commands.command(name="ping", description="เช็คการตอบสนองของบอท")
    async def ping(self, interaction: discord.Interaction):
        # คำนวณ latency
        latency = round(self.bot.latency * 1000)

        # สร้าง embed
        embed = discord.Embed(
            title="🏓 Pong!",
            description="ผลการตรวจสอบการเชื่อมต่อ",
            color=self.get_color_based_on_latency(latency),  # สีจะเปลี่ยนตาม latency
        )

        # เพิ่มข้อมูล latency
        embed.add_field(name="📊 การตอบสนอง", value=f"`{latency}ms`", inline=True)

        # เพิ่มสถานะการเชื่อมต่อ
        embed.add_field(
            name="📡 สถานะ", value=self.get_status_emoji(latency), inline=True
        )

        # เพิ่ม timestamp
        embed.timestamp = discord.utils.utcnow()

        # เพิ่ม footer
        embed.set_footer(text=f"ร้องขอโดย {interaction.user.name}")

        # ส่ง embed กลับไป
        await interaction.response.send_message(embed=embed)

    def get_color_based_on_latency(self, latency: int) -> discord.Color:
        """กำหนดสีตามค่า latency"""
        if latency < 100:
            return discord.Color.green()  # ดี
        elif latency < 200:
            return discord.Color.yellow()  # ปานกลาง
        else:
            return discord.Color.red()  # แย่

    def get_status_emoji(self, latency: int) -> str:
        """กำหนด emoji ตามค่า latency"""
        if latency < 100:
            return "🟢 ดีมาก"
        elif latency < 200:
            return "🟡 ปานกลาง"
        else:
            return "🔴 ช้า"


async def setup(bot: commands.Bot):
    await bot.add_cog(Basic(bot))
