# main.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.all(),
            application_id=os.getenv("APPLICATION_ID"),
        )

    async def setup_hook(self):
        print("กำลังโหลด cogs...")
        await self.load_extension("cogs.basic")
        print("กำลัง sync commands...")
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} commands")
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการ sync: {e}")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Connected to {len(self.guilds)} guilds:")
        for guild in self.guilds:
            print(f"- {guild.name} (ID: {guild.id})")


async def main():
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        raise ValueError("ไม่พบ DISCORD_TOKEN ในไฟล์ .env")

    bot = MyBot()
    await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
