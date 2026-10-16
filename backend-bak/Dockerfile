# backend-bak 部署镜像：基于迁移后的 FastAPI 后端
FROM python:3.11-slim

WORKDIR /app

# 安装与 backend/ 一致的 Python 依赖
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 复制迁移后的后端代码
COPY backend-bak/ /app/

# FastAPI 监听 0.0.0.0，便于容器外访问
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
