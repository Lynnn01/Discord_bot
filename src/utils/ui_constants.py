from discord import Color

class UIConstants:
    """ค่าคงที่สำหรับ UI ทั้งระบบ"""
    
    # สีมาตรฐาน
    COLORS = {
        "success": Color.green(),
        "error": Color.red(), 
        "warning": Color.yellow(),
        "info": Color.blue(),
        "default": Color.blurple(),
        "gold": Color.gold(),
        "greyple": Color.greyple()
    }
    
    # Emoji มาตรฐาน
    EMOJI = {
        # สถานะทั่วไป
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "loading": "⏳",
        "done": "✨",
        
        # หมวดหมู่
        "commands": "🎮",
        "settings": "⚙️",
        "tools": "🛠️",
        "fun": "🎲",
        "dev": "👨‍💻",
        
        # อื่นๆ
        "ping": "🏓",
        "stats": "📊",
        "time": "⏰",
        "user": "👤",
        "server": "🏠",
        "help": "❔",
        "search": "🔍",
        "new": "✨",
        "edit": "📝",
        "delete": "🗑️",
        "refresh": "🔄",
        "link": "🔗",
        "lock": "🔒",
        "unlock": "🔓",
        "star": "⭐",
        "crown": "👑"
    }
    
    # ข้อความสถานะมาตรฐาน 
    STATUS_MESSAGES = {
        "loading": "กำลังดำเนินการ...",
        "success": "ดำเนินการสำเร็จ",
        "error": "เกิดข้อผิดพลาด",
        "not_found": "ไม่พบข้อมูล",
        "no_permission": "คุณไม่มีสิทธิ์"
    }
