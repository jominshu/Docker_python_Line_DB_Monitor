import os
import time
import requests
import psycopg2
from datetime import datetime

# ================= 讀取環境變數 =================
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': os.getenv('DB_PORT', '5432'),
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

# 讀取 LINE 發送開關 (預設為 True)
ENABLE_LINE_NOTIFY = os.getenv('ENABLE_LINE_NOTIFY', 'True').lower() == 'true'

TARGET_TABLE = os.getenv('TARGET_TABLE')
TIME_COLUMN = os.getenv('TIME_COLUMN', 'created_at')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '300'))
ALERT_THRESHOLD = int(os.getenv('ALERT_THRESHOLD', '3600'))

# ================= 狀態記錄區 =================
already_notified = False
last_notified_date = None

# LINE 配額自動計數器
current_month = datetime.now().month
monthly_message_count = 0
MESSAGE_LIMIT = 190  # 免費額度 200，我們設 190 留點緩衝
# ================================================

def send_line_message(text):
    global current_month, monthly_message_count
    now = datetime.now()

    # 【修復重點】：檢查是否啟用 LINE 通知開關
    if not ENABLE_LINE_NOTIFY:
        print(f"[{now}] 🔕 (LINE 開關已關閉) 攔截訊息: {text}")
        return

    # 1. 檢查是否換月了？如果是，把計數器歸零
    if now.month != current_month:
        current_month = now.month
        monthly_message_count = 0
        print(f"[{now}] 📅 新的月份開始！LINE 訊息配額已自動歸零。")

    # 2. 檢查是否已經達到本月上限
    if monthly_message_count >= MESSAGE_LIMIT:
        print(f"[{now}] 🛑 攔截通知：本月 LINE 訊息已達上限 ({monthly_message_count}/{MESSAGE_LIMIT})，暫停推播。")
        print(f"未發送的訊息內容：\n{text}")
        return  # 直接中斷，不呼叫 LINE API

    # 3. 正常發送邏輯
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }
    data = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": text}]
    }
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        monthly_message_count += 1
        print(f"[{now}] LINE 發送成功！(本月已用額度: {monthly_message_count}/{MESSAGE_LIMIT})")
    else:
        print(f"[{now}] LINE 發送失敗: {response.text}")
        
def get_latest_record_time():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        query = f"SELECT MAX({TIME_COLUMN}) FROM {TARGET_TABLE};"
        cursor.execute(query)
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"[{datetime.now()}] 資料庫查詢發生錯誤: {e}")
        return None

def monitor_database():
    global already_notified, last_notified_date
    latest_time = get_latest_record_time()
    
    if latest_time is None:
        print(f"[{datetime.now()}] 找不到任何資料，或資料庫連線失敗。")
        return

    now = datetime.now()
    time_diff = (now - latest_time).total_seconds()
    print(f"[{datetime.now()}] 最新資料時間: {latest_time} (距今 {int(time_diff)} 秒)")

    if time_diff >= ALERT_THRESHOLD:
        if not already_notified:
            # 【情境 1】剛發現斷線超過 1 小時：立即發送首次通知
            msg = f"⚠️ 設備異常警告 ⚠️\n資料庫已經超過 {ALERT_THRESHOLD} 秒沒有新資料寫入！\n最後一筆資料時間：{latest_time.strftime('%Y-%m-%d %H:%M:%S')}"
            send_line_message(msg)
            already_notified = True
            last_notified_date = now.date()  # 記錄今天日期
            print(f"[{datetime.now()}] 已發送首次斷線通知！")
            
        else:
            # 【情境 2】已經處於斷線狀態：檢查是否需要發送「每日早上 8 點」的奪命連環 Call
            if now.date() > last_notified_date and now.hour >= 8:
                msg = f"🔔 持續斷線提醒 🔔\n設備尚未修復！\n最後一筆資料時間仍為：{latest_time.strftime('%Y-%m-%d %H:%M:%S')}"
                send_line_message(msg)
                last_notified_date = now.date()  # 更新最後通知日期為今天
                print(f"[{datetime.now()}] 已發送每日早上 8 點持續斷線提醒！")
                
    else:
        # 【情境 3】設備恢復正常
        if already_notified:
            recovery_msg = f"✅ 設備已恢復正常\n資料庫已有新資料寫入！\n最新資料時間：{latest_time.strftime('%Y-%m-%d %H:%M:%S')}"
            send_line_message(recovery_msg)
            already_notified = False
            last_notified_date = None  # 狀態歸零
            print(f"[{datetime.now()}] 設備恢復正常，狀態已重置。")

if __name__ == "__main__":
    print(f"[{datetime.now()}] 啟動資料庫寫入監控服務...")
    print(f"目標資料表: {TARGET_TABLE}, 檢查間隔: {CHECK_INTERVAL}秒, 警報閾值: {ALERT_THRESHOLD}秒")
    while True:
        monitor_database()
        time.sleep(CHECK_INTERVAL)