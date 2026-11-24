# Server OCR: Unlimited-OCR-2 qua bản SGLang tuỳ biến của chính repo model (ADR-005 mục 6).
# Chạy Python 3.10 riêng, tách khỏi backend/. Model không nằm trong image: mount ./model vào /model.
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive PIP_NO_CACHE_DIR=1 UV_LINK_MODE=copy
# python3-dev + build-essential: Triton biên dịch kernel lúc chạy (cần gcc). ninja đã nằm trong dependency của wheel.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv python3-pip python3-dev build-essential ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install uv
WORKDIR /srv
COPY model/wheel/sglang-0.5.20.dev13+g75b9b06b02-py3-none-any.whl /tmp/
RUN uv venv --python 3.10 /srv/.venv \
    && . /srv/.venv/bin/activate \
    && uv pip install "/tmp/sglang-0.5.20.dev13+g75b9b06b02-py3-none-any.whl" pymupdf==1.27.2.2 fastokens==0.3.2 \
    && rm -f /tmp/*.whl
# deep_ep (SGLang) cần CUDA_HOME có nvcc: dùng bản nvcc đi kèm gói torch cu13 trong venv.
ENV CUDA_HOME=/srv/.venv/lib/python3.10/site-packages/nvidia/cu13
ENV PATH=$CUDA_HOME/bin:/srv/.venv/bin:$PATH
EXPOSE 10000
