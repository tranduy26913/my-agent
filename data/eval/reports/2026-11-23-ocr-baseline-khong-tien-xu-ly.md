# Đo chất lượng OCR (2026-11-23)

Nguồn đáp án: `data/scan/ground-truth.md`. CER/WER càng thấp càng tốt; trường đúng càng cao càng tốt.

## Engine `tesseract`

### Văn bản thông báo SVT-TB-018

| File | CER | CER (bỏ dấu) | WER | Thời gian |
|---|---|---|---|---|
| SVT-TB-018-dieu-chinh-gio-lam-viec.png | 3.8% | 3.3% | 6.5% | 1967 ms |
| SVT-TB-018-dieu-chinh-gio-lam-viec.pdf | 4.4% | 3.4% | 8.5% | 2481 ms |

### Phiếu đề nghị thanh toán (trường đúng)

| File | Đúng cả dấu | Đúng (bỏ dấu) | Thời gian | Trường không tìm thấy |
|---|---|---|---|---|
| de-nghi-thanh-toan-CTP-NV017.png | 8/12 | 8/12 | 2676 ms | khoan1.thanh_tien, khoan2.thanh_tien, khoan3.thanh_tien, khoan4.thanh_tien |
| de-nghi-thanh-toan-CTP-NV018.png | 9/13 | 9/13 | 2457 ms | khoan1.thanh_tien, khoan2.thanh_tien, khoan3.thanh_tien, khoan4.thanh_tien |
