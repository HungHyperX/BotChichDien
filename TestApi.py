import discord
from discord.ext import commands
import requests
from datetime import datetime, timezone, timedelta

# Cấu hình intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # nếu cần

# Prefix lệnh là !
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

API_URL = "https://uma.moe/api/circles?circle_id={}"

@bot.event
async def on_ready():
    print(f"Bot đã online: {bot.user} (ID: {bot.user.id})")
    print("Bot đã sẵn sàng!")

@bot.command(name="checkcircle", aliases=["cc", "circle"])
async def checkcircle(ctx, circle_id: int):
    """Kiểm tra daily_fans của Club """
    await ctx.send(f"Đang kiểm tra Club `{circle_id}`... ⏳")

    try:
        url = API_URL.format(circle_id)
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            await ctx.send(f"Lỗi API: {response.status_code}")
            return
            
        data = response.json()
        
        # Kiểm tra xem có dữ liệu không
        if not data or "members" not in data or not data["members"]:
            await ctx.send("Không tìm thấy circle hoặc không có thành viên.")
            return

        members = data["members"]
        today = datetime.now(timezone.utc).date()  # Ngày hôm nay theo UTC
        msg = f"**Kết quả Circle {circle_id} - Ngày {today.day - 1}/{today.month}**\n\n"

        found_any = False
        for mem in members:
            name = mem.get("trainer_name", "Unknown")
            daily = mem.get("daily_fans", [])
            updated_str = mem.get("last_updated", "")

            if not updated_str or len(daily) < 2:
                continue

            # Parse thời gian cập nhật
            try:
                updated_dt = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
            except:
                continue

            # Chỉ lấy dữ liệu nếu được cập nhật hôm nay hoặc hôm qua
            if updated_dt.date() not in (today, today - timedelta(days=1)):
                continue

            # Tìm index tương ứng với hôm nay
            latest_day = updated_dt.day
            idx = latest_day - 1  # vì mảng bắt đầu từ index 0

            if idx <= 0 or idx >= len(daily):
                continue

            current_fans = daily[idx]
            previous_fans = daily[idx - 1] if idx > 0 else 0
            diff = current_fans - previous_fans
            found_any = True

            if diff < 500_000:
                msg += f"⚠️ **{name}**: Chỉ cày được `{diff:,}` fans nên sẽ bị chích điện\n"
            else:
                msg += f"✅ **{name}**: đã thoát được hôm nay với `{diff:,}` fans\n"

        if not found_any:
            msg += "Không có thành viên nào được cập nhật hôm nay hoặc dữ liệu chưa đủ."

        # Chia tin nhắn nếu quá dài
        if len(msg) > 1900:
            parts = [msg[i:i+1900] for i in range(0, len(msg), 1900)]
            for part in parts:
                await ctx.send(part)
        else:
            await ctx.send(msg)

    except requests.exceptions.RequestException as e:
        await ctx.send(f"Lỗi kết nối API: {e}")
    except Exception as e:
        await ctx.send(f"Lỗi không xác định: {e}")
        print(e)  # in ra console để debug

# Thay TOKEN của bạn vào đây
import os
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)