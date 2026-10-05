# WeHelp Message Board

WeHelp 後端第一週作業：圖文留言板。使用者可以留言並附一張圖片，頁面會顯示留言列表。圖片存放在 AWS S3，透過 CloudFront 提供；留言資料存放在 AWS RDS；以 Docker 部署到 EC2。後端使用 Python + FastAPI。

## 本機開發

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填入 AWS / RDS 設定
uvicorn app.main:app --reload
```

啟動後開啟：
- http://localhost:8000/
- http://localhost:8000/health
- http://localhost:8000/docs

## API

- `GET /api/messages`：留言列表
- `POST /api/messages`：`multipart/form-data`，欄位 `content`、`image`

## Docker

```bash
docker build -t wehelp-message-board .
docker run -p 8000:8000 --env-file .env wehelp-message-board
```

## 第二週：HTTPS、負載平衡與壓力測試

Nginx 反向代理 + SSL For Free 憑證、AMI 複製 instance 搭配 Load Balancer 一對二架構、Loader.io 壓力測試，步驟與驗收項目見 [`deploy/README.md`](deploy/README.md)，Nginx 設定檔在 [`deploy/nginx/wehelp-message-board.conf`](deploy/nginx/wehelp-message-board.conf)。

- `GET /health`：Load Balancer 健康檢查
- `GET /loaderio-<token>/`：Loader.io 網域驗證（需設定 `LOADERIO_TOKEN`）

## 資料庫

見 `schema.sql`。應用啟動時會自動 `CREATE TABLE IF NOT EXISTS messages`。
