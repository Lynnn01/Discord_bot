import discord
from discord import app_commands  # noqa
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.all(),
            application_id=os.getenv("APPLICATION_ID"),  # เพิ่ม application ID
        )

    async def setup_hook(self):
        print("กำลังเริ่มต้น setup_hook()...")
        try:
            print("กำลัง sync commands...")
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} commands")
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการ sync: {e}")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Connected to {len(self.guilds)} guilds:")
        for guild in self.guilds:
            print(f"- {guild.name} (ID: {guild.id})")


bot = MyBot()

# เพิ่มไฟล์ .env
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("ไม่พบ DISCORD_TOKEN ในไฟล์ .env")

print("กำลังเริ่มต้นบอท...")
bot.run(TOKEN)
