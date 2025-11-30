# Multi-arch (ARM/Raspberry Pi対応) のPythonベースイメージ
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 必要最低限のビルドツールと依存パッケージ
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       git \
       curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python依存関係を先にインストールしてキャッシュを効かせる
COPY pyproject.toml uv.lock* ./

# uvがあれば使うが、なければpipでインストール
RUN pip install --upgrade pip \
    && pip install uv || true

# uvがある場合はuv経由、なければpipで依存関係をインストール
RUN if command -v uv >/dev/null 2>&1; then \
        uv pip install --system .; \
    else \
        pip install .; \
    fi

# アプリ本体をコピー
COPY . .

# Streamlit用のポート
EXPOSE 8501

# Qdrantは別コンテナを想定（QDRANT_HOST/QDRANT_PORTで接続）

# 起動コマンド
CMD ["streamlit", "run", "main.py", "--server.address=0.0.0.0", "--server.port=8501"]

