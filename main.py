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

TARGET_TABLE = os.getenv('TARGET_TABLE')
TIME_COLUMN = os.getenv('TIME_COLUMN', 'created_at')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '300'))
ALERT_THRESHOLD = int(os.getenv('ALERT_THRESHOLD', '3600'))

already_notified = False
# ================================================

def send_line_message(text):
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
    if response.status_code != 200:
        print(f"[{datetime.now()}] LINE 發送失敗: {response.text}")

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
    global already_notified
    latest_time = get_latest_record_time()
    
    if latest_time is None:
        print(f"[{datetime.now()}] 找不到任何資料，或資料庫連線失敗。")
        return

    now = datetime.now()
    time_diff = (now - latest_time).total_seconds()
    print(f"[{datetime.now()}] 最新資料時間: {latest_time} (距今 {int(time_diff)} 秒)")

    if time_diff >= ALERT_THRESHOLD:
        if not already_notified:
            msg = f"⚠️ 設備異常警告 ⚠️\n資料庫已經超過 1 小時沒有新資料寫入！\n最後一筆資料時間：{latest_time.strftime('%Y-%m-%d %H:%M:%S')}"
            send_line_message(msg)
            already_notified = True
            print(f"[{datetime.now()}] 已發送斷線通知！")
    else:
        if already_notified:
            recovery_msg = f"✅ 設備已恢復正常\n資料庫已有新資料寫入！\n最新資料時間：{latest_time.strftime('%Y-%m-%d %H:%M:%S')}"
            send_line_message(recovery_msg)
            already_notified = False
            print(f"[{datetime.now()}] 設備恢復正常，狀態已重置。")

if __name__ == "__main__":
    print(f"[{datetime.now()}] 啟動資料庫寫入監控服務...")
    print(f"目標資料表: {TARGET_TABLE}, 檢查間隔: {CHECK_INTERVAL}秒, 警報閾值: {ALERT_THRESHOLD}秒")
    while True:
        monitor_database()
        time.sleep(CHECK_INTERVAL)