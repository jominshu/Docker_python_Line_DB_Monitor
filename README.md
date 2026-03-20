# 資料庫斷線Line通知機器人
## 說明
監控 PostgreSQL 指定資料表的最新資料時間，若超過門檻未更新就透過 LINE 發送通知。

## 功能重點
- 定期查詢最新資料時間(目前設定15分鐘)
- 超過設定時間立即發送首次警告(斷線超過1小時)
- 若仍未恢復，每天早上 8 點再提醒一次(可自由設定)
- 恢復正常後發送復原通知
- 內建每月訊息額度上限保護
- 可用環境變數關閉 LINE 通知（只寫日誌）

## 需求
- Docker + Docker Compose（建議）
- 或 Python 3.11
- 可連線的 PostgreSQL
- LINE Messaging API 的 Channel Access Token 與 User ID

## 設定
建立 `.env`（已在 `.gitignore` 中，不建議提交）：

```dotenv
# LINE Messaging API
LINE_CHANNEL_ACCESS_TOKEN=your_token
LINE_USER_ID=your_user_id

# PostgreSQL 連線
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_password

# 監控設定
TARGET_TABLE=your_table
TIME_COLUMN=created_at
CHECK_INTERVAL=300
ALERT_THRESHOLD=3600
ENABLE_LINE_NOTIFY=True
```

說明：
- `ENABLE_LINE_NOTIFY` 只有值為 `true`（不分大小寫）時才會啟用；其餘值都視為關閉。
- Windows + WSL Docker 可用 `DB_HOST=host.docker.internal` 連到 Windows 主機。

## 使用方式（Docker Compose）
```bash
docker compose up -d --build
docker compose logs -f
```

停止：
```bash
docker compose down
```

## 使用方式（本機執行）
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## 行為說明
- 每 `CHECK_INTERVAL` 秒檢查一次最新資料時間。
- 若無新資料超過 `ALERT_THRESHOLD` 秒，會發送第一次警告。
- 若仍未恢復，隔天早上 8 點再提醒一次。
- 資料恢復後會發送復原通知並重置狀態。

## 專案結構
- `main.py`：監控邏輯與 LINE 通知
- `docker-compose.yml`：服務啟動設定
- `Dockerfile`：容器建置設定
- `requirements.txt`：Python 依賴
