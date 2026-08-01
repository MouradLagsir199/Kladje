from fastapi import FastAPI

from receptenapp.api import health
from receptenapp.core.errors import register_exception_handlers

app = FastAPI(title="Receptenapp API")

register_exception_handlers(app)
app.include_router(health.router)
