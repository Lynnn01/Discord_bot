from typing import Optional

class BotError(Exception):
    """Base exception class สำหรับ bot"""
    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code
        super().__init__(message)

class UserError(BotError):
    """Exception สำหรับข้อผิดพลาดที่เกิดจากผู้ใช้"""
    pass

class DevModeError(BotError):
    """Exception สำหรับข้อผิดพลาดที่เกี่ยวกับ Dev Mode"""
    pass

class PermissionError(BotError):
    """Exception สำหรับข้อผิดพลาดเกี่ยวกับสิทธิ์"""
    def __init__(self, message: str, missing_perms: list[str]):
        self.missing_perms = missing_perms
        super().__init__(message)
