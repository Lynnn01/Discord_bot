import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict


class PrettyFormatter(logging.Formatter):
    """สร้าง log format ที่สวยงามและอ่านง่าย"""

    # สีที่ใช้งานบ่อย
    COLORS = {
        "WHITE": "\033[37m",
        "GREEN": "\033[32m",
        "YELLOW": "\033[33m",
        "RED": "\033[31m",
        "BOLD_RED": "\033[31;1m",
        "RESET": "\033[0m",
    }

    # สีสำหรับแต่ละระดับ log
    LEVEL_COLORS = {
        "DEBUG": COLORS["WHITE"],
        "INFO": COLORS["GREEN"],
        "WARNING": COLORS["YELLOW"],
        "ERROR": COLORS["RED"],
        "CRITICAL": COLORS["BOLD_RED"],
    }

    # Emoji และ prefix สำหรับแต่ละระดับ
    LEVEL_STYLES = {
        "DEBUG": ("🔍", "DEBUG"),
        "INFO": ("✨", "INFO"),
        "WARNING": ("⚠️", "WARN"),
        "ERROR": ("❌", "ERROR"),
        "CRITICAL": ("💥", "FATAL"),
    }

    def __init__(self, colored: bool = True):
        """
        Args:
            colored: เปิด/ปิดการแสดงสี
        """
        self.colored = colored and sys.stderr.isatty()
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        # รับ emoji และ prefix
        emoji, prefix = self.LEVEL_STYLES.get(record.levelname, ("", record.levelname))

        # จัดรูปแบบเวลา
        time_str = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")

        # สร้าง prefix สำหรับ log
        if self.colored:
            color = self.LEVEL_COLORS.get(record.levelname, "")
            level_prefix = f"{color}{emoji} {prefix:5}{self.COLORS['RESET']}"
        else:
            level_prefix = f"{emoji} {prefix:5}"

        # ส่วนของไฟล์และบรรทัด (แสดงเฉพาะ debug)
        if record.levelno == logging.DEBUG:
            file_info = f"[{record.filename}:{record.lineno}] "
        else:
            file_info = ""

        # รวมข้อความ log
        return f"{time_str} {level_prefix} {file_info}{record.getMessage()}"


def setup_logger(log_dir: str = "logs") -> logging.Logger:
    """ตั้งค่า logger ที่สวยงามและใช้งานง่าย

    Args:
        log_dir: โฟลเดอร์สำหรับเก็บไฟล์ log

    Returns:
        Logger ที่ตั้งค่าแล้ว
    """
    # สร้าง logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # ล้าง handler เก่า
    logger.handlers.clear()

    # ตั้งค่า console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(PrettyFormatter(colored=True))
    logger.addHandler(console)

    # ตั้งค่า file handler
    try:
        # สร้างโฟลเดอร์ถ้ายังไม่มี
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # สร้างไฟล์ log ตามวันที่
        today = datetime.now().strftime("%Y-%m-%d")
        file_handler = logging.FileHandler(
            log_path / f"bot_{today}.log", encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(PrettyFormatter(colored=False))
        logger.addHandler(file_handler)

    except Exception as e:
        console.error(f"ไม่สามารถสร้างไฟล์ log ได้: {e}")

    return logger


if __name__ == "__main__":
    # ตัวอย่างการใช้งาน
    logger = setup_logger()

    logger.debug("เริ่มโหลดการตั้งค่า...")
    logger.info("บอทพร้อมใช้งานแล้ว")
    logger.warning("พบการเชื่อมต่อที่ช้า")
    logger.error("ไม่สามารถเชื่อมต่อกับฐานข้อมูลได้")
    logger.critical("บอทหยุดทำงานเนื่องจากข้อผิดพลาดร้ายแรง")
