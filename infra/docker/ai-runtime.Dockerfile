# services/ai-runtime —— YOLO26 GPU 推理
#
# 基础镜像用官方 pytorch/pytorch（torch+CUDA+cuDNN 已预装在镜像层，避免 pip
# 安装 torch 时解包 6GB 耗尽 WSL2 虚拟磁盘）。
FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn \
    DEBIAN_FRONTEND=noninteractive

# 基础镜像是 ubuntu-based；切清华镜像源避免 apt 502
RUN set -eux; \
    for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.list; do \
        [ -f "$f" ] || continue; \
        sed -i 's#http://archive.ubuntu.com#https://mirrors.tuna.tsinghua.edu.cn#g; s#http://security.ubuntu.com#https://mirrors.tuna.tsinghua.edu.cn#g' "$f"; \
    done; \
    apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 只装 ultralytics + web 框架（torch 已在基础镜像里，requirements 里剥掉）
COPY services/ai-runtime/requirements.txt /tmp/requirements.txt
RUN sed -i -E '/^torch(\b|>=|==)/d;/^torchvision\b/d' /tmp/requirements.txt \
    && pip install --retries 5 -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# 源码 + 权重
COPY services/ai-runtime /app

ENV PYTHONPATH=/app/src \
    INFERENCE_DEVICE=cuda:0 \
    DETECTOR_MODEL=yolo26_campus \
    USE_REAL_MODELS=True

EXPOSE 9001

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -fsS http://127.0.0.1:9001/health || exit 1

CMD ["python", "main.py"]
