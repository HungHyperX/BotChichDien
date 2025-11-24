import discord
from discord.ext import commands
import requests
from datetime import datetime, timezone, timedelta
from flask import Flask
from threading import Thread

# Cấu hình intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
API_URL = "https://uma.moe/api/circles?circle_id={}"

@bot.event
async def on_ready():
    print(f"Bot đã online: {bot.user} (ID: {bot.user.id})")
    print("Bot đã sẵn sàng!")

@bot.command(name="checkcircle", aliases=["cc", "circle"])
async def checkcircle(ctx, circle_id: int):
    """Kiểm tra daily_fans của Circle + sắp xếp theo diff giảm dần"""
    await ctx.send(f"Đang kiểm tra Circle `{circle_id}`...")

    try:
        url = API_URL.format(circle_id)
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            await ctx.send(f"Lỗi API: {response.status_code}")
            return

        data = response.json()
        if not data or "members" not in data or not data["members"]:
            await ctx.send("Không tìm thấy circle hoặc không có thành viên.")
            return

        members = data["members"]
        today = datetime.now(timezone.utc).date()
        name_club = data["circle"]["name"]

        # Danh sách tạm để lưu thông tin mỗi thành viên
        results = []

        for mem in members:
            name = mem.get("trainer_name", "Unknown")
            daily = mem.get("daily_fans", [])
            updated_str = mem.get("last_updated", "")
            

            if not updated_str or len(daily) < 2:
                continue

            try:
                updated_dt = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
            except:
                continue

            # Chỉ lấy dữ liệu hôm nay hoặc hôm qua
            if updated_dt.date() not in (today, today - timedelta(days=1)):
                continue

            idx = updated_dt.day - 1
            if idx <= 0 or idx >= len(daily):
                continue

            current_fans = daily[idx]
            previous_fans = daily[idx - 1] if idx > 0 else 0
            diff = current_fans - previous_fans

            # Icon + thông báo
            if diff < 500_000:
                signal = f"⚠️"
                status = f"Chỉ cày được `{diff:,}` fans nên sẽ bị chích điện"
            else:
                signal = f"✅"
                status = f"đã thoát được hôm nay với `{diff:,}` fans"

            results.append({
                "signal": signal,
                "name": name,
                "diff": diff,
                "status": status
            })

        if not results:
            await ctx.send("Không có thành viên nào được cập nhật hôm nay hoặc dữ liệu chưa đủ.")
            return

        # Sắp xếp theo diff giảm dần (người cày nhiều nhất lên đầu)
        results.sort(key=lambda x: x["diff"], reverse=True)

        # Tạo tin nhắn
        msg = f"**Kết quả Club {name_club} {circle_id} - Ngày {today.day - 1}/{today.month}**\n\n"
        for i, r in enumerate(results, 1):
            msg += f"`{i:2}.` **{r['signal']}** **{r['name']}**: {r['status']}\n"

        # Chia nhỏ nếu quá dài
        if len(msg) > 1900:
            lines = msg.split('\n')
            chunk = ""
            for line in lines:
                if len(chunk) + len(line) + 1 > 1900:
                    await ctx.send(chunk)
                    chunk = line + "\n"
                else:
                    chunk += line + "\n"
            if chunk:
                await ctx.send(chunk)
        else:
            await ctx.send(msg)

    except requests.exceptions.RequestException as e:
        await ctx.send(f"Lỗi kết nối API: {e}")
    except Exception as e:
        await ctx.send(f"Lỗi không xác định: {e}")
        print(e)

# Keep alive cho Replit
app = Flask('')

@app.route('/')
def home():
    return "Bot đang online!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

keep_alive()

# Chạy bot
import os
bot.run(os.getenv("DISCORD_TOKEN"))