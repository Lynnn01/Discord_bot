# Discord Bot

บอท Discord ที่พัฒนาด้วย Python และ discord.py library

## โครงสร้างไฟล์

├── run**.**py
├── requirements**.**txt
├── commands**/**
│   ├── __init__**.**py
│   ├── base_command**.**py
│   ├── ping_command**.**py
│   └── roll_command**.**py
├── cogs**/**
│   ├── __init__**.**py
│   ├── commands**.**py
│   └── event_handler**.**py
├── utils**/**
│   ├── __init__**.**py
│   ├── logging_config**.**py
│   └── embed_builder**.**py
└── bot**.**py

## การติดตั้ง

1. ติดตั้ง dependencies:

```bash
pip install discord.py python-dotenv
```

2. สร้างไฟล์ `.env` ในโฟลเดอร์โปรเจคและเพิ่มค่าต่อไปนี้:

```
DISCORD_TOKEN=your_bot_token_here
APPLICATION_ID=your_application_id_here
```

## การใช้งาน

1. รันบอทด้วยคำสั่ง:

```
bash
python bot.py
```

2. บอทจะทำการ:

- เชื่อมต่อกับ Discord
- Sync slash commands อัตโนมัติ
- แสดงรายการเซิร์ฟเวอร์ที่บอทเข้าร่วม

## คุณสมบัติ

- ใช้ระบบ Slash Commands
- แสดงสถานะการเชื่อมต่อกับเซิร์ฟเวอร์
- Command prefix: `!`

## การพัฒนา

บอทถูกพัฒนาโดยใช้:

- discord.py
- python-dotenv สำหรับจัดการตัวแปรสภาพแวดล้อม

## หมายเหตุ

อย่าลืมตั้งค่า:

1. Bot Token จาก Discord Developer Portal
2. Application ID ของบอท
3. เปิด Privileged Gateway Intents ทั้งหมดใน Discord Developer Portal
