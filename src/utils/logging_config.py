# utils/logging_config.py

import logging
import sys
import codecs
from datetime import datetime
from pathlib import Path
from typing import Optional


class CustomFormatter(logging.Formatter):
    """
    Custom formatter ที่รองรับสี และ emoji สำหรับระดับ log ต่างๆ
    """

    # สีสำหรับแต่ละระดับ log
    COLORS = {
        "DEBUG": "\033[37m",  # GRAY
        "INFO": "\033[32m",  # GREEN
        "WARNING": "\033[33m",  # YELLOW
        "ERROR": "\033[31m",  # RED
        "CRITICAL": "\033[41m",  # RED BACKGROUND
    }

    # Emoji สำหรับแต่ละระดับ log
    EMOJIS = {
        "DEBUG": "🔍",
        "INFO": "✨",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "🚨",
    }

    def format(self, record):
        # เพิ่ม emoji และสีตามระดับ log
        if not hasattr(record, "emoji"):
            record.emoji = self.EMOJIS.get(record.levelname, "")

        if sys.stderr.isatty():  # ตรวจสอบว่ารองรับการแสดงสีหรือไม่
            color = self.COLORS.get(record.levelname, "")
            reset = "\033[0m"
            record.levelname = f"{color}{record.emoji} {record.levelname}{reset}"
        else:
            record.levelname = f"{record.emoji} {record.levelname}"

        return super().format(record)


class UnicodeStreamHandler(logging.StreamHandler):
    """
    Handler ที่รองรับ UTF-8 encoding สำหรับ console output
    """

    def __init__(self):
        if sys.stdout.encoding != "utf-8":
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
        super().__init__(sys.stdout)

    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            if isinstance(msg, str):
                stream.write(msg + self.terminator)
            else:
                stream.write(msg.encode("utf-8").decode("utf-8") + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


class RotatingFileHandler(logging.FileHandler):
    """
    Handler ที่สร้างไฟล์ log ใหม่ทุกวัน
    """

    def __init__(self, base_path: str, encoding: Optional[str] = None):
        self.base_path = Path(base_path)
        self.base_path.parent.mkdir(parents=True, exist_ok=True)

        filename = self._get_log_filename()
        super().__init__(filename, encoding=encoding)

    def _get_log_filename(self) -> str:
        """สร้างชื่อไฟล์ log ตามวันที่"""
        today = datetime.now().strftime("%Y-%m-%d")
        return str(self.base_path.parent / f"{self.base_path.stem}_{today}.log")


def setup_logger(log_path: str = "logs/bot.log") -> logging.Logger:
    """
    ตั้งค่าระบบ logging

    Args:
        log_path: ที่อยู่ของไฟล์ log

    Returns:
        logging.Logger: configured logger instance
    """
    # สร้าง logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # ลบ handler เดิม
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # สร้าง formatter
    detailed_formatter = CustomFormatter(
        "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    simple_formatter = CustomFormatter("%(levelname)s - %(message)s")

    # สร้างและตั้งค่า console handler
    console_handler = UnicodeStreamHandler()
    console_handler.setFormatter(simple_formatter)
    console_handler.setLevel(logging.INFO)

    # สร้างและตั้งค่า file handler
    file_handler = RotatingFileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(detailed_formatter)
    file_handler.setLevel(logging.DEBUG)

    # เพิ่ม handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # บันทึก log เริ่มต้น
    logger.info("=" * 50)
    logger.info("🚀 เริ่มต้นการทำงานของระบบ")
    logger.debug(f"📁 บันทึก log ที่: {log_path}")

    return logger


# ตัวอย่างการใช้งาน
if __name__ == "__main__":
    logger = setup_logger()

    # ทดสอบ log ระดับต่างๆ
    logger.debug("🔍 นี่คือข้อความ Debug")
    logger.info("✨ นี่คือข้อความ Info")
    logger.warning("⚠️ นี่คือข้อความ Warning")
    logger.error("❌ นี่คือข้อความ Error")
    logger.critical("🚨 นี่คือข้อความ Critical")
