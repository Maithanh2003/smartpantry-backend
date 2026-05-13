# Test nhanh: cache pantry, upload ảnh, list/detail

Giả định API chạy tại `http://127.0.0.1:8000` và bạn dùng **Docker Compose** (`DATABASE_URL` / `REDIS_URL` / MinIO như trong `.env`).

## Vì sao không thấy log CACHE HIT / MISS?

1. **Mức logger + propagate:** các dòng cache dùng `logger.info(...)`. Chỉ `setLevel(INFO)` cho `app` **không đủ** nếu log vẫn propagate lên **root** (thường WARNING) — bản ghi INFO bị loại trước khi in. `main.py` gắn `StreamHandler` cho `logging.getLogger("app")`, đặt **`propagate=False`**, để `app.services.*` chỉ đi qua handler của `app`. Biến `LOG_LEVEL` (mặc định `INFO`) điều chỉnh mức trên handler đó.
2. **Tắt cache:** `PANTRY_LIST_CACHE_ENABLED=false` thì không đi vào nhánh HIT/MISS/SET/INVALIDATE (không có log cache).
3. **Chưa gọi đúng API:** chỉ **`GET /api/v1/pantry-items`** mới dùng list cache; `GET /pantry-items/{id}` không ghi cache.

Sau khi sửa code/logging, restart container `app`: `docker compose up -d --build app`.

## Biến môi trường (theo `.env` hiện tại)

| Biến | Ý nghĩa khi test |
|------|------------------|
| `DATABASE_URL` | `...@db:5432...` khi app trong container; host chạy uvicorn thì `localhost:5432`. |
| `REDIS_URL` | `redis://redis:6379/0` (Docker) — cache list pantry. |
| `PANTRY_LIST_CACHE_ENABLED` | `true` để thấy log HIT/MISS trong `docker compose logs -f app`. |
| `OBJECT_STORAGE_ENDPOINT_URL` | `http://minio:9000` trong container. |
| `OBJECT_STORAGE_PUBLIC_BASE_URL` | **Để trống** nếu chưa có CDN public; khi set (vd. `https://cdn.example.com`), response có thêm `image_url` = base + `image_path`. |

Sau khi sửa `.env`, restart app: `docker compose up -d --build` hoặc restart service `app`.

---

## 1) Cache list pantry (MISS → HIT → INVALIDATE)

```powershell
# Theo dõi log cache
docker compose logs -f app
```

1. **Đăng nhập** lấy `access_token` (xem mục 2 dưới).
2. **GET list lần 1** (cùng query để tái sử dụng cache):

   `GET http://127.0.0.1:8000/api/v1/pantry-items?page=1&page_size=20&q=test`

   Header: `Authorization: Bearer <token>`

   Kỳ vọng log: **`CACHE MISS`** rồi **`CACHE SET`**.

3. **GET list lần 2** (y hệt URL + query).

   Kỳ vọng: **`CACHE HIT`**.

4. **KEY Redis** (tuỳ chọn):

   ```powershell
   docker compose exec redis redis-cli KEYS "smartpantry:pantry-list:u:*"
   ```

5. **Invalidate**: gọi `POST /api/v1/pantry-items`, `PATCH ...`, `DELETE ...`, hoặc `POST .../restore` — sau đó list lại cùng query.

   Kỳ vọng log: **`CACHE INVALIDATE`**, lần list tiếp theo lại **MISS** rồi **SET**.

---

## 2) Token (login)

```powershell
$body = '{"email":"you@example.com","password":"YourPassword1"}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/auth/login" -ContentType "application/json" -Body $body
```

Lấy `data.tokens.access_token`. Kiểm tra audit: `docker compose exec db psql -U user -d smartpantry -c "SELECT action, entity_type, entity_id FROM audit_logs ORDER BY id DESC LIMIT 5;"` — thấy `LOGIN_SUCCESS` hoặc `LOGIN_FAILED`.

---

## 3) Upload → POST item có `image_path` → list/detail

**Upload** (đường dẫn file ảnh thật trên máy bạn):

```powershell
$token = "<access_token>"
curl.exe -sS -X POST "http://127.0.0.1:8000/api/v1/pantry-items/upload-image" `
  -H "Authorization: Bearer $token" `
  -F "file=@C:\path\to\photo.jpg;type=image/jpeg"
```

Trong JSON: `data.path` (vd. `pantry-items/1/xxx.jpg`). Nếu có `OBJECT_STORAGE_PUBLIC_BASE_URL`, sẽ có thêm `data.image_url`.

**Tạo item** (thay `image_path` bằng `path` vừa trả về):

```powershell
$token = "<access_token>"
$path = "pantry-items/1/....jpg"
$json = @{
  name = "Sữa"
  quantity_value = "1"
  quantity_unit = "l"
  image_path = $path
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/pantry-items" -Headers @{ Authorization = "Bearer $token" } -ContentType "application/json; charset=utf-8" -Body $json
```

**List**: `GET /api/v1/pantry-items?page=1&page_size=20` — mỗi phần tử có `image_path` và `image_url` (nếu base URL đã cấu hình).

**Detail**: `GET /api/v1/pantry-items/{id}` — cùng shape.

---

## 4) Soft delete + restore

```powershell
# DELETE (soft)
curl.exe -sS -X DELETE "http://127.0.0.1:8000/api/v1/pantry-items/123" -H "Authorization: Bearer $token"

# Detail → 404 ITEM_NOT_FOUND
curl.exe -sS "http://127.0.0.1:8000/api/v1/pantry-items/123" -H "Authorization: Bearer $token"

# Restore
curl.exe -sS -X POST "http://127.0.0.1:8000/api/v1/pantry-items/123/restore" -H "Authorization: Bearer $token"
```

Restore khi item chưa xóa: **`409`** `ITEM_NOT_DELETED`.
