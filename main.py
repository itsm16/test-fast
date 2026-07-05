from fastapi import FastAPI
from src.common.utils.router import api_router

app = FastAPI()

app.include_router(api_router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}