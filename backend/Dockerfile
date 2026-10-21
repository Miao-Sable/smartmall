# SmartMall 后端镜像
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先复制依赖清单，独立一层便于缓存
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# 源码 + mock 数据（mock 需与后端一起打包，运行时读商品/字典）
COPY backend/ /app/backend/
COPY mock/ /app/mock/

WORKDIR /app/backend
EXPOSE 8000

# 启动时自动 init_db()：建表 + 灌字典 + 建默认档案
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
