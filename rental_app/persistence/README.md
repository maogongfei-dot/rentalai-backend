# Phase 5 Round3 — JSON persistence

## Users (`user_store` / `user_repository` / `user_auth_service`)

- **File**: `data/storage/persistence_users.json` (override: `RENTALAI_PERSISTENCE_USERS_JSON`).
- **`/auth/register`**, **`/auth/login`**, **`/auth/me`** use **`user_auth_service`**: register writes a row; login verifies `password_hash` + `password_hash_algorithm` (`sha256_v1` today; extend in `password_hashing.py`).
- **Duplicate email**: rejected in `register_user` via `UserRepository.get_by_email` (normalized lowercase).

## Analysis history (server-side JSON)

- Optional next step: `history_store` / `HistoryRepository` beside user rows; not wired to web UI yet.
