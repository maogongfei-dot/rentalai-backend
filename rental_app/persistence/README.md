# Phase 5 Round3 — JSON persistence

## Users (`user_store` / `user_repository` / `user_auth_service`)

- **File**: `data/storage/persistence_users.json` (override: `RENTALAI_PERSISTENCE_USERS_JSON`).
- **`/auth/register`**, **`/auth/login`**, **`/auth/me`** use **`user_auth_service`**: register writes a row; login verifies `password_hash` + `password_hash_algorithm` (`sha256_v1` today; extend in `password_hashing.py`).
- **Duplicate email**: rejected in `register_user` via `UserRepository.get_by_email` (normalized lowercase).

## Analysis history (server-side JSON)

- **File**: `data/storage/persistence_analysis_history.json` (override: `RENTALAI_PERSISTENCE_ANALYSIS_HISTORY_JSON`).
- **Write** (Phase 5 Round3 Step3): `analysis_history_writer` appends after successful **`POST /api/ai/query`** (property) and **`POST /api/contract/analysis/text`**, **`/file-path`**, **`/upload`** (contract). Optional JSON/form **`userId`** / **`user_id`**; omitted → **`guest`**.
- **Read API**: not in this step; use `HistoryRepository.list_by_user` from server code or add HTTP later.
