from discord.ext import commands
from discord import app_commands

ERROR_MESSAGES = {
    commands.MissingPermissions: "คุณไม่มีสิทธิ์ในการใช้คำสั่งนี้",
    commands.BotMissingPermissions: "บอทไม่มีสิทธิ์ที่จำเป็น",
    commands.MissingRequiredArgument: "กรุณาระบุข้อมูลให้ครบถ้วน", 
    commands.BadArgument: "รูปแบบข้อมูลไม่ถูกต้อง",
    commands.CommandOnCooldown: "กรุณารอสักครู่ก่อนใช้คำสั่งนี้อีกครั้ง",
    app_commands.CommandOnCooldown: "กรุณารอ {retry_after:.1f} วินาที",
    app_commands.MissingPermissions: "คุณไม่มีสิทธิ์ใช้คำสั่งนี้"
}
