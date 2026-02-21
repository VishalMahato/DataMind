from fastapi import FastAPI

from app.api.routes import router as api_router


app = FastAPI(title="Boardroom AI Backend")

app.include_router(api_router)
