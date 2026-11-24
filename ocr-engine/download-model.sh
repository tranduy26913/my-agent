#!/usr/bin/env bash
# Tải baidu/Unlimited-OCR-2 (MIT, ~6,9 GB) và wheel SGLang tuỳ biến về ocr-engine/model/. Chạy lại được (curl -C -).
# Cần: curl. Dùng bản gốc từ huggingface.co; không cần tài khoản.
set -euo pipefail
cd "$(dirname "$0")/model"
BASE=https://huggingface.co/baidu/Unlimited-OCR-2/resolve/main
FILES=(
  config.json generation_config.json special_tokens_map.json tokenizer.json tokenizer_config.json
  model.safetensors.index.json configuration_deepseek_v2.py conversation.py dash_attention.py deepencoder.py
  modeling_deepseekv2.py modeling_unlimitedocr.py packing_patch.py _sparse_base_impl.py
  sparse_gather_e2e_triton.py sparse_gather_triton.py
  model-00002-of-00002.safetensors model-00001-of-00002.safetensors
  "wheel/sglang-0.5.20.dev13+g75b9b06b02-py3-none-any.whl"
)
# WHEEL_ONLY=1: chỉ tải wheel SGLang (15 MB) mà Dockerfile cần để build image; bỏ trọng số Unlimited-OCR (6,7 GB, không chạy được
# trên card 8 GB, xem README.md).
if [ "${WHEEL_ONLY:-0}" = 1 ]; then FILES=("wheel/sglang-0.5.20.dev13+g75b9b06b02-py3-none-any.whl"); fi
for f in "${FILES[@]}"; do
  echo ">> $f"
  curl -fL -C - --retry 5 --retry-delay 3 -o "$f" "$BASE/${f//+/%2B}"
done
echo "XONG"
