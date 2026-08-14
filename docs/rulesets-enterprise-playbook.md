# Playbook GitHub Ruleset Cho App Repository

## Mục Tiêu

Ruleset bảo vệ `master` nhưng không require trực tiếp các job theo domain vì backend, frontend,
edge hoặc nginx có thể được skip. Required context ổn định của repo này là:

```text
CI / gateway
Sandbox Policy / evaluate
Repo Security / secret-scan
```

## Rule Cho Master

- Require pull request before merging: bật.
- Required approving reviews: `0` khi chỉ có một maintainer.
- Require code owner review native: tắt trong giai đoạn solo.
- Require status checks: ba context ở trên.
- Require branch up to date: bật nếu merge queue/CI capacity đáp ứng được.
- Restrict direct push và deletion: bật.
- Allow auto-merge: bật sau khi checks pass.
- Bypass: chỉ owner/break-glass identity, mọi lần dùng phải ghi lý do.

`CODEOWNERS` vẫn là metadata cho custom governance, không phải native review gate trong chế độ
solo maintainer.

## Lane-Based CI

Workflow `.github/workflows/ci.yml` phân loại changed paths rồi gọi reusable app CI:

- `backend/**`: backend test/security/image checks;
- `frontend-admin/**`: frontend test/build/audit;
- `edge-client/**`: edge test/image checks;
- `nginx/**`: nginx image checks;
- compose, image catalog và shared workflow/action: chạy broader app verification.

Job `gateway` luôn chạy với `if: always()` và fail nếu classifier hoặc lane bắt buộc fail. Vì vậy
ruleset chỉ cần require `CI / gateway`, không chờ một domain job không được tạo.

## Workflow Và Policy Changes

Các path `.github/workflows/**`, `.github/actions/**`, `policies/**` và `CODEOWNERS` phải chạy
Repo Security cùng governance tests. Khi có ít nhất hai trusted humans, có thể thêm ruleset riêng
yêu cầu một approval cho các path control-plane này.

## Checklist Cutover

1. Merge migration PR sau khi review.
2. Bật Secret Scanning và Push Protection.
3. Tạo ruleset cho `master` với đúng context name.
4. Không copy AWS secrets/roles vào app repo.
5. Cấu hình GitHub Apps cross-repo theo `docs/repository-boundaries.md`.
6. Bật Actions và thử lần lượt docs-only PR, single-domain PR, shared-app PR và sandbox PR.
