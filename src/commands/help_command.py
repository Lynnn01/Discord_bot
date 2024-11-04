from dataclasses import dataclass
from typing import Dict, List, Optional
import discord
from discord import app_commands
import logging
from datetime import datetime
from .base_command import BaseCommand
from utils.embed_builder import EmbedBuilder

logger = logging.getLogger(__name__)


@dataclass
class CommandInfo:
    """ข้อมูลของแต่ละคำสั่ง"""

    name: str
    description: str
    usage: str
    emoji: str
    examples: List[str]
    category: str = "ทั่วไป"
    options: List[str] = None
    dev_only: bool = False
    cooldown: Optional[int] = None
    permissions: List[str] = None


class HelpCommand(BaseCommand):
    """คำสั่งสำหรับแสดงวิธีใช้งานคำสั่งต่างๆ พร้อมรองรับ Dev Mode"""

    def __init__(self, bot):
        super().__init__(bot)
        self.categories = {
            "ทั่วไป": "🔧",
            "เกม": "🎮",
            "ระบบ": "⚙️",
            "พัฒนา": "🛠️",  # สำรับ dev commands
        }
        self.command_info = self._setup_command_info()

    def _setup_command_info(self) -> Dict[str, Dict]:
        """ตั้งค่าข้อมูลพื้นฐานของคำสั่ง"""
        return {
            "ping": {
                "emoji": "🏓",
                "category": "ระบบ",
                "examples": [
                    "ตรวจสอบความเร็วในการตอบสนอง",
                    "ดูสถิติการใช้งานบอท",
                    "ตรวจสอบเวลาทำงานของบอท",
                ],
                "cooldown": 5,
                "dev_only": False,
            },
            "roll": {
                "emoji": "🎲",
                "category": "เกม",
                "examples": [
                    "ทอยลูกเต๋าเพื่อตัดสินใจ",
                    "ทอยเพื่อลุ้น Critical Success (20)",
                    "ดูโชคของคุณวันนี้",
                ],
                "cooldown": 3,
                "dev_only": False,
            },
            "help": {
                "emoji": "❓",
                "category": "ทั่วไป",
                "examples": [
                    "ดูรายการคำสั่งทั้งหมด: /help",
                    "ดูวิธีใช้คำสั่งเฉพาะ: /help [ชื่อคำสั่ง]",
                ],
                "cooldown": None,
                "dev_only": False,
            },
            "dev": {
                "emoji": "🛠️",
                "category": "พัฒนา",
                "examples": [
                    "/dev action:Sync Commands scope:Guild - ซิงค์คำสั่งกับเซิร์ฟเวอร์",
                    "/dev action:Sync Commands scope:Global - ซิงค์คำสั่งทั้งหมด",
                    "/dev action:Reload Cogs cog:all - โหลด cogs ทั้งหมดใหม่",
                    "/dev action:Reload Cogs cog:commands - โหลด cog เฉพาะใหม่",
                    "/dev action:Show Status - แสดงสถานะระบบ",
                    "/dev action:Cleanup Commands - ลบคำสั่งเก่า",
                ],
                "cooldown": None,
                "dev_only": True,
                "permissions": ["Administrator"],
                "options": [
                    "`action`: การดำเนินการที่ต้องการ (จำเป็น)",
                    "`scope`: ขอบเขตการ sync - global/guild (สำหรับ Sync Commands)",
                    "`cog`: ชื่อ cog ที่ต้องการ reload (สำหรับ Reload Cogs)",
                ],
            },
        }

    def _build_usage_string(self, command: app_commands.Command) -> str:
        """สร้างข้อความแสดงวิธีใช้งานคำสั่ง"""
        usage = f"/{command.name}"

        # ตรวจสอบว่าเป็นคำสั่ง dev หรือไม่
        if command.name == "dev":
            return (
                f"{usage} action:<Sync/Reload/Status/Cleanup> "
                "[scope:guild/global] [cog:name]"
            )

        # สำหรับคำสั่งอื่นๆ
        if hasattr(command, "_params"):
            for param in command._params.values():
                param_str = (
                    f" [{param.name}]" if not param.required else f" <{param.name}>"
                )
                usage += param_str

        return usage

    def _get_command_info(self, command: app_commands.Command) -> CommandInfo:
        """สร้าง CommandInfo จาก Command object"""
        base_info = self.command_info.get(command.name, {})
        options = []
        permissions = []

        # ตรวจสอบ permissions
        if hasattr(command, "default_permissions"):
            perms = command.default_permissions
            if perms:
                permissions = [perm for perm, value in perms.items() if value]

        # ดึงข้อมูล options
        if hasattr(command, "_params"):
            for param in command._params.values():
                option_desc = f"`{param.name}`"
                if param.description:
                    option_desc += f": {param.description}"
                if not param.required:
                    option_desc += " (ไม่จำเป็น)"
                options.append(option_desc)

        return CommandInfo(
            name=command.name,
            description=command.description or "ไม่มีคำอธิบาย",
            usage=self._build_usage_string(command),
            emoji=base_info.get("emoji", "🔹"),
            examples=base_info.get("examples", ["ไม่มีตัวอย่าง"]),
            category=base_info.get("category", "ทั่วไป"),
            options=options,
            dev_only=base_info.get("dev_only", False),
            cooldown=base_info.get("cooldown"),
            permissions=permissions,
        )

    def _filter_commands(self, commands) -> List[app_commands.Command]:
        """กรองคำสั่งตามโหมดการทำงาน"""
        filtered_commands = []
        for command in commands:
            cmd_info = self.command_info.get(command.name, {})
            # แสดงคำสั่ง dev เฉพาะใน dev mode
            if cmd_info.get("dev_only", False) and not self.bot.dev_mode:
                continue
            filtered_commands.append(command)
        return filtered_commands

    async def execute(
        self,
        interaction: discord.Interaction,
        command_stats: Dict[str, int],
        command_name: Optional[str] = None,
    ):
        """ดำเนินการคำสั่ง help"""
        try:
            command_stats["help"] = command_stats.get("help", 0) + 1

            if command_name:
                # หาคำสั่งจาก CommandTree
                command = self.bot.tree.get_command(command_name)
                if not command:
                    raise ValueError(f"ไม่พบคำสั่ง `{command_name}`")

                # ตรวจสอบสิทธิ์การเข้าถึง
                cmd_info = self.command_info.get(command_name, {})
                if cmd_info.get("dev_only", False) and not self.bot.dev_mode:
                    raise ValueError("คำสั่งนี้ใช้ได้เฉพาะในโหมดพัฒนาเท่านั้น")

                embed = await self._create_command_detail_embed(command)
            else:
                embed = await self._create_commands_overview_embed()

            await interaction.response.send_message(embed=embed)
            logger.info(
                f"🔍 ผู้ใช้ {interaction.user} ขอดูวิธีใช้คำสั่ง {command_name if command_name else 'ทั้งหมด'}"
            )

        except Exception as e:
            logger.error(f"❌ เกิดข้อผิดพลาดในคำสั่ง help: {str(e)}")
            await interaction.response.send_message(f"❌ {str(e)}", ephemeral=True)

    async def _create_command_detail_embed(
        self, command: app_commands.Command
    ) -> discord.Embed:
        """สร้าง embed แสดงรายละเอียดของคำสั่ง"""
        cmd_info = self._get_command_info(command)
        category_emoji = self.categories.get(cmd_info.category, "📁")

        builder = (
            EmbedBuilder()
            .set_title(f"วิธีใช้คำสั่ง {cmd_info.name}", emoji=cmd_info.emoji)
            .set_description(cmd_info.description)
            .set_color(discord.Color.blue())
            .add_field(
                name="หมวดหมู่",
                value=f"{category_emoji} {cmd_info.category}",
                emoji="📂",
                inline=True,
            )
            .add_field(
                name="วิธีใช้", value=f"`{cmd_info.usage}`", emoji="📝", inline=True
            )
        )

        # เพิ่มข้อมูล cooldown
        if cmd_info.cooldown:
            builder.add_field(
                name="Cooldown",
                value=f"{cmd_info.cooldown} วินาที",
                emoji="⏱️",
                inline=True,
            )

        # เพิ่มข้อมูลสิทธิ์
        if cmd_info.permissions:
            builder.add_field(
                name="สิทธิ์ที่จำเป็น",
                value="\n".join(f"• {perm}" for perm in cmd_info.permissions),
                emoji="🔒",
                inline=True,
            )

        # เพิ่ม options ถ้ามี
        if cmd_info.options:
            builder.add_field(
                name="พารามิเตอร์",
                value="\n".join(f"• {opt}" for opt in cmd_info.options),
                emoji="🔧",
                inline=False,
            )

        # เพิ่มตัวอย่างการใช้งาน
        builder.add_field(
            name="ตัวอย่างการใช้งาน",
            value="\n".join(f"• {example}" for example in cmd_info.examples),
            emoji="💡",
            inline=False,
        )

        # เพิ่มข้อความ Dev Mode ถ้าจำเป็น
        if cmd_info.dev_only:
            builder.set_footer("คำสั่งนี้ใช้ได้เฉพาะในโหมดพัฒนาเท่านั้น", emoji="⚠️")
        else:
            builder.set_footer("💡 เคล็ด��ับ: ใช้ /help เพื่อดูคำสั่งทั้งหมด")

        return builder.build()

    async def _create_commands_overview_embed(self) -> discord.Embed:
        """สร้าง embed แสดงภาพรวมของคำสั่งทั้งหมด"""
        commands_by_category = {}

        # จัดกลุ่มคำสั่งตามหมวดหมู่
        commands = self._filter_commands(self.bot.tree.get_commands())
        for command in commands:
            cmd_info = self._get_command_info(command)
            if cmd_info.category not in commands_by_category:
                commands_by_category[cmd_info.category] = []
            commands_by_category[cmd_info.category].append(cmd_info)

        # สร้าง embed
        builder = (
            EmbedBuilder()
            .set_title("คำสั่งทั้งหมด", emoji="📚")
            .set_description(
                "รายการคำสั่งที่สามารถใช้งานได้ แยกตามหมวดหมู่"
                + ("\n⚠️ *กำลังทำงานในโหมดพัฒนา*" if self.bot.dev_mode else "")
            )
            .set_color(discord.Color.blue())
        )

        # เพิ่มฟิลด์สำหรับแต่ละหมวดหมู่
        for category, commands in commands_by_category.items():
            category_emoji = self.categories.get(category, "📁")
            commands_text = []
            for cmd in sorted(commands, key=lambda x: x.name):
                text = f"{cmd.emoji} `/{cmd.name}`"
                if cmd.cooldown:
                    text += f" `⏱️{cmd.cooldown}s`"
                text += f" • {cmd.description}"
                commands_text.append(text)

            if commands_text:  # เพิ่มเฉพาะหมวดหมู่ที่มีคำสั่ง
                builder.add_field(
                    name=f"{category_emoji} {category}",
                    value="\n".join(commands_text),
                    inline=False,
                )

        return builder.set_footer(
            text="💡 พิมพ์ /help [ชื่อคำสั่ง] เพื่อดูรายละเอียดเพิ่มเติม", emoji="❓"
        ).build()
