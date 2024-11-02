from typing import List, Dict, Any
import os


def validate_env_vars(required_vars: set) -> List[str]:
    """ตรวจสอบตัวแปรสภาพแวดล้อมที่จำเป็น"""
    return [var for var in required_vars if not os.getenv(var)]


def validate_bot_config(config: Dict[str, Any]) -> List[str]:
    """ตรวจสอบการตั้งค่าของ bot"""
    missing = []
    required_keys = {"command_prefix", "application_id", "token"}

    for key in required_keys:
        if key not in config or not config[key]:
            missing.append(key)

    return missing
