# Python Refresher — Concepts You Need for FastAPI

## 1. `yield` — Generators & Dependency Injection

### What it does

`yield` pauses a function, saves its state, and returns a value. The caller can resume it later.

```python
def count_up_to(n):
    i = 0
    while i < n:
        yield i
        i += 1

for num in count_up_to(3):
    print(num)  # 0, 1, 2
```

### Why FastAPI needs it — Dependencies with cleanup

FastAPI uses `yield` in `Depends()` to run **setup code**, then **teardown code** after the response is sent.

```python
from fastapi import Depends

def get_db():
    db = SessionLocal()       # setup: open connection
    try:
        yield db              # inject db into route
    finally:
        db.close()            # teardown: close connection

@app.get("/users")
def list_users(db=Depends(get_db)):  # db is the yielded value
    return db.query(User).all()
```

**Flow:** route handler gets `db` → handler runs → `finally` closes db → response sent.

### With context manager (`contextlib.contextmanager`)

```python
from contextlib import contextmanager

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Same result. FastAPI accepts both bare generators and `@contextmanager` decorated ones.

### Case: Transaction rollback on error

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()       # commit only if no exception in route
    except Exception:
        db.rollback()     # rollback if route raised
        raise
    finally:
        db.close()
```

### Case: Async generator

```python
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

---

## 2. Type Hints / Annotations

FastAPI uses type hints for **validation**, **serialization**, and **OpenAPI docs**.

### Basic syntax

```python
name: str = "hello"
age: int
items: list[str]
pairs: dict[str, int]
maybe: str | None = None        # Python 3.10+
maybe: Optional[str] = None     # Python 3.9 and earlier
```

### In function signatures

```python
def greet(name: str, count: int = 1) -> str:
    return f"{name} " * count
```

### How FastAPI uses them

```python
@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None) -> Item:
    # item_id → path param, validated as int
    # q       → query param, optional
    # Item    → response_model inferred from return type
    pass
```

### `List`, `Dict`, `Optional`, `Union` (pre-3.10 style)

```python
from typing import List, Dict, Optional, Union

ids: List[int] = [1, 2, 3]
data: Dict[str, int] = {"a": 1}
flag: Optional[bool] = None     # same as bool | None
val: Union[int, str] = "hello"  # same as int | str
```

New style (3.10+): `list[int]`, `dict[str, int]`, `str | None`, `int | str`.

---

## 3. Decorators (`@` syntax)

A decorator wraps a function to add behavior.

```python
def log_call(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@log_call
def say_hello(name):
    print(f"Hello {name}")

say_hello("Alice")
# Output:
# Calling say_hello
# Hello Alice
```

### How FastAPI uses them

```python
@app.get("/")         # registers the function as a GET route
@router.post("/x")    # registers under a router prefix
```

Under the hood: `app.get("/")` returns a decorator; calling that decorator with the function registers it in the router table.

---

## 4. Context Managers (`with`)

```python
with open("file.txt") as f:
    data = f.read()
# file is auto-closed here
```

Implement with `__enter__` / `__exit__`:

```python
class ManagedDB:
    def __enter__(self):
        self.conn = create_connection()
        return self.conn
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

with ManagedDB() as conn:
    conn.query(...)
```

Or with `contextlib`:

```python
from contextlib import contextmanager

@contextmanager
def managed_db():
    conn = create_connection()
    try:
        yield conn
    finally:
        conn.close()
```

### Relation to FastAPI: `yield` in dependencies is a context manager pattern applied per-request.

---

## 5. `if __name__ == "__main__":`

Guards code from running when the file is imported.

```python
# main.py
def run():
    print("starting")

if __name__ == "__main__":
    run()  # runs only when `python main.py`, NOT when imported
```

In FastAPI, you rarely need this — uvicorn launches the app directly:

```bash
uvicorn main:app
```

But you **can** add it for convenience:

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", reload=True)
```

---

## 6. `__init__.py` — Python Packages

Any directory with `__init__.py` becomes an importable **package**.

```
app/
├── __init__.py        # can be empty
├── routers/
│   ├── __init__.py
│   └── auth.py
└── models.py
```

```python
from app.routers.auth import router  # works because of __init__.py
```

**In FastAPI projects:** every subdirectory needs `__init__.py` (even empty) for imports to work.

---

## 7. `*args` and `**kwargs`

Collects extra positional and keyword arguments.

```python
def log(message, *args, **kwargs):
    print(f"MSG: {message}")
    print(f"Extra args: {args}")      # tuple
    print(f"Extra kwargs: {kwargs}")  # dict

log("hi", 1, 2, 3, a=4, b=5)
# MSG: hi
# Extra args: (1, 2, 3)
# Extra kwargs: {'a': 4, 'b': 5}
```

**Used in FastAPI:** rarely directly, but `Depends()` and middleware signatures use similar patterns internally.

---

## 8. Dunder Methods (`__str__`, `__repr__`, `__eq__`, etc.)

Special methods that customize built-in behavior.

```python
class User:
    def __init__(self, id, email):
        self.id = id
        self.email = email

    def __repr__(self):
        return f"User(id={self.id}, email={self.email})"

    def __str__(self):
        return self.email

    def __eq__(self, other):
        return isinstance(other, User) and self.id == other.id
```

| Method | Triggers when |
|---|---|
| `__init__` | `User(...)` — constructor |
| `__repr__` | `repr(obj)`, debugging |
| `__str__` | `str(obj)`, `print(obj)` |
| `__eq__` | `obj == other` |
| `__hash__` | `set()`, `dict` key usage |
| `__call__` | `obj()` — calling instance as function |
| `__enter__` / `__exit__` | `with obj:` — context manager |

---

## 9. `Enum` — Fixed Choices

```python
from enum import Enum

class Role(str, Enum):    # inherit str for JSON serialization
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

@app.get("/role/{role}")
def check_role(role: Role):
    return {"role": role.value}
```

FastAPI auto-validates that the value is one of the enum members and generates an OpenAPI dropdown.

---

## 10. `dataclasses` — Lightweight Data Containers

Alternative to Pydantic for simple cases (but Pydantic is preferred in FastAPI).

```python
from dataclasses import dataclass

@dataclass
class User:
    id: int
    email: str
    is_active: bool = True
```

Auto-generates `__init__`, `__repr__`, `__eq__`. Pydantic `BaseModel` does all this **plus** validation and serialization — use that in FastAPI.

---

## 11. `Literal` and `TypedDict` (typing module)

```python
from typing import Literal, TypedDict

# Literal: restrict to exact values
def set_mode(mode: Literal["dev", "prod", "test"]):
    pass

# TypedDict: type hints for dicts (not validation, just hints)
class UserDict(TypedDict):
    id: int
    email: str
```

FastAPI prefers Pydantic models over TypedDict, but Literal is useful:

```python
@app.get("/status")
def get_status(env: Literal["dev", "prod"] = "dev"):
    ...
```

---

## 12. `Any`, `Callable`, `TypeVar` — Advanced Typing

```python
from typing import Any, Callable, TypeVar

T = TypeVar("T")  # generic type

def identity(x: T) -> T:
    return x

def run_twice(fn: Callable[[int], str], val: int) -> tuple[str, str]:
    return fn(val), fn(val)
```

---

## 13. List/Dict/Set Comprehensions

```python
squares = [x**2 for x in range(5)]          # [0, 1, 4, 9, 16]
evens   = [x for x in range(10) if x % 2 == 0]
pairs   = {k: v for k, v in items if v > 0}
unique  = {x.strip() for x in names}
```

Often used in route handlers for data transformation.

---

## 14. `zip` and `enumerate`

```python
names = ["a", "b", "c"]
scores = [90, 80, 70]

for i, (name, score) in enumerate(zip(names, scores)):
    print(i, name, score)  # 0 a 90 / 1 b 80 / 2 c 70
```

---

## 15. Exception Handling

```python
try:
    result = risky_operation()
except ValueError as e:
    log_error(e)
    raise  # re-raise, don't swallow
except (TypeError, KeyError):
    return fallback()
else:
    print("no error")  # runs only if no exception
finally:
    cleanup()          # always runs
```

In FastAPI routes, raise `HTTPException` instead of returning error dicts manually.

---

## Summary: Where each concept hits FastAPI

| Python Concept | Where you'll see it in FastAPI |
|---|---|
| `yield` / generators | `Depends()` with cleanup — `get_db` session |
| Type hints | Everything — path/query/body validation, return types |
| Decorators `@` | `@app.get`, `@router.post`, `@app.middleware` |
| `with` / context manager | `get_db` (yield pattern), file handling |
| `if __name__` | `main.py` optional uvicorn launcher |
| `__init__.py` | Package structure for `app/`, `routers/` |
| `*args` / `**kwargs` | Middleware internals, generic wrappers |
| Dunder methods | Pydantic models internally, custom classes |
| `Enum` | Fixed-choice query/path params |
| `dataclasses` | Pydantic does this × 10 |
| `Literal` | Restrict param values |
| Comprehensions | Data transforms in routes |
| Exceptions `try/except` | Error handling → `HTTPException` |
