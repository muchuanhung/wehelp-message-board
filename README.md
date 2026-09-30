# WeHelp Message Board

WeHelp 後端第一週作業：圖文留言板。使用者可以留言並附一張圖片，頁面會顯示留言列表。圖片存放在 AWS S3，透過 CloudFront 提供；留言資料存放在 AWS RDS；以 Docker 部署到 EC2。後端使用 Python + FastAPI。

## 本機開發

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

啟動後開啟：
- http://localhost:8000/health
- http://localhost:8000/docs

## Docker

```bash
docker build -t wehelp-message-board .
docker run -p 8000:8000 --env-file .env wehelp-message-board
```
