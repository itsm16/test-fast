# Errors & Fixes

## Why errors appear even though IDE suggests imports

When you write `from auth import auth_service` inside `src/modules/auth/auth_controller.py`, your IDE may show autocomplete suggestions because it sees the `auth/` folder as a package. But **this does not work at runtime** — Python's import system does not look at local directories by folder name alone. It uses `sys.path`, and only `src` (the top-level package under the project root) is discoverable.

## Fixes

### 1. `src/modules/auth/auth_model.py` — Missing BaseModel import
- **Error:** `BaseModel` is used but never imported → `NameError: name 'BaseModel' is not defined`
- **Fix:** Added `from pydantic import BaseModel` at the top.

### 2. `src/modules/auth/auth_service.py` — Wrong import path
- **Error:** `from auth import auth_model` → `ModuleNotFoundError: No module named 'auth'`
- **Fix:** Changed to `from src.modules.auth import auth_model`.

### 3. `src/modules/auth/auth_controller.py` — Wrong import paths
- **Error:** `from auth import auth_service` / `from auth import auth_model` → same `ModuleNotFoundError`
- **Fix:** Changed to `from src.modules.auth import auth_service` and `from src.modules.auth import auth_model`.

### 4. `src/modules/auth/auth_route.py` — Import & signature mismatch
- **Error:** Imported `auth_controller` (no such name in module; controller is now a function, not a class), and called `register_user()` with no args while the function expects `body`.
- **Fix:** Import `register_user` directly from `auth_controller`, import `RegisterUserDto` from `auth_model`, and pass the request body via FastAPI.

## Importing within the same module

For files inside `src/modules/auth/`, you **do not** have to start from the project root. You have two valid options:

| Style | Example | Works from project root |
|-------|---------|------------------------|
| Absolute | `from src.modules.auth import auth_model` | ✅ Always |
| Relative | `from . import auth_model` | ✅ Always (within package) |
| ❌ Wrong | `from auth import auth_model` | ❌ Never |

**Rule of thumb:** If you're inside the `auth/` package, use either `from . import xxx` (relative) or `from src.modules.auth import xxx` (absolute). Never use bare `from auth import ...`.

## Verification
All endpoints working:
- `GET /health` → `200`
- `GET /api/auth/test` → `200`
- `POST /api/auth/register` → `200`
