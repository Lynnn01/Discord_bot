# cogs/event_handler.py
import discord
from discord.ext import commands
import logging
from datetime import datetime
from typing import Optional
from utils.embed_builder import EmbedBuilder  # แก้ไขเป็น relative import

logger = logging.getLogger(__name__)


class EventHandler(commands.Cog):
    """
    Cog สำหรับจัดการ events ต่างๆ ของ bot
    เช่น การเข้าร่วมเซิร์ฟเวอร์, ข้อผิดพลาด, การใช้งานคำสั่ง
    """

    def __init__(self, bot):
        """
        Initialize event handler

        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self._setup_constants()
        logger.info("✅ โหลด Event Handler สำเร็จ")

    def _setup_constants(self):
        """ตั้งค่าค่าคงที่สำหรับ event handler"""
        self.ERROR_MESSAGES = {
            commands.MissingPermissions: "คุณไม่มีสิทธิ์ในการใช้คำสั่งนี้",
            commands.BotMissingPermissions: "บอทไม่มีสิทธิ์ที่จำเป็น",
            commands.MissingRequiredArgument: "กรุณาระบุข้อมูลให้ครบถ้วน",
            commands.BadArgument: "รูปแบบข้อมูลไม่ถูกต้อง",
            commands.CommandOnCooldown: "กรุณารอสักครู่ก่อนใช้คำสั่งนี้อีกครั้ง",
        }

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """
        จัดการเมื่อ bot เข้าร่วมเซิร์ฟเวอร์ใหม่

        Args:
            guild: Discord guild ที่ bot เข้าร่วม
        """
        logger.info(f"🎉 เข้าร่วมเซิร์ฟเวอร์: {guild.name} (ID: {guild.id})")

        # สร้าง embed แจ้งเตือน
        embed = (
            EmbedBuilder()
            .set_title("ขอบคุณที่เชิญบอทเข้าร่วมเซิร์ฟเวอร์", emoji="👋")
            .set_description("บอทพร้อมใช้งานแล้ว! ใช้คำสั่ง /help เพื่อดูคำสั่งทั้งหมด")
            .set_color("success")
            .add_field("เซิร์ฟเวอร์", guild.name, emoji="🏢")
            .add_field("สมาชิก", str(guild.member_count), emoji="👥")
            .add_field("เจ้าของเซิร์ฟเวอร์", str(guild.owner), emoji="👑")
            .set_footer("Discord Bot")
            .set_timestamp()
            .build()
        )

        # ส่ง embed ไปยังช่องทางหลัก
        try:
            system_channel = guild.system_channel or await self._find_suitable_channel(
                guild
            )
            if system_channel:
                await system_channel.send(embed=embed)
        except Exception as e:
            logger.error(f"❌ ไม่สามารถส่งข้อความต้อนรับได้: {str(e)}")

    async def _find_suitable_channel(
        self, guild: discord.Guild
    ) -> Optional[discord.TextChannel]:
        """
        ค้นหาช่องทางที่เหมาะสมสำหรับส่งข้อความ

        Args:
            guild: Discord guild ที่ต้องการค้นหาช่องทาง

        Returns:
            Optional[discord.TextChannel]: ช่องทางที่เหมาะสม หรือ None ถ้าไม่พบ
        """
        # ลองหาช่องทางชื่อ general ก่อน
        general_channel = discord.utils.get(guild.text_channels, name="general")
        if general_channel:
            return general_channel

        # ถ้าไม่พบ ใช้ช่องทางแรกที่บอทมีสิทธิ์ส่งข้อความ
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                return channel

        return None

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """
        จัดการเมื่อ bot ถูกลบออกจากเซิร์ฟเวอร์

        Args:
            guild: Discord guild ที่ bot ถูกลบออก
        """
        logger.info(f"👋 ออกจากเซิร์ฟเวอร์: {guild.name} (ID: {guild.id})")

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        await self.bot.error_handler.handle_error(ctx, error)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        จัดการเมื่อมีสมาชิกใหม่เข้าร่วมเซิร์ฟเวอร์

        Args:
            member: Discord member ที่เข้าร่วม
        """
        # สร้าง embed ต้อนรับ
        embed = (
            EmbedBuilder()
            .set_title("ยินดีต้อนรับสมาชิกใหม่!", emoji="👋")
            .set_description(f"ยินดีต้อนรับ {member.mention} เข้าสู่เซิร์ฟเวอร์!")
            .set_color("success")
            .add_field("สมาชิกคนที่", str(member.guild.member_count), emoji="👥")
            .set_footer(f"User ID: {member.id}")
            .set_timestamp()
            .build()
        )

        # ส่ง embed ไปยังช่องทางต้อนรับ
        try:
            welcome_channel = member.guild.system_channel
            if welcome_channel:
                await welcome_channel.send(embed=embed)
        except Exception as e:
            logger.error(f"❌ ไม่สามารถส่งข้อความต้อนรับได้: {str(e)}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        จัดการเมื่อมีข้อความใหม่

        Args:
            message: Discord message
        """
        # ไม่สนใจข้อความจาก bot
        if message.author.bot:
            return

        # เพิ่มสถิติ
        self.bot.stats["messages_processed"] += 1

        # ตรวจสอบ mentions
        if self.bot.user in message.mentions:
            await self._handle_bot_mention(message)

    async def _handle_bot_mention(self, message: discord.Message):
        """
        จัดการเมื่อมีการ mention bot

        Args:
            message: Discord message ที่ mention bot
        """
        embed = (
            EmbedBuilder()
            .set_title("สวัสดี!", emoji="👋")
            .set_description("ใช้คำสั่ง /help เพื่อดูคำสั่งทั้งหมด")
            .set_color("info")
            .add_field("Prefix", self.bot.command_prefix, emoji="⌨️")
            .set_footer(f"Mentioned by {message.author.name}")
            .set_timestamp()
            .build()
        )

        await message.channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(EventHandler(bot))
