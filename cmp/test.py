from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import requests
from datetime import datetime

WEBHOOK_URL = "https://discordapp.com/api/webhooks/1499790908307148891/ymhlvnx7TNQBL2j6eV7ueFOw2F1AErMXNwPdhOvSJCes3Daz5x86_v-oAUv6BHY1luch"
URL = "https://tixcraft.com/ticket/area/26_kyuhyun/22386"

# 👉 無頭模式（不開視窗）
options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")

driver = webdriver.Chrome(options=options)

def get_seat_data():
    driver.get(URL)
    time.sleep(5)  # 等JS載入

    soup = BeautifulSoup(driver.page_source, "html.parser")

    result = []

    # 👉 抓區域資料（拓元常見結構）
    areas = soup.find_all("a", class_="area")

    for a in areas:
        text = a.get_text(strip=True)

        # 範例：A2區 5680元 剩餘4
        if "剩餘" in text:
            result.append(text)

    return result

def send_discord(seat_list):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    description = f"⏰ 清票時間：{now}\n\n"

    if seat_list:
        description += "🛒 購買狀態：剩餘票券\n\n"
        for s in seat_list[:5]:  # 👉 最多顯示5個（避免太長）
            description += f"🎫 {s}\n"
    else:
        description += "❌ 目前無可購票區域"

    requests.post(WEBHOOK_URL, json={
        "content": "@清票通知",
        "embeds": [
            {
                "title": "⚡ KYUHYUN Fanmeeting 清票囉 ⚡",
                "url": URL,
                "color": 65280 if seat_list else 16711680,
                "description": description,
                "footer": {
                    "text": "拓元票務監控系統"
                }
            }
        ]
    })

# 👉 狀態記錄（避免洗版）
last_data = []

while True:
    try:
        current = get_seat_data()

        if current != last_data:
            print("狀態變化！")
            send_discord(current)
            last_data = current
        else:
            print("無變化")

    except Exception as e:
        print("錯誤:", e)

    time.sleep(120)