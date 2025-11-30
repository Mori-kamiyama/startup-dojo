#!/usr/bin/env bash
set -e

# Raspberry Pi / Linux 上でのワンコマンド起動スクリプト
# 使い方: bash run.sh

echo "[entre-rag] Qdrant + App を起動します..."

# Qdrantイメージを先にpull（ARM対応タグ）
docker compose pull qdrant || true

# アプリをビルドして起動
docker compose up --build

