#!/usr/bin/env bash
# Tải PaddlePaddle/PaddleOCR-VL-1.6 (Apache-2.0, ~1,9 GB) về models/paddleocr-vl-1.6/. Chạy lại được.
set -euo pipefail
cd "$(dirname "$0")/models/paddleocr-vl-1.6"
BASE=https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6/resolve/main
for f in LICENSE added_tokens.json chat_template.jinja config.json configuration_paddleocr_vl.py generation_config.json \
         image_processing_paddleocr_vl.py inference.yml modeling_paddleocr_vl.py preprocessor_config.json \
         processing_paddleocr_vl.py processor_config.json special_tokens_map.json tokenizer.json tokenizer.model \
         tokenizer_config.json model.safetensors; do
  echo ">> $f"; curl -fL -C - --retry 5 --retry-delay 3 -s -o "$f" "$BASE/$f"
done
echo XONG
