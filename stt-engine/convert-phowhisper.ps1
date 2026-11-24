# Chuyển vinai/PhoWhisper-small (PyTorch) sang CTranslate2 int8 vào models/phowhisper-small (~240 MB). Chạy một lần.
# Dùng venv tạm riêng vì cần torch + transformers (nặng), không cài vào .venv của server.
Set-Location $PSScriptRoot
$tmp = Join-Path $env:TEMP "stt-conv"
if (-not (Test-Path $tmp)) {
  python -m venv $tmp
  & "$tmp\Scripts\python.exe" -m pip install -q --index-url https://download.pytorch.org/whl/cpu torch
  & "$tmp\Scripts\python.exe" -m pip install -q ctranslate2 transformers huggingface_hub sentencepiece
}
& "$tmp\Scripts\ct2-transformers-converter.exe" --model vinai/PhoWhisper-small --output_dir models\phowhisper-small `
  --copy_files tokenizer.json preprocessor_config.json --quantization int8 --force
