# logging_config.py
import logging
import sys
import codecs


class UnicodeStreamHandler(logging.StreamHandler):
    def __init__(self):
        # บังคับให้ใช้ UTF-8 encoding สำหรับ stdout
        if sys.stdout.encoding != "utf-8":
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
        super().__init__(sys.stdout)

    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # ตรวจสอบและแปลงข้อความให้เป็น UTF-8
            if isinstance(msg, str):
                stream.write(msg + self.terminator)
            else:
                stream.write(msg.encode("utf-8").decode("utf-8") + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


def setup_logging():
    # สร้าง logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # ลบ handler เดิมทั้งหมด
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # สร้าง handler ใหม่
    console_handler = UnicodeStreamHandler()
    file_handler = logging.FileHandler("bot.log", encoding="utf-8")

    # กำหนดรูปแบบข้อความ log
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # เพิ่ม formatter ให้กับ handler
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # เพิ่ม handler เข้าไปใน logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.info("\n\n-------------------------------------------------------------")
    logger.info("\n=== 📑 เริ่มต้นการทำงานของโปรแกรม ===")

    return logger
