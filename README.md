# Face Detector App

Repository này là source-of-truth cho application code của Face Detector.

## Phạm vi sở hữu

- `backend/`: FastAPI, worker, migration và face-recognition services.
- `frontend-admin/`: giao diện quản trị, enrollment và audit logs.
- `edge-client/`: kiosk chạy tại edge device.
- `nginx/`: public application boundary.
- `docker-compose*.yml`: local development, CI smoke và observability local.

Repository này build, test và publish OCI images lên GHCR. Nó không chứa Terraform,
không quản lý Kubernetes desired state và không được cấp AWS deployment role.

## Luồng phát hành

```text
Pull request -> CI / gateway
merge master -> App Release -> GHCR image@sha256
App Release -> repository_dispatch -> face-detector-gitops
GitHub Release -> production promotion request -> face-detector-gitops
```

Sandbox được yêu cầu bằng label trong PR. Workflow chỉ gửi request sang
`face-detector-infra`; toàn bộ AWS apply/destroy chạy từ workflow tin cậy của infra repo.

Xem [ranh giới repository](docs/repository-boundaries.md) trước khi cấu hình cutover.
