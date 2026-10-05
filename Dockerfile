FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static

EXPOSE 8000

# 部署在 Nginx / Load Balancer 後方，信任 X-Forwarded-* 標頭以取得真實 client IP 與協定
# 容器埠只綁定 127.0.0.1，外部流量必須經過 Nginx
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
