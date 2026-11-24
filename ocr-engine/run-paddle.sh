#!/usr/bin/env bash
# Chạy server PaddleOCR-VL-1.6 (cổng 127.0.0.1:10001, chỉ máy này gọi được). Cần: image svt-ocr-engine:dev (docker build -t
# svt-ocr-engine:dev .) và model trong ./models/paddleocr-vl-1.6 (./download-paddleocr-vl.sh).
# Model nạp lười ở lần gọi đầu và tự nhả VRAM sau PADDLE_VL_IDLE_SECONDS (mặc định 30 giây) để chat còn chỗ.
set -euo pipefail
cd "$(dirname "$0")"
NAME=svt-ocr-paddle
docker rm -f "$NAME" >/dev/null 2>&1 || true
ROOT="$(pwd -W 2>/dev/null || pwd)"
MSYS_NO_PATHCONV=1 docker run -d --name "$NAME" --gpus all --ipc=host --restart unless-stopped \
  -p 127.0.0.1:10001:10001 \
  -v "$ROOT/models:/models:ro" -v "$ROOT/server:/server:ro" \
  -e PADDLE_VL_IDLE_SECONDS="${PADDLE_VL_IDLE_SECONDS:-30}" \
  svt-ocr-engine:dev python -m uvicorn paddle_vl_server:app --app-dir /server --host 0.0.0.0 --port 10001
