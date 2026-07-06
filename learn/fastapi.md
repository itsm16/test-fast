# FastAPI validation flow

The request is received right here in the route function parameter. FastAPI automatically
validates the request body against the Pydantic model and injects the validated instance —
so it's obvious just by looking at the function signature that validation happens at
this boundary.

```python
@auth_router.post("/register")
def register_user_route(body: RegisterUserDto):
    # body is already validated by FastAPI
    return auth_controller.register_user(body)
```

Validation happens at the boundary (route). Downstream layers (controller, service)
don't need to re-import Pydantic models — they can accept plain dicts, dataclasses,
or individual fields. This keeps the service decoupled from the web framework.

## Dict spreading & duplicate keys

When using `**dict` to spread, duplicate keys get overwritten — last one wins:

```python
# If service returns {"message": "from service"}
return {"message": "from controller", **user}
# Result: {"message": "from service"} — service overwrote controller
```

Python processes the dict literal left to right. So the second occurrence of a key
always overwrites the first. Be mindful of this when merging controller response
with service output.

To avoid accidentally overwriting keys, use distinct top-level keys like
`message`, `status`, `data` instead of spreading raw service output.

## Database session

`sessionmaker` is a factory that creates DB sessions from an engine's connection pool
— no reconnect overhead.

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

engine = create_engine(getenv("DATABASE_URL"), echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- **`create_engine`** — creates a connection pool. Connects lazily on first query.
- **`sessionmaker`** — factory that returns a `Session` borrowed from the pool.
- **`get_db`** — FastAPI dependency (`Depends(get_db)`) that yields a session and
  auto-closes it when the request ends. Use it in routes:

```python
@router.post("/signup")
def signup(body: UserCreate, db: Session = Depends(get_db)):
    user = User(email=body.email, ...)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
```
