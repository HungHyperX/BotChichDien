import discord
from discord.ext import commands, tasks
import requests
from datetime import datetime, timezone, timedelta, time
from flask import Flask
from threading import Thread
import asyncio

# ================== CẤU HÌNH CỦA BẠN ==================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
API_URL = "https://uma.moe/api/circles?circle_id={}"

# THAY 2 DÒNG NÀY BẰNG CỦA BẠN
CIRCLE_ID_TO_CHECK = 230947009  # ← ID Circle chính (Strategist)
CHANNEL_ID_TO_SEND = 1442395967369511054  # ← ID kênh nhận báo cáo tự động 7h sáng
# ====================================================


@bot.event
async def on_ready():
    print(f"Bot đã online: {bot.user} (ID: {bot.user.id})")
    print("Bot đã sẵn sàng!")
    auto_keep_awake.start()
    daily_check_circle.start()


# Task 1: Giữ Replit awake mỗi 12 phút
@tasks.loop(minutes=5)
async def auto_keep_awake():
    try:
        requests.get("https://uma.moe/api/circles?circle_id=1", timeout=10)
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] Auto ping – Replit awake!"
        )
    except:
        pass


# Task 2: Tự động check + gửi kênh lúc 7h sáng giờ Việt Nam
@tasks.loop(hours=24)
async def daily_check_circle():
    vn_time = datetime.now(timezone(timedelta(hours=7)))
    if vn_time.hour != 11 or vn_time.minute > 10:  # Chỉ chạy 1 lần trong 10 phút đầu giờ 7
        return

    channel = bot.get_channel(CHANNEL_ID_TO_SEND)
    if not channel:
        print("Không tìm thấy kênh tự động!")
        return

    await channel.send("Đang tự động kiểm tra Circle lúc **7h sáng**...")
    await run_check_and_send(CIRCLE_ID_TO_CHECK, channel)


# Hàm chung để xử lý check circle (dùng cho cả lệnh thủ công và tự động)
async def run_check_and_send(circle_id: int, destination):
    try:
        response = requests.get(API_URL.format(circle_id), timeout=15)
        if response.status_code != 200:
            await destination.send(f"Lỗi API: {response.status_code}")
            return

        data = response.json()
        if not data or "circle" not in data or not data.get("members"):
            await destination.send("Không tìm thấy dữ liệu circle.")
            return

        circle_name = data["circle"]["name"]
        members = data["members"]
        today = datetime.now(timezone.utc).date()

        results = []
        for mem in members:
            name = mem.get("trainer_name", "Unknown")
            daily = mem.get("daily_fans", [])
            updated_str = mem.get("last_updated", "")
            if not updated_str or len(daily) < 2:
                continue
            try:
                updated_dt = datetime.fromisoformat(
                    updated_str.replace("Z", "+00:00"))
            except:
                continue
            if updated_dt.date() not in (today, today - timedelta(days=1)):
                continue
            idx = updated_dt.day - 1
            if idx <= 0 or idx >= len(daily):
                continue

            diff = daily[idx] - (daily[idx - 1] if idx > 0 else 0)
            signal = "✅" if diff >= 500_000 else "⚠️"
            status = f"đã thoát được hôm nay với `{diff:,}` fans" if diff >= 500_000 else f"Chỉ cày được `{diff:,}` fans nên sẽ bị chích điện"

            results.append({
                "signal": signal,
                "name": name,
                "diff": diff,
                "status": status
            })

        if not results:
            await destination.send(
                "Không có thành viên nào được cập nhật hôm nay.")
            return

        results.sort(key=lambda x: x["diff"], reverse=True)

        msg = f"**Club {circle_name} ({circle_id})**\n"
        msg += f"**Ngày {(today - timedelta(days=1)).day}/{today.month}**\n\n"
        for i, r in enumerate(results, 1):
            msg += f"`{i:2}.` **{r['signal']} {r['name']}**: {r['status']}\n"

        # Chia nhỏ nếu quá dài
        if len(msg) > 1900:
            for part in [msg[i:i + 1900] for i in range(0, len(msg), 1900)]:
                await destination.send(part)
        else:
            await destination.send(msg)

    except Exception as e:
        await destination.send(f"Lỗi: {e}")
        print(e)


# LỆNH THỦ CÔNG: !cc hoặc !circle (có thể bỏ trống ID → dùng ID mặc định)
@bot.command(name="checkcircle", aliases=["cc", "circle"])
async def checkcircle(ctx, circle_id: int = None):
    if circle_id is None:
        circle_id = CIRCLE_ID_TO_CHECK  # Dùng circle chính nếu không nhập ID
    await ctx.send(f"Đang kiểm tra Circle `{circle_id}`...")
    await run_check_and_send(circle_id, ctx)  # Dùng lại hàm chung


# Keep alive dự phòng
app = Flask('')


@app.route('/')
def home():
    return "Bot 24/7 + Auto 7h sáng đã bật!"


def run_flask():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run_flask)
    t.start()


keep_alive()

import os

bot.run(os.getenv("DISCORD_TOKEN"))
