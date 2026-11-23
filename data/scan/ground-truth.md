# Đáp án gốc (ground truth) cho bản scan

Dùng để đo chất lượng OCR (CER/WER) và trích xuất có cấu trúc. **Không nạp file này vào kho tri thức** (nó là đáp án).

## 1. `SVT-TB-018-dieu-chinh-gio-lam-viec.pdf` (PDF chỉ có ảnh, không có lớp text)

Metadata dự kiến khi nạp:

```yaml
doc_id: SVT-TB-018
so_hieu: 18/2026/TB-SVT
tieu_de: Thông báo điều chỉnh giờ làm việc mùa đông
loai: thong-bao
phong_ban_so_huu: HCNS
pham_vi_truy_cap: cong-khai
ngay_ban_hanh: 2026-11-10
hieu_luc_tu: 2026-12-01
het_hieu_luc: 2027-03-01
```

Văn bản gốc:

```text
CÔNG TY CỔ PHẦN CÔNG NGHỆ SAO VIỆT
Số: 18/2026/TB-SVT
CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
Hà Nội, ngày 10 tháng 11 năm 2026

THÔNG BÁO
Về việc điều chỉnh giờ làm việc mùa đông

Căn cứ khoản 4 Điều 3 Nội quy lao động ban hành kèm theo Quyết định
số 05/2025/QĐ-SVT; xét đề nghị của Phòng Hành chính - Nhân sự,
Công ty thông báo điều chỉnh giờ làm việc như sau:

1. Thời gian áp dụng: từ ngày 01/12/2026 đến hết ngày 28/02/2027.
2. Giờ làm việc trong thời gian áp dụng:
   - Buổi sáng: từ 08 giờ 30 đến 12 giờ 00;
   - Buổi chiều: từ 13 giờ 00 đến 17 giờ 30.
3. Thời giờ làm việc vẫn bảo đảm 08 giờ/ngày, 40 giờ/tuần.
4. Cách tính đi muộn, về sớm áp dụng theo khung giờ mới.
5. Từ ngày 01/3/2027, giờ làm việc trở lại theo Điều 3 Nội quy lao động.

Các Trưởng phòng có trách nhiệm phổ biến thông báo này đến người lao động.

Nơi nhận:
- Toàn thể người lao động;
- Lưu: VT, HCNS.
TỔNG GIÁM ĐỐC
Phạm Đức Long
```

Lưu ý: con dấu đỏ đè lên vùng chữ ký – OCR thường sinh ký tự rác ở vùng này.

## 2. Giấy đề nghị thanh toán công tác phí – kết quả trích xuất mong đợi

Schema gợi ý: `so_phieu, ma_nv, ho_ten, phong_ban, noi_cong_tac, tu_ngay, den_ngay, cac_khoan[{noi_dung, so_luong, thanh_tien, co_hoa_don}], tong_cong, da_tam_ung, de_nghi_thanh_toan_them, ngay_lap`.

### `de-nghi-thanh-toan-CTP-NV017.png`

```json
{
  "so_phieu": "CTP-2026-0412", "ma_nv": "NV017", "ho_ten": "Lê Văn Bình", "phong_ban": "Kinh doanh",
  "noi_cong_tac": "Đà Nẵng", "tu_ngay": "2026-10-12", "den_ngay": "2026-10-14",
  "cac_khoan": [
    {"noi_dung": "Vé máy bay khứ hồi HN - ĐN", "so_luong": "1", "thanh_tien": 3450000, "co_hoa_don": true},
    {"noi_dung": "Khách sạn (1.150.000 đ/đêm)", "so_luong": "2 đêm", "thanh_tien": 2300000, "co_hoa_don": true},
    {"noi_dung": "Phụ cấp lưu trú", "so_luong": "3 ngày", "thanh_tien": 900000, "co_hoa_don": null},
    {"noi_dung": "Taxi tại nơi công tác", "so_luong": "3 ngày", "thanh_tien": 620000, "co_hoa_don": true}
  ],
  "tong_cong": 7270000, "da_tam_ung": 5000000, "de_nghi_thanh_toan_them": 2270000, "ngay_lap": "2026-10-16"
}
```

Kiểm tra theo Quy định công tác phí 08/2025/QĐ-SVT: **hợp lệ** (khách sạn Đà Nẵng ≤ 1.200.000 đ/đêm; lưu trú 300.000 × 3; taxi ≤ 500.000/ngày; nộp trong 7 ngày làm việc; tổng ≤ 20 triệu → Kế toán trưởng duyệt).

### `de-nghi-thanh-toan-CTP-NV018.png`

```json
{
  "so_phieu": "CTP-2026-0467", "ma_nv": "NV018", "ho_ten": "Hồ Thị Phương", "phong_ban": "Kinh doanh",
  "noi_cong_tac": "TP. Hồ Chí Minh", "tu_ngay": "2026-11-03", "den_ngay": "2026-11-06",
  "cac_khoan": [
    {"noi_dung": "Vé máy bay khứ hồi HN - HCM", "so_luong": "1", "thanh_tien": 4280000, "co_hoa_don": true},
    {"noi_dung": "Khách sạn (1.450.000 đ/đêm)", "so_luong": "3 đêm", "thanh_tien": 4350000, "co_hoa_don": true},
    {"noi_dung": "Phụ cấp lưu trú", "so_luong": "4 ngày", "thanh_tien": 1200000, "co_hoa_don": null},
    {"noi_dung": "Taxi tại nơi công tác", "so_luong": "4 ngày", "thanh_tien": 2350000, "co_hoa_don": true},
    {"noi_dung": "Tiếp khách", "so_luong": "1", "thanh_tien": 3000000, "co_hoa_don": false}
  ],
  "tong_cong": 15180000, "da_tam_ung": 8000000, "de_nghi_thanh_toan_them": 7180000, "ngay_lap": "2026-11-18"
}
```

Kiểm tra mong đợi – **có vi phạm, cần người duyệt**:
1. Khách sạn 1.450.000 đ/đêm > mức tối đa 1.200.000 đ/đêm cho TP.HCM (NV018 cấp L2, không được +30%) → vượt 750.000 đ (Điều 5).
2. Taxi 2.350.000 đ / 4 ngày > 500.000 đ/ngày × 4 = 2.000.000 đ → vượt 350.000 đ (khoản 4 Điều 4).
3. Tiếp khách 3.000.000 đ không có hóa đơn và không thuộc danh mục công tác phí → loại hoặc chuyển sang thủ tục chi tiếp khách.
4. Ngày lập 18/11 so với ngày về 06/11: 8 ngày làm việc (07–08/11 là cuối tuần) → **quá hạn 7 ngày làm việc** (Điều 7).

Đây là bài kiểm tra cho bước "validate + người duyệt khi có ngoại lệ" (GĐ2 ngày 10, và kịch bản tự động hóa trong `docs/04-...`).
