# 第二週部署：HTTPS、負載平衡與壓力測試

```
                                 ┌─▶ EC2 #1: Nginx :80 ─▶ FastAPI (Docker) ─┐
Client ──HTTPS──▶ Load Balancer ─┤                                          ├─▶ RDS (MySQL)
                  (ACM 憑證)     └─▶ EC2 #2: Nginx :80 ─▶ FastAPI (Docker) ─┘
                                            圖片：S3 + CloudFront
```

- Nginx 設定檔：[`nginx/wehelp-message-board.conf`](nginx/wehelp-message-board.conf)
- 健康檢查：`GET /health`
- 每個回應都有 `X-Served-By` 標頭（EC2 hostname），可確認流量有分到兩台 instance

## 1. 在 EC2 上用 Docker 執行 App

容器埠只綁 `127.0.0.1`，外部流量一律經過 Nginx；`--restart unless-stopped` 讓之後由 AMI 複製出來的 instance 開機就自動啟動。

```bash
sudo systemctl enable --now docker
docker build -t wehelp-message-board .
docker run -d --name message-board --restart unless-stopped \
  -p 127.0.0.1:8000:8000 --env-file .env wehelp-message-board
curl http://127.0.0.1:8000/health
```

需要提高單機吞吐量時，可在 `.env` 加上 `WEB_CONCURRENCY=2`（uvicorn worker 數，建議不超過 vCPU 數）。

## 2. 安裝 Nginx 並套用設定

```bash
sudo apt install -y nginx          # Amazon Linux：sudo dnf install -y nginx
sudo cp deploy/nginx/wehelp-message-board.conf /etc/nginx/conf.d/
sudo sed -i 's/example.com www.example.com/<你的網域>/' /etc/nginx/conf.d/wehelp-message-board.conf
sudo rm -f /etc/nginx/sites-enabled/default   # Ubuntu 預設站台會搶 80 port
```

> 取得憑證前 443 的 `ssl_certificate` 檔案還不存在，`nginx -t` 會失敗。可以先把 HTTPS `server` 區塊註解掉，完成第 3 步再打開。

## 3. SSL For Free 取得憑證（Nginx 支援 HTTPS）

1. 網域的 DNS A 紀錄先指向 EC2 的 Elastic IP，Security Group 開放 80 / 443。
2. 到 SSL For Free（ZeroSSL）申請 90 天免費憑證，驗證方式選 **HTTP File Upload**。
3. 把下載的驗證檔放到 Nginx 設定中預留的路徑：
   ```bash
   sudo mkdir -p /var/www/ssl-validation/.well-known/pki-validation
   sudo cp <驗證檔>.txt /var/www/ssl-validation/.well-known/pki-validation/
   curl http://<你的網域>/.well-known/pki-validation/<驗證檔>.txt   # 確認內容正確後回網站按驗證
   ```
4. 下載 Nginx 格式的憑證壓縮檔（`certificate.crt`、`ca_bundle.crt`、`private.key`），合併成 fullchain：
   ```bash
   sudo mkdir -p /etc/nginx/ssl/wehelp-message-board
   cd /etc/nginx/ssl/wehelp-message-board
   sudo sh -c 'cat certificate.crt; echo; cat ca_bundle.crt' | sudo tee fullchain.crt >/dev/null
   sudo chmod 600 private.key
   ```
5. 打開 HTTPS `server` 區塊，`sudo nginx -t && sudo systemctl reload nginx`。

## 4. 用 AMI 複製 Instance

1. EC2 Console → 選取 instance → **Actions → Image and templates → Create image**。
2. AMI 可用後 **Launch instance from AMI**，與原本 instance 放在**不同 AZ**，使用同一個 Security Group / IAM / Key pair。
3. 確認 RDS 的 Security Group 也允許新 instance 連線。
4. 在新 instance 上 `curl http://127.0.0.1/health -H 'X-Forwarded-Proto: https'` 應回 `{"status":"ok"}`。

## 5. 建立 Load Balancer（一對二）

1. **ACM 匯入同一張憑證**（與 ALB 同一個 region）：Certificate body = `certificate.crt`、Private key = `private.key`、Certificate chain = `ca_bundle.crt`。
2. **Target group**：Instances、HTTP : 80，Health check path `/health`、成功碼 `200`，註冊兩台 instance。
3. **Application Load Balancer**：Internet-facing，選兩台 instance 所在的 AZ。
   - Listener HTTPS : 443 → forward 到 target group，憑證選 ACM 匯入的那張。
   - Listener HTTP : 80 → Redirect 到 HTTPS : 443（301）。
4. **Security Group**：ALB 開 80 / 443 給 `0.0.0.0/0`；EC2 的 80 改成只允許 ALB 的 Security Group。
5. **DNS**：網域改指向 ALB 的 DNS name（Route 53 用 Alias A 紀錄；其他 DNS 用 CNAME 指向子網域）。

ALB 轉給 Nginx 的請求會帶 `X-Forwarded-Proto: https`，Nginx 直接代理不再導向；ALB 健康檢查打 `/health` 不會被導向；直接以 HTTP 連 EC2 則會 301 到 HTTPS。

## 6. Loader.io 壓力測試策略

### 網域驗證

1. Loader.io 新增 Target host（`https://<你的網域>`），取得 `loaderio-xxxxxxxx` token。
2. 在**兩台** instance 的 `.env` 設定 `LOADERIO_TOKEN=loaderio-xxxxxxxx`，重啟容器。
3. `curl https://<你的網域>/loaderio-xxxxxxxx/` 回傳 token 後，回 Loader.io 按 Verify。

### 測試端點

| 端點 | 目的 |
| --- | --- |
| `GET /` | 圖文頁面 HTML（Nginx → FastAPI 靜態檔），測整體轉發能力 |
| `GET /api/messages` | 圖文頁面實際載入的留言資料，會查詢 RDS，是主要瓶頸 |

### 測試步驟

1. **暖身**：Clients per test，250 clients / 1 分鐘，確認 0% error。
2. **找上限**：Clients per second（maintain client load），從 50 開始，每輪約加倍（50 → 100 → 200 → 400 …），每輪 1 分鐘。
3. **判定標準**：error rate > 1% 或平均回應時間 > 1000ms 即視為超過承受量；前一輪的 RPS 即為結果。
4. **對照組**：同樣測試分別打「單台 EC2 直連 HTTPS」與「ALB 兩台」，比較負載平衡的效果。
5. 每輪截圖：Loader.io 結果頁（RPS、平均 / 最大回應時間、成功 / 錯誤數）以及 ALB Target group 的 Monitoring（兩台 target 都有流量）。

### 結果紀錄

| 對象 | 端點 | Clients/s | 平均回應 (ms) | Error % | 結論 RPS |
| --- | --- | --- | --- | --- | --- |
| 單台 EC2 | `/api/messages` | | | | |
| ALB ×2 | `/api/messages` | | | | |

## 驗收項目

- [ ] `http://<網域>` 自動 301 到 `https://<網域>`，瀏覽器顯示有效憑證
- [ ] HTTPS 頁面可發表圖文、列表正常顯示（S3 / CloudFront / RDS 正常）
- [ ] 兩台 instance 在 Target group 都是 **healthy**
- [ ] 多次 `curl -sI https://<網域>/health | grep -i x-served-by` 會看到兩個不同的 hostname
- [ ] 停掉其中一台容器，網站仍可正常使用；恢復後重新變回 healthy
- [ ] Loader.io 完成網域驗證，產出單台與 ALB 的測試結果截圖並記錄 RPS
- [ ] 繳交：HTTPS 網址、Nginx 設定檔、Loading Test 截圖
