#!/usr/bin/env bash
# Chạy server Unlimited-OCR-2 (cổng 127.0.0.1:10000). Cần: image svt-ocr-engine:dev (docker build -t svt-ocr-engine:dev .)
# và model trong ./model (./download-model.sh). GPU 8 GB không chạy chung được với local-ai (qwen3-4b): tắt local-ai trước.
set -euo pipefail
cd "$(dirname "$0")"
NAME=svt-ocr
docker rm -f "$NAME" >/dev/null 2>&1 || true
MSYS_NO_PATHCONV=1 docker run -d --name "$NAME" --gpus all --ipc=host --shm-size 8g \
  -p 127.0.0.1:10000:10000 -v "$(pwd -W 2>/dev/null || pwd)/model:/model:ro" \
  -e SGLANG_UOCR_EANABLE_DOC_LIMIT=1 -e SGLANG_UOCR_DOC_GUNDAM_PAGE_WINDOW=10 -e SGLANG_UOCR_DOC_BASE_PAGE_WINDOW=10 \
  -e SGLANG_UOCR_MAX_PAGE_TOKENS=20000 -e SGLANG_OPT_UOCR_SAM_REL_POS_BIAS_MB=64 \
  -e SGLANG_UOCR_SHM_WRAP_MODEL_DATA=1 -e SGLANG_UOCR_SHM_WRAP_MIN_MB=1 -e SGLANG_VLM_CACHE_SIZE_MB=0 \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  -e CUDA_HOME=/srv/.venv/lib/python3.10/site-packages/nvidia/cu13 \
  -e PATH=/srv/.venv/lib/python3.10/site-packages/nvidia/cu13/bin:/srv/.venv/bin:/usr/local/bin:/usr/bin:/bin \
  svt-ocr-engine:dev python -m sglang.launch_server \
  --model-path /model --served-model-name Unlimited-OCR-2 --chat-template unlimited-ocr \
  --tokenizer-backend fastokens --dtype float16 \
  --mem-fraction-static "${MEM_FRACTION:-0.85}" --max-running-requests 1 --max-prefill-tokens 2048 \
  --enable-custom-logit-processor --allow-auto-truncate --disable-radix-cache --mm-preprocess-cache-size-mb 0 \
  --disable-cuda-graph ${EXTRA_ARGS:-} --host 0.0.0.0 --port 10000
