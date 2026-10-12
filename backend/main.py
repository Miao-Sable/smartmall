"""智慧购物 H5 后端入口

启动：uvicorn main:app --reload
文档：http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import init_db
from app.routers import auth, meta, products, scan, shopping_list, stats, user


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()  # 建表 + 灌入字典 mock 数据
    yield


app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)

# 开发环境放开跨域，便于前端直连调试
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(user.router, prefix="/api/user", tags=["用户"])
app.include_router(meta.router, prefix="/api/meta", tags=["字典"])
app.include_router(products.router, prefix="/api/products", tags=["商品"])
app.include_router(scan.router, prefix="/api/scan", tags=["扫码"])
app.include_router(stats.router, prefix="/api/stats", tags=["统计"])
app.include_router(shopping_list.router, prefix="/api/shopping-list", tags=["购物清单"])


@app.get("/")
def root():
    return {"message": "智慧购物 API", "docs": "/docs", "health": "/api/health"}


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}
