from fastapi import FastAPI

from receptenapp.api import health, imports, me, recipes
from receptenapp.core.errors import register_exception_handlers

app = FastAPI(title="Kladje API")

register_exception_handlers(app)
app.include_router(health.router)
app.include_router(me.router)
app.include_router(recipes.router)
app.include_router(imports.router)
