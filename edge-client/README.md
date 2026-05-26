# Edge Client Kiosk

`edge-client` là ứng dụng kiosk chạy gần camera ở cửa ra vào. Nhiệm vụ chính của nó là đọc camera local, detect/crop mặt, gửi ảnh mặt đã crop về backend, rồi hiển thị kết quả xác minh cho người dùng hoặc bảo vệ.

## Cấu Trúc Thư Mục

```text
edge-client/
  main.py                  # launcher tương thích để chạy local
  pyproject.toml           # metadata package và CLI entrypoint
  src/edge_client/
    app.py                 # điều phối runtime chính
    config.py              # đọc cấu hình từ environment
    clients/backend.py     # client gọi backend API
    hardware/camera.py     # adapter camera
    hardware/door.py       # placeholder cho cửa/relay
    vision/face_detector.py
    ui/web_kiosk.py        # kiosk web local bằng FastAPI
    ui/opencv_display.py   # UI OpenCV cũ
    ui/static/kiosk.css    # CSS cho web kiosk
  tests/
```

## Cách Chạy Local

Chạy bằng launcher tương thích:

```powershell
.\.venv\Scripts\python.exe main.py
```

Cài package ở chế độ editable rồi chạy module:

```powershell
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m edge_client
```

Docker image sẽ cài package và chạy console script `edge-client`.

## Cấu Hình Quan Trọng

Edge không hardcode URL backend trong code. URL backend được truyền qua biến:

```text
API_BASE_URL
```

Ví dụ:

```powershell
$env:API_BASE_URL = "http://localhost"
$env:EDGE_UI_MODE = "web"
$env:EDGE_KIOSK_PORT = "8080"
python main.py
```

Trong production, `API_BASE_URL` nên là stable domain:

```text
https://face.example.com
```

Với staging:

```text
https://staging.face.example.com
```

Với sandbox test:

```text
https://sandbox-pr-123.face.example.com
```

Không nên build lại image edge-client chỉ để đổi backend URL. Hãy đổi runtime config bằng systemd environment file, MDM, Ansible, SSM, hoặc cơ chế quản lý config tương đương.
