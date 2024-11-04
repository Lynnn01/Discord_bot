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
        # ตรวจสอบ Dev Mode ก่อน
        if await self.bot.handle_dev_mode(guild):
            return
            
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
            .set_footer("Discord Bot", emoji="🤖")
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
        """จัดการเมื่อมีสมาชิกเข้าร่วมเซิร์ฟเวอร์"""
        try:
            # หาช่องทางที่เหมาะสม
            channel = await self._find_suitable_channel(member.guild)
            if not channel:
                return

            # สร้าง welcome embed
            embed = EmbedBuilder.create_welcome_embed(
                member=member,
                member_count=member.guild.member_count,
                guild_name=member.guild.name,
                thumbnail_url=member.display_avatar.url
            )

            await channel.send(embed=embed)
            logger.info(f"👋 ส่งข้อความต้อนรับให้ {member.name} ใน {member.guild.name}")

        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในการส่งข้อความต้อนรับ: {str(e)}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """จัดการเมื่อมีข้อความใหม่"""
        if message.author.bot or not message.guild:
            return

        # ตอบกลับเมื่อถูก mention
        if self.bot.user in message.mentions:
            try:
                embed = EmbedBuilder.create_help_embed(
                    prefix=self.bot.command_prefix,
                    description="ใช้คำสั่ง /help เพื่อดูคำสั่งทั้งหมด",
                    user=message.author,
                    command_count=len(self.bot.tree.get_commands())
                )
                
                await message.reply(embed=embed)
                logger.info(f"💬 ตอบกลับ mention จาก {message.author.name}")

            except Exception as e:
                logger.error(f"❌ เกิดข้อผิดพลาดในการตอบกลับ mention: {str(e)}")


async def setup(bot):
    await bot.add_cog(EventHandler(bot))
