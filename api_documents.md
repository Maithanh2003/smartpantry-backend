# SmartPantry Backend API Documents

Tai lieu nay tong hop cac API da co trong he thong de frontend theo doi.

Base URL:
- local: `http://127.0.0.1:8000`
- production: `https://mysmartpantry.duckdns.org`

API prefix: `/api/v1`

## 1) Health

### GET `/health`
- Auth: none
- Response:
```json
{
  "status": "ok|degraded",
  "db": "ok|error",
  "redis": "ok|error"
}
```

## 2) Auth APIs

### POST `/api/v1/auth/register`
- Auth: none
- Request:
```json
{
  "email": "user@example.com",
  "password": "stringst",
  "full_name": "String User"
}
```
- Success `201`:
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "email": "user@example.com",
      "full_name": "String User"
    },
    "tokens": {
      "token_type": "bearer",
      "access_token": "jwt",
      "refresh_token": "jwt"
    }
  },
  "meta": {
    "request_id": "uuid-string",
    "timestamp": "ISO_DATETIME"
  }
}
```
- Error:
  - `VALIDATION_ERROR` (email existed)

### POST `/api/v1/auth/login`
- Auth: none
- Request:
```json
{
  "email": "user@example.com",
  "password": "stringst"
}
```
- Success `200`: same token payload format as register.
- Error:
  - `PERMISSION_DENIED` (invalid credentials)

### POST `/api/v1/auth/refresh`
- Auth: none
- Request:
```json
{
  "refresh_token": "jwt"
}
```
- Success `200`:
```json
{
  "success": true,
  "data": {
    "token_type": "bearer",
    "access_token": "jwt",
    "refresh_token": "jwt"
  },
  "meta": {
    "request_id": "uuid-string",
    "timestamp": "ISO_DATETIME"
  }
}
```
- Error:
  - `INVALID_TOKEN`
  - `PERMISSION_DENIED`

### GET `/api/v1/auth/me`
- Auth: required (Bearer access token)
- Success `200`:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "String User",
    "status": "active"
  },
  "meta": {
    "request_id": "uuid-string",
    "timestamp": "ISO_DATETIME"
  }
}
```

### GET `/api/v1/auth/protected-test`
- Auth: required (Bearer access token)
- Success `200`:
```json
{
  "success": true,
  "data": {
    "message": "JWT access token is valid",
    "user_id": 1
  },
  "meta": {
    "request_id": "uuid-string",
    "timestamp": "ISO_DATETIME"
  }
}
```

## 3) Pantry APIs (skeleton)

### POST `/api/v1/pantry-items`
- Auth: required
- Request:
```json
{
  "name": "Ca chua",
  "category_id": 1,
  "quantity_value": 2.5,
  "quantity_unit": "kg",
  "source": "manual",
  "notes": "Mua o cho",
  "expiry_date": "2026-05-20",
  "image_path": "pantry-items/<user_id>/<generated-file>.jpg"
}
```
- Success `201`: `success/data/meta`
- Error:
  - `VALIDATION_ERROR`

### POST `/api/v1/pantry-items/upload-image`
- Auth: required
- Content-Type: `multipart/form-data`
- Field: `file` (image)
- Validate:
  - MIME: `image/jpeg|image/png|image/webp`
  - Max size: `PANTRY_IMAGE_MAX_SIZE_BYTES` (default `5MB`)
- Flow:
  1) Flutter upload multipart
  2) Backend validate mime/size
  3) Generate UUID filename
  4) Upload to R2/S3
  5) Return relative object path (`path`) de luu vao `pantry_items.image_path`; neu `OBJECT_STORAGE_PUBLIC_BASE_URL` duoc set thi them `image_url` (base + path).
- Success `201`:
```json
{
  "success": true,
  "data": {
    "path": "pantry-items/1/4f54f6f2a91b4d469840ed405f9e4f76.jpg",
    "image_url": "https://cdn.example.com/pantry-items/1/4f54f6f2a91b4d469840ed405f9e4f76.jpg",
    "mime_type": "image/jpeg",
    "size_bytes": 102400
  },
  "meta": {
    "request_id": "uuid-string",
    "timestamp": "ISO_DATETIME"
  }
}
```
- Error:
  - `VALIDATION_ERROR` (mime/size/empty file/invalid extension)
  - `INTERNAL_ERROR` (R2/S3 upload failed)

### GET `/api/v1/pantry-items/{item_id}`
- Auth: required
- Success `200`: one item (same shape as list element); only the owner can read it.
- Error:
  - `ITEM_NOT_FOUND` (wrong id, other user’s item, or soft-deleted)

### GET `/api/v1/pantry-items?page=1&page_size=20&category_id=1&expiry_status=warning&source=manual&q=ca&sort_by=created_at&sort_order=desc`
- Auth: required
- Query params:
  - `page` (1..10000), `page_size` (1..100): pagination
  - `category_id`: filter theo category
  - `expiry_status`: `fresh|warning|expired`
  - `source`: `manual|ocr_confirmed|ai_assisted`
  - `q`: search theo `name` va `notes` (ILIKE)
  - `sort_by`: `created_at|updated_at|expiry_date|name`
  - `sort_order`: `asc|desc`
- Success `200`:
```json
{
  "success": true,
  "data": [
    {
      "id": 1001,
      "user_id": 1,
      "category_id": 1,
      "name": "Ca chua",
      "quantity_value": "2.50",
      "quantity_unit": "kg",
      "source": "manual",
      "notes": "Mua o cho",
      "expiry_date": "2026-05-20",
      "expiry_status": "fresh",
      "image_path": "pantry-items/<user_id>/<generated-file>.jpg",
      "image_url": "https://cdn.example.com/pantry-items/<user_id>/<generated-file>.jpg",
      "created_at": "ISO_DATETIME",
      "updated_at": "ISO_DATETIME"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 1,
    "filters": {
      "category_id": 1,
      "expiry_status": "warning",
      "source": "manual",
      "q": "ca"
    },
    "sort": {
      "by": "created_at",
      "order": "desc"
    },
    "request_id": "uuid-string",
    "timestamp": "ISO_DATETIME"
  }
}
```
- Error:
  - `VALIDATION_ERROR` (invalid filter/sort values)
  - Cache backend unavailable: endpoint still works (fallback to DB query)

### Redis cache cho Pantry list
- Scope: chi ap dung cho `GET /api/v1/pantry-items` (list).
- Key: `smartpantry:pantry-list:u:{user_id}:q:{sha256(filters+pagination+sort+search)}`
- TTL mac dinh: `120s` (configurable).
- Log `CACHE HIT` / `CACHE MISS` / `CACHE SET` / `CACHE INVALIDATE`: logger `app.services.pantry_cache_service`, muc **INFO**. `main.py` gan handler rieng cho `logging.getLogger("app")` va `propagate=False` (neu chi set level ma van propagate len `root` thi root WARNING se nuot mat INFO).
- Cache invalidation:
  - `POST /api/v1/pantry-items` -> xoa toan bo list cache cua user.
  - `PATCH /api/v1/pantry-items/{item_id}` -> xoa toan bo list cache cua user.
  - `DELETE /api/v1/pantry-items/{item_id}` -> xoa toan bo list cache cua user.
  - `POST /api/v1/pantry-items/{item_id}/restore` -> xoa toan bo list cache cua user.
- Ownership-safe:
  - key co `user_id`, repository query van bat buoc `user_id` + `deleted_at IS NULL`.

### PATCH `/api/v1/pantry-items/{item_id}`
- Auth: required
- Request: partial fields from create payload.
- Success `200`: updated item.
- Error:
  - `ITEM_NOT_FOUND`
  - `VALIDATION_ERROR`

### POST `/api/v1/pantry-items/{item_id}/restore`
- Auth: required
- Soft-delete: set `deleted_at` ve `NULL` cho item thuoc user (neu dang bi xoa mem).
- Success `200`: item sau restore (cung shape list/detail).
- Error:
  - `ITEM_NOT_FOUND` (sai id / user khac / khong ton tai)
  - `ITEM_NOT_DELETED` (`409`) — item chua bi soft delete

### DELETE `/api/v1/pantry-items/{item_id}`
- Auth: required
- Success `200`:
```json
{
  "success": true,
  "data": {
    "deleted": true,
    "item_id": 1001
  },
  "meta": {
    "request_id": "uuid-string",
    "timestamp": "ISO_DATETIME"
  }
}
```
- Error:
  - `ITEM_NOT_FOUND`

## Error code catalog (implemented/used)
- `INVALID_TOKEN`
- `PERMISSION_DENIED`
- `VALIDATION_ERROR`
- `ITEM_NOT_FOUND`
- `ITEM_NOT_DELETED` (restore khi item chua deleted)
- `INTERNAL_ERROR`
- `DATABASE_MIGRATION_REQUIRED` (register when DB schema is behind code, e.g. `users.id` UUID vs integer)

### Validation error shape (request body / query)
When request JSON fails Pydantic validation, response is `400` with:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "image_path must be relative object path",
    "fields": {
      "image_path": "image_path must be relative object path"
    }
  },
  "meta": { "request_id": "...", "timestamp": "..." }
}
```
`message` is the first issue (human-readable for Flutter). `fields` maps dotted field paths to messages when multiple errors exist.

## Audit logs (DB table `audit_logs`)
- Ghi lai cac su kien quan trong (IP + User-Agent khi co).
- `action`: `CREATE`, `UPDATE`, `DELETE` (pantry item), `LOGIN_SUCCESS`, `LOGIN_FAILED` (auth).
- `entity_type` / `entity_id`: vi du `pantry_item` + id, hoac `user` + user id, hoac `auth` + `-` cho login failed.
- `before_json` / `after_json`: snapshot JSON (pantry); login failed: `after_json.attempted_email`.

## 4) Pantry Categories APIs (full CRUD)

All endpoints below require Bearer access token.

### GET `/api/v1/pantry-categories?page=1&page_size=20`
- Success `200`: list categories + pagination meta.

### GET `/api/v1/pantry-categories/{category_id}`
- Success `200`: one category.
- Error:
  - `ITEM_NOT_FOUND`

### POST `/api/v1/pantry-categories`
- Request:
```json
{
  "code": "snack",
  "name": "Snack"
}
```
- Success `201`: created category.
- Error:
  - `VALIDATION_ERROR` (duplicate code)

### PATCH `/api/v1/pantry-categories/{category_id}`
- Request (partial):
```json
{
  "name": "Healthy Snack"
}
```
- Success `200`: updated category.
- Error:
  - `ITEM_NOT_FOUND`
  - `VALIDATION_ERROR`

### DELETE `/api/v1/pantry-categories/{category_id}`
- Success `200`:
```json
{
  "success": true,
  "data": {
    "deleted": true,
    "category_id": 1
  },
  "meta": {
    "request_id": "uuid-string",
    "timestamp": "ISO_DATETIME"
  }
}
```
- Error:
  - `ITEM_NOT_FOUND`

## Auth header standard
- Header: `Authorization: Bearer <access_token>`
- Endpoints requiring auth:
  - `/api/v1/auth/me`
  - `/api/v1/auth/protected-test`
  - `/api/v1/pantry-items` (all methods)
  - `/api/v1/pantry-categories` (all methods)
