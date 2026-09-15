import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from core import client
from seed import seed
from auth import router as auth_router
from public import router as public_router
from workspace import router as workspace_router
from platform_routes import router as platform_router
from media import router as media_router
from jobs import router as jobs_router

@asynccontextmanager
async def lifespan(app):
    await seed()
    yield
    client.close()

app = FastAPI(title="AuraStay", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.environ['CORS_ORIGINS'].split(','),
                   allow_credentials=False, allow_methods=['*'], allow_headers=['*'])
for router in (auth_router, public_router, workspace_router, platform_router, media_router, jobs_router):
    app.include_router(router, prefix='/api')

@app.get('/api/health')
async def health():
    return {'status': 'ok', 'payments_enabled': False}