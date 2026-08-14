# Ranh Giới Ba Repository

Hệ thống được tách thành ba source of truth độc lập để một lỗi hoặc credential bị lộ ở
application CI không tự động trở thành quyền quản trị AWS hay quyền sửa production.

| Repository | Source of truth | Quyền không được cấp |
| --- | --- | --- |
| `face-detector-app` | source code, test, OCI image, SBOM và attestation | AWS IAM role, Terraform apply, sửa GitOps state trực tiếp |
| `face-detector-gitops` | Helm values, Argo CD Application/AppProject, image digest theo môi trường | build image, AWS IAM role |
| `face-detector-infra` | Terraform, AWS OIDC/IAM, EKS platform và sandbox lifecycle | thay đổi application source |

## Luồng Release

```text
app PR
-> CI / gateway
-> merge master
-> App Release build và ký image
-> push GHCR bằng tag commit SHA
-> resolve image@sha256
-> GitHub App dispatch promote-staging-v1 sang GitOps repo
-> GitOps repo mở promotion PR
-> merge promotion PR
-> Argo CD reconcile staging từ Git
```

Production bắt đầu từ GitHub Release. GitOps workflow phải qua GitHub Environment
`production`, sau đó vẫn mở PR và Argo CD production vẫn giữ manual sync.

## Luồng Sandbox Và Ranh Giới Code Không Tin Cậy

```text
owner gắn deploy-sandbox trên app PR
-> runner A chỉ có contents:read, build Dockerfile của PR
-> runner A upload image archives, không có registry/AWS credential
-> runner B chỉ checkout workflow từ master, load archive nhưng không chạy app code
-> runner B push GHCR và resolve digest
-> app GitHub App dispatch sandbox-apply-v1 sang infra repo
-> infra workflow trên master xác minh lại PR, SHA, label actor và digest
-> infra repo assume AWS role rồi apply/deploy/smoke
-> infra GitHub App gắn sandbox-validated vào app PR
```

Không được gộp runner A và runner B. Dockerfile trong PR là code không tin cậy; nó không
được chạy trong job có package-write token, GitHub App private key hoặc AWS OIDC token.

## GitHub Apps Cần Có

App repo chỉ giữ private key của các App dùng để gửi event:

- `GITOPS_DISPATCH_APP_ID`, `GITOPS_DISPATCH_APP_PRIVATE_KEY`: cài trên
  `face-detector-gitops`, dùng để gọi `repository_dispatch`.
- `INFRA_DISPATCH_APP_ID`, `INFRA_DISPATCH_APP_PRIVATE_KEY`: cài trên
  `face-detector-infra`, dùng để gọi `repository_dispatch`.

Không dùng PAT cá nhân. Hai App phải tách nhau để key gửi GitOps không có quyền trên infra.
Do GitHub yêu cầu quyền `Contents: write` cho Repository Dispatch, branch ruleset ở repo đích
vẫn phải chặn direct push vào `master`.

Variables của app repo:

```text
GITOPS_REPOSITORY=chiendz11/face-detector-gitops
GITOPS_REPOSITORY_NAME=face-detector-gitops
INFRA_REPOSITORY=chiendz11/face-detector-infra
INFRA_REPOSITORY_NAME=face-detector-infra
INFRA_AUTOMATION_BOT_LOGIN=<app-control-slug>[bot]
```

`INFRA_AUTOMATION_BOT_LOGIN` là exact login của GitHub App mà infra dùng để gắn
`sandbox-validated`. Sandbox policy fail-closed nếu actor không khớp biến này.

## Trạng Thái Cutover

Các repository mới được public để review nhưng GitHub Actions phải giữ ở trạng thái disabled.
Chưa copy secrets, chưa bật ruleset automation và chưa deploy cho tới khi ba migration PR được
review/merge theo thứ tự GitOps, infra, app và checklist cutover đã được xác nhận.
