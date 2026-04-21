# apps/api —— FastAPI 控制面 + Python 解码线程池（OpenCV/FFmpeg）
# 不需要 GPU；转发推理请求到 ai-runtime。
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

# Debian 官方源被 502，切清华镜像（python:3.11-slim 基于 debian trixie）
# OpenCV 需要 libgl/libglib；FFmpeg 提供解码；curl 用于 healthcheck
RUN set -eux; \
    for f in /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources; do \
        [ -f "$f" ] || continue; \
        sed -i 's#http://deb.debian.org#https://mirrors.tuna.tsinghua.edu.cn#g' "$f"; \
    done; \
    apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY apps/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --retries 5 -r /app/requirements.txt

COPY apps/api /app

ENV AI_RUNTIME_URL=http://ai-runtime:9001 \
    USE_SQLITE_FALLBACK=True \
    SQLITE_PATH=/data/campus_guard.db \
    DATABASE_URL=postgresql+asyncpg://campus_guard:campus_guard_secret@postgres:5432/campus_guard

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
