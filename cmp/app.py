import json, time, hashlib, requests, random
from datetime import datetime
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ===== 載入設定 =====
with open("monitors.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

WEBHOOK = cfg["webhook"]
INTERVAL = cfg.get("interval_sec", 120)
COOLDOWN = cfg.get("cooldown_sec", 300)

# ===== Selenium =====
opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--disable-gpu")
driver = webdriver.Chrome(options=opts)

# ===== 狀態 =====
last_hash = {}
last_counts = {}
last_notify_time = {}

# ===== 抓網頁（升級版）=====
def fetch(url):
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.area"))
        )
    except:
        print("⚠️ 沒抓到座位，重試")
        driver.refresh()
        time.sleep(5)

    return driver.page_source

# ===== 解析 =====
def parse_tixcraft(html):
    soup = BeautifulSoup(html, "html.parser")

    seats = []
    for a in soup.select("a.area"):
        text = a.get_text(strip=True)
        if "剩餘" in text:
            seats.append(text)

    title = soup.title.string if soup.title else "活動"

    text_all = soup.get_text(" ", strip=True)
    time_info = ""
    for part in text_all.split():
        if "/" in part or "202" in part:
            time_info = part
            break

    return seats, title, time_info

# ===== Discord通知 =====
def send_embed(name, url, seats, title, event_time):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count = len(seats)

    color = 0x2ecc71 if count > 0 else 0xe74c3c

    seat_text = "\n".join([f"• {s}" for s in seats[:6]]) if seats else "無"

    payload = {
        "content": "@清票通知" if count > 0 else None,
        "embeds": [{
            "title": f"⚡ {name} 有票釋出！⚡" if count > 0 else f"{name} 狀態更新",
            "url": url,
            "description": f"🎤 {title}\n🕒 {event_time}",
            "color": color,
            "fields": [
                {"name": "🎫 區域狀態", "value": seat_text, "inline": False},
                {"name": "📊 區域數", "value": str(count), "inline": True},
                {"name": "⏰ 偵測時間", "value": now, "inline": True}
            ],
            "footer": {"text": "票務監控系統 Ultimate"}
        }]
    }

    requests.post(WEBHOOK, json=payload)

# ===== 主程式 =====
while True:
    for m in cfg["items"]:
        name = m["name"]
        url = m["url"]

        try:
            html = fetch(url)
            seats, title, event_time = parse_tixcraft(html)

            count = len(seats)
            current_hash = hashlib.md5("\n".join(sorted(seats)).encode()).hexdigest()
            now = time.time()

            # ===== 判斷條件 =====
            changed = name not in last_hash or last_hash[name] != current_hash
            cooldown_ok = now - last_notify_time.get(name, 0) > COOLDOWN

            increased = count > last_counts.get(name, 0)
            first_appear = last_counts.get(name, 0) == 0 and count > 0

            # ⭐ 最終條件
            if changed and cooldown_ok and (increased or first_appear):
                send_embed(name, url, seats, title, event_time)
                last_notify_time[name] = now
                print(f"[通知] {name}")

            last_hash[name] = current_hash
            last_counts[name] = count

            print(f"[狀態] {name}：{count} 區")

        except Exception as e:
            print(f"[錯誤] {name}:", e)

    time.sleep(INTERVAL)