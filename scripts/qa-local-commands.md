# Lệnh QA Local

Tài liệu này ghi lại các lệnh thường dùng để chạy stack local, chạy smoke test, chạy edge-client, và debug lỗi cơ bản trên máy phát triển.

## 1. Script Mặc Định Chạy Gì?

Script `scripts/qa-local-compose.ps1` mặc định dùng hai file compose:

```text
docker-compose.yml
docker-compose.dev.yml
```

Nghĩa là script sẽ chạy stack local chuẩn:

- backend
- worker
- frontend-admin
- nginx
- db
- redis
- minio

Mặc định chưa chạy `edge-client`.

## 2. Khi Nào Edge-Client Được Chạy?

Edge-client chỉ được thêm khi dùng cờ:

```powershell
-IncludeEdge
```

Chạy QA có edge-client:

```powershell
.\scripts\qa-local-compose.ps1 -Action qa -IncludeEdge
```

Up stack có edge-client:

```powershell
.\scripts\qa-local-compose.ps1 -Action up -IncludeEdge
```

Khi đã dùng `-IncludeEdge`, bạn không cần mở thêm cửa sổ riêng để chạy edge-client, vì edge-client sẽ chạy bằng container từ `docker-compose.edge.yml`.

## 3. Bộ Lệnh Khuyến Nghị Bằng Script

Chạy smoke QA local:

```powershell
.\scripts\qa-local-compose.ps1 -Action qa
```

Chạy smoke QA local và build image trước khi test:

```powershell
.\scripts\qa-local-compose.ps1 -Action qa -Build
```

Chạy smoke QA local và build sạch không dùng cache:

```powershell
.\scripts\qa-local-compose.ps1 -Action qa -Build -NoCache
```

Chạy smoke QA local kèm edge-client:

```powershell
.\scripts\qa-local-compose.ps1 -Action qa -IncludeEdge
```

Up local stack:

```powershell
.\scripts\qa-local-compose.ps1 -Action up
```

Up local stack và build image trước:

```powershell
.\scripts\qa-local-compose.ps1 -Action up -Build
```

Build không dùng cache:

```powershell
.\scripts\qa-local-compose.ps1 -Action up -Build -NoCache
```

Xem trạng thái service:

```powershell
.\scripts\qa-local-compose.ps1 -Action ps
```

Xem log:

```powershell
.\scripts\qa-local-compose.ps1 -Action logs
```

Xem log realtime:

```powershell
.\scripts\qa-local-compose.ps1 -Action logs -Follow
```

Restart stack:

```powershell
.\scripts\qa-local-compose.ps1 -Action restart
```

Tắt stack:

```powershell
.\scripts\qa-local-compose.ps1 -Action down
```

## 4. Chạy Edge-Client Local Và Container

### 4.1. Chạy Trực Tiếp Trên Máy Tính

Cách này phù hợp khi bạn đang test camera trên Windows. Container Linux trên Docker Desktop thường không truy cập webcam Windows trực tiếp như `/dev/video0`.

Nên dùng venv riêng trong thư mục `edge-client`, không dùng chung root `.venv` nếu root venv đã cài tooling như `semgrep` hoặc `pip-audit`.

```powershell
cd edge-client

if (Get-Command deactivate -ErrorAction SilentlyContinue) { deactivate }

py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1

.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check

$env:EDGE_BACKEND_ENABLED = "true"
$env:EDGE_UI_MODE = "web"
$env:EDGE_KIOSK_PORT = "8080"
$env:API_BASE_URL = "http://localhost"

.\.venv\Scripts\python.exe main.py
```

Mở kiosk UI:

```text
http://localhost:8080
```

Nếu muốn chạy UI OpenCV cũ:

```powershell
$env:EDGE_UI_MODE = "opencv"
.\.venv\Scripts\python.exe main.py
```

Nếu muốn chạy bằng package entrypoint:

```powershell
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m edge_client
```

### 4.2. Chạy Bằng Container

Chạy toàn bộ stack kèm edge-client:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.edge.yml up -d --build
```

Hoặc dùng script:

```powershell
.\scripts\qa-local-compose.ps1 -Action up -IncludeEdge
```

Restart riêng edge-client container:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.edge.yml restart edge-client
```

Xem log edge-client:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.edge.yml logs -f edge-client
```

## 5. Health Check Đúng Endpoint

Up local stack:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

Up local stack kèm edge-client:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.edge.yml up -d --build
```

Kiểm tra service:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml ps
```

Xem log:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f
```

Tắt local stack:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.edge.yml down --remove-orphans
```

Backend root health qua nginx:

```powershell
Invoke-WebRequest http://localhost/health
```

Admin API health:

```powershell
Invoke-WebRequest http://localhost/api/admin/health
```

Admin UI:

```powershell
Invoke-WebRequest http://localhost/admin/
```

Enrollment compatibility redirect:

```powershell
Invoke-WebRequest http://localhost/enroll/
```

## 6. Troubleshooting Khi `-Action qa` Bị Timeout

Nếu script báo timeout ở `http://localhost/health`, nguyên nhân thường là backend chưa start thành công dù container đang `Up`.

Kiểm tra nhanh:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml ps
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs backend --tail 100
```

Lỗi hay gặp:

- dependency mismatch, ví dụ `numpy` và `opencv-python`
- migration chưa chạy
- biến môi trường thiếu hoặc sai
- backend fail khi import DeepFace/runtime dependency

Ưu tiên build lại image rồi chạy QA:

```powershell
.\scripts\qa-local-compose.ps1 -Action qa -Build
```

Nếu vẫn lỗi, build sạch:

```powershell
.\scripts\qa-local-compose.ps1 -Action qa -Build -NoCache
```

## 7. Manual E2E: Enroll Face Rồi Verify Qua Edge

Flow này dùng frontend-admin để tạo dữ liệu khuôn mặt thật trong Postgres/pgvector. Sau đó edge-client gửi face crop về backend để verify.

Trước khi chạy, đảm bảo `.env` local dùng đúng model contract:

```env
EMBEDDING_PROVIDER=deepface
MODEL_NAME=Facenet512
MODEL_VERSION=2026.05-deepface-facenet512
EMBEDDING_DIMENSIONS=512
DEEPFACE_DETECTOR_BACKEND=opencv
DEEPFACE_ALIGN=true
DEEPFACE_ENFORCE_DETECTION=false
EMBEDDING_ALLOW_HASH_FALLBACK=false
MATCH_THRESHOLD=0.55
```

Chạy stack server:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

Chạy migration:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend alembic upgrade head
```

Mở admin UI:

```text
http://localhost/admin/
```

Production lưu ý: browser chỉ cho camera trên HTTPS hoặc `localhost`. Vì vậy enrollment bằng camera trong production phải chạy qua HTTPS.

Flow test:

1. Login vào admin UI bằng user/password trong `.env`.
2. Tạo employee hoặc chọn employee đã có.
3. Vào khu enrollment.
4. Chụp 3-5 mẫu mặt live.
5. Save enrollment để backend tạo embedding/vector.
6. Dùng edge-client hoặc API recognition để verify.

Kiểm tra vector đã ghi:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec db psql -U postgres -d face_detector -c "select employee_code, created_at from face_embeddings;"
```

Test API recognition bằng ảnh file:

```powershell
curl.exe -F "device_name=local-manual-test" -F "file=@.\path\to\face.jpg" http://localhost/api/vision/recognize
```

Trên Windows, chạy edge-client bằng venv local để verify ở kiosk:

```powershell
cd edge-client
.\.venv\Scripts\Activate.ps1
$env:API_BASE_URL = "http://localhost"
$env:EDGE_BACKEND_ENABLED = "true"
$env:EDGE_UI_MODE = "web"
python main.py
```

Mở kiosk UI:

```text
http://localhost:8080
```
