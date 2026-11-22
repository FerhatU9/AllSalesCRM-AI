FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements-runtime.txt ./
RUN pip install --no-cache-dir -r requirements-runtime.txt \
    && groupadd --system allsales \
    && useradd --system --gid allsales --home-dir /app allsales

COPY app.py ./
COPY backend ./backend
COPY allsales ./allsales

USER allsales
EXPOSE 8000
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
