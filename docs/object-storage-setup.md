# Object storage: MinIO (local/VPS) và Cloudflare R2

Backend dùng API S3-compatible (`boto3`). Cùng một code path cho **MinIO** (dev/VPS) và **Cloudflare R2** (prod): chỉ đổi biến môi trường.

## Biến môi trường (tóm tắt)

| Biến | MinIO local (Docker) | MinIO VPS | R2 |
|------|----------------------|-----------|-----|
| `OBJECT_STORAGE_ENDPOINT_URL` | `http://minio:9000` (app trong Docker) hoặc `http://127.0.0.1:9000` (uvicorn trên máy host) | `https://s3.example.com` (reverse proxy TLS) hoặc `http://IP:9000` (chỉ lab) | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` |
| `OBJECT_STORAGE_REGION` | `auto` hoặc `us-east-1` | tùy cấu hình | `auto` |
| `OBJECT_STORAGE_BUCKET` | `smartpantry-assets` (trùng với bucket `minio-init` tạo) | tên bucket bạn tạo | tên bucket R2 |
| `OBJECT_STORAGE_ACCESS_KEY_ID` / `OBJECT_STORAGE_SECRET_ACCESS_KEY` | `minioadmin` / `minioadmin` (mặc định compose) | user MinIO hoặc access key | R2 S3 API token (Access Key ID + Secret) |
| `OBJECT_STORAGE_PUBLIC_BASE_URL` | (tuỳ chọn) URL public nếu bạn bật CDN/proxy | tuỳ chọn | URL public R2 (custom domain / `*.r2.dev`) nếu cần |

**Lưu ý:** App trong container không thể dùng `http://127.0.0.1:9000` để gọi MinIO trên host — phải dùng hostname service Docker `http://minio:9000`.

### `OBJECT_STORAGE_PUBLIC_BASE_URL` — lấy ở đâu?

Hiện **API upload không đọc biến này** (response chỉ có `path` tương đối trên bucket). Bạn chỉ cần điền khi **frontend** (hoặc code sau này) ghép URL công khai để hiển thị ảnh.

| Môi trường | Nguồn giá trị |
|------------|----------------|
| **MinIO local** | Thường **để trống**. Nếu sau này bạn public qua Nginx/Caddy (vd. `https://cdn.ban.com`), điền **base URL đó** (không có `/` cuối). |
| **Cloudflare R2** | Dashboard → **R2** → chọn bucket → **Settings** → **Public access** → bật **R2.dev subdomain** (sẽ có dạng `https://pub-xxxxx.r2.dev`) hoặc gắn **Custom Domain**; dùng đúng URL base đó (scheme + host, không thêm path bucket nếu bạn tự ghép path). |

Ví dụ ghép URL ảnh (ở client): `{OBJECT_STORAGE_PUBLIC_BASE_URL}/{path}` — chỉ đúng nếu R2/MinIO được cấu hình phục vụ object theo path đó.

---

## 1) Local dev — Docker Compose + MinIO

### Bước 1 — Chuẩn bị `.env`

Sao chép `.env.example` → `.env` và chỉnh các dòng object storage cho khớp compose (đã gợi ý sẵn trong `.env.example`):

- `OBJECT_STORAGE_ENDPOINT_URL=http://minio:9000`
- `OBJECT_STORAGE_ACCESS_KEY_ID=minioadmin`
- `OBJECT_STORAGE_SECRET_ACCESS_KEY=minioadmin`
- `OBJECT_STORAGE_BUCKET=smartpantry-assets`

### Bước 2 — Khởi động stack

Từ thư mục `smartpantry-backend`:

```bash
docker compose up -d --build
```

Compose gồm: Postgres, Redis, **MinIO** (API `9000`, console `9001`), job **`minio-init`** (tạo bucket `smartpantry-assets` nếu chưa có), rồi `app`.

Service `app` còn gán mặc định qua `docker-compose.yml` (`OBJECT_STORAGE_ENDPOINT_URL` → `http://minio:9000`, …) nếu biến không có trong file `.env` dùng để interpolate — tránh lỗi boto3 gọi nhầm `*.amazonaws.com` khi quên cấu hình.

- Console MinIO: `http://127.0.0.1:9001` — đăng nhập `minioadmin` / `minioadmin`.
- Kiểm tra object sau upload: bucket `smartpantry-assets` → prefix `pantry-items/<user_id>/`.

### Bước 3 — Nếu chạy API **trên host** (không dùng container `app`)

Đặt endpoint tới MinIO publish ra máy bạn:

- `OBJECT_STORAGE_ENDPOINT_URL=http://127.0.0.1:9000`

(`DATABASE_URL` / `REDIS_URL` khi đó thường trỏ `localhost:5432`, `localhost:6379` thay vì hostname Docker.)

---

## 2) Test flow upload → tạo pantry item

API có prefix `/api/v1`. Cần JWT access (Bearer).

### Đăng ký và đăng nhập

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"you@example.com\",\"password\":\"YourStrongPass1\",\"full_name\":\"You\"}"
```

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"you@example.com\",\"password\":\"YourStrongPass1\"}"
```

Lấy `data.access_token` trong JSON trả về (wrapper `success` / `data`).

### Upload ảnh (multipart)

Chỉ chấp nhận MIME/size theo `.env` (mặc định JPEG/PNG/Webp, tối đa 5MB).

```bash
export TOKEN="<paste_access_token_here>"

curl -sS -X POST "http://127.0.0.1:8000/api/v1/pantry-items/upload-image" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/photo.jpg;type=image/jpeg"
```

Trong `data` sẽ có **`path`** (relative key trên bucket), ví dụ `pantry-items/1/abc....jpg`.

### Tạo pantry item với `image_path`

Dùng đúng chuỗi `path` từ bước upload (không được là URL tuyệt đối):

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/v1/pantry-items" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Milk\",\"quantity_value\":\"1\",\"quantity_unit\":\"l\",\"image_path\":\"pantry-items/1/your-uuid.jpg\"}"
```

(Thay `image_path` bằng giá trị thật từ response upload.)

### Kỳ vọng lỗi thường gặp

- **503** `Object storage upload failed` — sai endpoint/credentials/bucket chưa tồn tại, hoặc app không reach được MinIO/R2.
- **400** mime/size/extension — file không đúng loại hoặc quá lớn.
- **401** — thiếu/sai Bearer token.

---

## 3) VPS / staging — MinIO giống prod nội bộ

Luồng giống local: chạy MinIO (Docker hoặc binary), tạo bucket, tạo user/access key **không** dùng root trong thật.

Gợi ý an toàn:

- Chỉ expose API S3 (`9000`) ra internet qua **reverse proxy TLS** (Caddy / Nginx); console (`9001`) hạn chế VPN/firewall.
- Trong `.env` production: `OBJECT_STORAGE_ENDPOINT_URL=https://...` trỏ tới proxy đó.
- Bucket policy: chỉ user ứng dụng được `s3:PutObject` / `s3:GetObject` trên prefix `pantry-items/*` nếu cần tối thiểu quyền.

Backend không đổi code — chỉ đổi env giống bảng ở đầu tài liệu.

---

## 4) Production — Cloudflare R2

1. Cloudflare Dashboard → **R2** → tạo bucket (ví dụ `smartpantry-assets`).
2. **Manage R2 API Tokens** → tạo token kiểu S3 (Access Key ID + Secret Access Key), quyền đọc/ghi bucket đó.
3. Endpoint S3: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` (Account ID lấy trong trang R2 / Overview).
4. Cập nhật env trên server deploy:

   - `OBJECT_STORAGE_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com`
   - `OBJECT_STORAGE_REGION=auto`
   - `OBJECT_STORAGE_BUCKET=<tên bucket>`
   - `OBJECT_STORAGE_ACCESS_KEY_ID` / `OBJECT_STORAGE_SECRET_ACCESS_KEY` = token vừa tạo

5. (Tuỳ chọn) **Public access** — nếu client cần URL ảnh trực tiếp: cấu hình custom domain hoặc R2 public URL; ghi vào `OBJECT_STORAGE_PUBLIC_BASE_URL` nếu app của bạn dùng field này ở tầng khác (API upload vẫn chỉ trả `path` tương đối).

---

## 5) Kiểm tra nhanh bằng MinIO Client (`mc`) — tùy chọn

Trên máy có `mc`:

```bash
mc alias set local http://127.0.0.1:9000 minioadmin minioadmin
mc ls local/smartpantry-assets/pantry-items/
```

Với R2, dùng endpoint + key R2 khi `mc alias set`.

---

## 6) Xử lý sự cố Docker

**`smartpantry-minio-init`: `connection refused` tới `minio:9000`** — container init chạy ngay khi service MinIO *đã start* nhưng process MinIO có thể chưa mở port S3. Compose dùng vòng lặp `until mc alias set ...` rồi `until mc ready local` để đợi API thật sự sẵn sàng. Nếu bạn vẫn thấy log lỗi từ bản compose cũ: `docker compose up -d minio-init` (hoặc `docker compose up -d` lại) sau khi kéo file `docker-compose.yml` mới.

---

Tóm lại: **local/VPS** dùng MinIO + env endpoint nội bộ; **prod** trỏ endpoint R2 và API token — cùng một flow test: đăng nhập → `upload-image` → `POST /pantry-items` với `image_path` = `path` trả về.
