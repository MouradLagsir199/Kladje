from fastapi import FastAPI

from receptenapp.api import health

app = FastAPI(title="Receptenapp API")

app.include_router(health.router)
