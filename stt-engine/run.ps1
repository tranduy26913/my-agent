# Chạy server STT trên máy host (cổng 127.0.0.1:10002). Lần đầu tự tạo .venv và tải model (vài trăm MB đến ~1,6 GB).
# Chọn cấu hình bằng biến môi trường, ví dụ:
#   $env:STT_MODEL="large-v3-turbo"; $env:STT_DEVICE="cpu"; $env:STT_COMPUTE_TYPE="int8"; ./run.ps1
#   $env:STT_DEVICE="cuda"; $env:STT_COMPUTE_TYPE="float16"; ./run.ps1      # cần cuBLAS + cuDNN 9 (xem README)
Set-Location $PSScriptRoot
if (-not (Test-Path .venv)) {
  python -m venv .venv
  .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
}
.\.venv\Scripts\python.exe -m uvicorn whisper_server:app --app-dir server --host 127.0.0.1 --port 10002
