# FastAPI Auth API — Learning Notes

## Setup

```bash
uvicorn main:app --reload
```

## Routes (Path Operations)

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")          # GET /
@app.post("/items")    # POST /items
@app.put("/items/{id}") # PUT /items/123
@app.delete("/items/{id}")
```

### Path Parameters

```python
@app.get("/users/{user_id}")
def get_user(user_id: int):  # auto-validated as int
    return {"user_id": user_id}
```

### Query Parameters

```python
@app.get("/items")
def list_items(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}
```

## Request Body (Pydantic Models)

```python
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: str
    password: str
    username: str | None = None

@app.post("/signup")
def signup(body: UserCreate):
    return {"email": body.email}
```

## Response Models

```python
from pydantic import BaseModel

class UserOut(BaseModel):
    id: int
    email: str

@app.post("/users", response_model=UserOut)
def create_user(body: UserCreate) -> UserOut:
    ...
```

Use `response_model` for automatic filtering (password won't leak).

## Parameter Breakdown — Why Each Is Needed

| Concept | What it does | Why needed |
|---|---|---|
| `Path("/{id}")` | Extracts value from URL path | Identifies **which specific resource** (e.g. which user) |
| `Query()` | Extracts `?key=value` from URL | **Filters, pagination, sorting** without changing the endpoint path |
| `Body()` / Pydantic model | Parses JSON request body | **Sends structured data** (e.g. signup form) that can't fit in URL |
| `Depends()` | Injects a reusable callable result | **Shared logic** like auth checks, DB sessions — no boilerplate per route |
| `Header()` | Extracts HTTP headers | Read tokens, custom headers like `X-API-Key` |
| `Cookie()` | Extracts cookies | Session IDs, remember-me tokens |
| `Form()` | Parses form data (not JSON) | Login forms, file upload metadata |
| `File()` | Parses uploaded files | Profile pictures, CSV imports |
| `status_code` | Sets default HTTP status | Signals success/failure semantics (201 created vs 200 ok) |
| `response_model` | Filters output fields | Prevents leaking sensitive fields (passwords, secrets) |
| `response_model_exclude_unset` | Omits unset fields | Cleaner responses with sensible defaults |
| `tags` | Groups routes in docs | Organises OpenAPI/Swagger UI by feature |

## Dependencies (DI for Auth)

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)  # your JWT decode logic
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

@app.get("/me")
def read_me(user: dict = Depends(get_current_user)):
    return user
```

## Middleware

Runs on every request before/after the route handler.

```python
@app.middleware("http")
async def log_requests(request, call_next):
    # before
    response = await call_next(request)
    # after
    response.headers["X-Process-Time"] = ...
    return response
```

### CORS Middleware

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Other Common Middleware

- **TrustedHostMiddleware** — restricts allowed Host headers (prevents host header attacks)
- **GZipMiddleware** — compresses responses
- **HTTPSRedirectMiddleware** — redirects HTTP → HTTPS

## Auth Flow (JWT)

```
POST /signup   → create user, hash password (bcrypt)
POST /login    → verify password → return JWT access token
GET  /me       → protected route, requires valid JWT
```

### Key packages

- `python-jose` — JWT encode/decode
- `passlib[bcrypt]` — password hashing
- `python-multipart` — required for OAuth2 form data

## Structure for Auth API

```
app/
├── main.py
├── config.py          # settings, SECRET_KEY, ALGORITHM
├── database.py        # DB connection
├── models.py          # SQLAlchemy models
├── schemas.py         # Pydantic schemas
├── auth.py            # JWT helpers, password hashing
├── dependencies.py    # Depends functions
└── routers/
    ├── auth.py        # signup, login
    └── users.py       # /me, user CRUD
```

## Config (pydantic-settings)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = "sqlite:///./app.db"

    class Config:
        env_file = ".env"

settings = Settings()
```

## Password Hashing

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

## JWT Helpers

```python
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
```

## Error Handling

```python
from fastapi import HTTPException, status

raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid credentials",
    headers={"WWW-Authenticate": "Bearer"},
)
```

## SQLAlchemy ORM Setup

### Install

```bash
pip install sqlalchemy
# for async: pip install sqlalchemy[asyncio] aiosqlite
```

### database.py — Engine & Session

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///./app.db"  # or postgresql://user:pass@host/db

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})  # SQLite only
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass
```

- **`create_engine`** — creates a connection pool to the database. Doesn't connect immediately; connects lazily on first query.
- **`sessionmaker`** — a factory that creates `Session` objects. Instead of opening a new connection each time, it borrows one from the engine's pool — no reconnect overhead.
- **`DeclarativeBase`** — the base class for all ORM models. Every table class inherits from it so SQLAlchemy can track and sync them.
- **`DATABASE_URL`** — tells the engine which database to use (SQLite, Postgres, MySQL, etc.).
- **`engine`** — the core interface to the DB. Handles connection pooling, SQL dialect, and execution.
- **`SessionLocal`** — the actual session factory you call to get a DB session (e.g., `db = SessionLocal()`). `autocommit=False` means you must explicitly `commit()`; `autoflush=False` prevents automatic flush before queries.
- **`Base`** — your project's declarative base. All models (`class User(Base)`) register themselves on it, which Alembic uses to detect changes.

### models.py — Table Definitions

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from database import Base
from datetime import datetime, timezone

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
```

### Dependency — Get DB Session

```python
from database import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Usage in routes:
@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    return db.query(User).filter(User.id == user_id).first()
```

### Common CRUD Operations

```python
# Create
user = User(email="a@b.com", hashed_password="...")
db.add(user)
db.commit()
db.refresh(user)  # populate auto-generated fields like id

# Read (all / one)
users = db.query(User).all()
user = db.query(User).filter(User.email == email).first()

# Update
user.username = "new"
db.commit()
db.refresh(user)

# Delete
db.delete(user)
db.commit()
```

## Migrations with Alembic

### Install & Init

```bash
pip install alembic
alembic init alembic
```

### alembic.ini — Set DB URL

```ini
sqlalchemy.url = sqlite:///./app.db
```

### alembic/env.py — Point to your models

```python
from database import Base
import models        # noqa: ensure models are loaded

target_metadata = Base.metadata
```

### Create & Apply Migrations

```bash
alembic revision --autogenerate -m "create users table"
alembic upgrade head
```

### Useful Commands

| Command | What it does |
|---|---|
| `alembic init alembic` | Scaffolds migration directory |
| `alembic revision --autogenerate -m "msg"` | Generates migration from model changes |
| `alembic upgrade head` | Applies all pending migrations |
| `alembic downgrade -1` | Reverts last migration |
| `alembic history` | Shows migration history |
| `alembic current` | Shows current migration state |

### Manual Revision (when autogenerate can't detect changes)

```bash
alembic revision -m "manual change"
# then edit the generated file's upgrade() / downgrade() functions
```

## Async SQLAlchemy (optional)

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine("sqlite+aiosqlite:///./app.db")
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Routes must be async:
@app.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()
```

## Environment Variables (.env)

```
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///./app.db
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Common Pitfalls

- **Not calling `db.commit()`** — changes are lost
- **Forgetting `refresh()`** — returned object won't have auto-generated fields (id, timestamps)
- **Using `response_model` without excluding password** — always define a separate `UserOut` schema
- **Hardcoding SECRET_KEY** — use environment variables / pydantic-settings
- **SQLite `check_same_thread`** — must be `False` when FastAPI uses multiple threads
- **Alembic autogenerate misses changes** — happens with constraint/complex changes; write manual revisions

## Project Layout — Why `src/`

```
fastapi-git/
├── main.py
├── src/
│   ├── common/
│   └── modules/
```

Python's official packaging guide recommends the **src layout** (`src/` directory at project root). Benefits:
- **Clear boundary** between project source code and config files (main.py, requirements.txt, etc.)
- **Prevents accidental imports** of local packages without installation — catches import errors early
- **Standard convention** — tools like `setuptools`, `pip`, and `tox` expect this layout

The alternative is a flat layout (source files directly at root), but the extra `__pycache__` from the `src/` directory is negligible. Stick with `src/`.

## Full auth route example

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas import UserCreate, UserOut, Token
from models import User
from auth import hash_password, verify_password, create_access_token
from dependencies import get_db, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(body: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=body.email, hashed_password=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login(body: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user
```

## Sync vs Async — For JavaScript/Node.js Developers

### The Core Difference

| JavaScript (Node.js) | Python (FastAPI) |
|---|---|
| Everything is async by default (event loop is the only game in town) | Sync is the default; async is opt-in |
| `async function` + `await` | Same syntax: `async def` + `await` |
| One runtime thread, event loop interleaves everything | Sync code blocks **the whole worker thread** until done |
| There is no "sync Express" vs "async Express" — Express is always async | FastAPI has **two modes**: sync `def` and async `async def` — both coexist |

### The Rule in FastAPI

```python
# SYNC — runs in a threadpool, won't block the event loop
@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()  # blocking I/O, but FastAPI offloads it
    return users

# ASYNC — runs directly on the event loop, must await everything
@app.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))  # must await
    return result.scalars().all()
```

**Key insight**: FastAPI automatically detects the difference. If you write `def`, it runs the function in a **thread pool** so it doesn't block the main event loop. If you write `async def`, it runs directly on the event loop — and you **must** `await` all I/O.

### What This Means for You (JS dev)

**1. You can mix sync and async routes freely** — FastAPI handles the dispatching. Unlike Node.js where mixing sync `fs.readFileSync` in an async handler blocks everything, Python's threadpool lets sync routes coexist safely.

**2. SQLAlchemy (sync) is simpler, not evil** — In Node.js you'd never write `db.users.findAllSync()` — it would block the entire server. But in FastAPI, sync `def` routes run in a threadpool, so a "blocking" ORM call does **not** block other requests. Many production FastAPI apps use sync SQLAlchemy without issues.

**3. You must pick one per route** — You cannot mix `await` inside a sync `def` route, and you cannot call blocking code directly inside `async def` (it would block the event loop). The `get_db` dependency must match the route's sync/async mode.

**4. The `get_db` pattern — why the confusion?**

```python
# SYNC db session — works with sync routes only
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ASYNC db session — works with async routes only
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

If you mix them (sync route + async session or vice versa), you get errors. **Choose one style per project** — mixing them is unnecessarily painful.

### Recommendation for a JS Migrant

**Start with sync SQLAlchemy + sync `def` routes.** It maps cleanly to what you'd do in Express with a promise-less ORM — except it won't block because FastAPI thread-pools it. Only reach for async when you need websocket-level concurrency or async HTTP calls inside a route.

### Python's `asyncio` vs Node.js Event Loop

- Node.js: single-threaded, everything non-blocking by coercion (callbacks/promises).
- Python asyncio: cooperative multitasking — your code must explicitly `await` to yield control. If any `async def` function does CPU work without `await`, the entire event loop stalls (same as JS).

### TL;DR Mental Model

```
Node.js:         [async by default] — sync code anywhere crashes the party
Python/FastAPI:  [sync by default]  — async is opt-in, FastAPI protects you from sync-blocking
```
