FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000

# 隐私默认：容器内监听 0.0.0.0（映射到宿主机端口时请自行限制）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
