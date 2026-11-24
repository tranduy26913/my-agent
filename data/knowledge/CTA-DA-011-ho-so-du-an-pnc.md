---
doc_id: CTA-DA-011
so_hieu: DA-2026-07/CHARTER
tieu_de: Điều lệ dự án Cổng dịch vụ khách hàng Phương Nam (PNC Portal)
loai: ho-so-du-an
phong_ban_so_huu: DA
pham_vi_truy_cap: phong-ban
phong_ban_duoc_xem: [DA, KD, BGD]
vai_tro_duoc_xem: []
ma_du_an: DA-2026-07
phan_loai_bao_mat: Mat
ngay_ban_hanh: 2026-05-25
hieu_luc_tu: 2026-05-25
het_hieu_luc: null
thay_the: null
phien_ban: 1.2
nguoi_ky: Trần Thu Trang – Trưởng phòng Dự án
---

# ĐIỀU LỆ DỰ ÁN (PROJECT CHARTER)
## Dự án: Cổng dịch vụ khách hàng trực tuyến – Khách hàng Phương Nam
**Mã dự án: DA-2026-07 – Phân loại: MẬT**

### 1. Thông tin chung
| Mục | Nội dung |
|---|---|
| Khách hàng | Công ty Phân phối Năng lượng Phương Nam (gọi tắt là "PNC") – khách hàng giả lập |
| Hợp đồng | Số 26/2026/HĐ-CTA-PNC ký ngày 20/5/2026 |
| Giá trị hợp đồng | 4.850.000.000 đồng (đã gồm VAT) |
| Ngân sách chi phí nội bộ | 3.200.000.000 đồng |
| Thời gian | 01/6/2026 – 31/12/2026 |
| Giám đốc dự án (PM) | Hoàng Minh Đức |
| Nhà tài trợ dự án (Sponsor) | Trần Thu Trang – Trưởng phòng Dự án |
| Đầu mối kinh doanh | Lê Hoàng Nam – Trưởng phòng Kinh doanh |

### 2. Mục tiêu
1. Xây dựng cổng web và ứng dụng di động cho phép khách hàng của PNC tra cứu hóa đơn, thanh toán trực tuyến, gửi yêu cầu sửa chữa.
2. Giảm 40% cuộc gọi đến tổng đài của PNC sau 6 tháng vận hành.
3. Tích hợp với hệ thống CRM và hệ thống hóa đơn hiện có của PNC qua API.

### 3. Phạm vi
- **Trong phạm vi**: cổng web, ứng dụng di động (iOS, Android), tích hợp CRM và hóa đơn, chatbot trả lời câu hỏi thường gặp, đào tạo người dùng, bảo hành 6 tháng.
- **Ngoài phạm vi**: thay thế hệ thống hóa đơn của PNC, tích hợp cổng thanh toán quốc tế, vận hành tổng đài.

### 4. Các mốc chính
| Mốc | Nội dung | Ngày hoàn thành |
|---|---|---|
| M1 | Khảo sát và tài liệu yêu cầu được ký duyệt | 30/6/2026 |
| M2 | Thiết kế giải pháp và giao diện được duyệt | 31/7/2026 |
| M3 | Hoàn thành phát triển giai đoạn 1 (web) | 30/9/2026 |
| M4 | Kiểm thử chấp nhận (UAT) | 15/11/2026 |
| M5 | Vận hành chính thức (go-live) | 01/12/2026 |
| M6 | Nghiệm thu, thanh lý giai đoạn triển khai | 31/12/2026 |

### 5. Đội dự án
| Vai trò | Thành viên |
|---|---|
| Giám đốc dự án | Hoàng Minh Đức |
| Trưởng nhóm kỹ thuật | Trịnh Văn Sơn |
| Phân tích nghiệp vụ | Mai Thị Ngọc |
| Lập trình viên | Đinh Công Tuấn, Lý Thị Hoa |
| Kiểm thử | Phan Văn Lộc |

### 6. Rủi ro chính
| Rủi ro | Mức | Biện pháp |
|---|---|---|
| API hệ thống hóa đơn của PNC thiếu tài liệu | Cao | Yêu cầu PNC cử đầu mối kỹ thuật; dựng môi trường giả lập API |
| Thay đổi yêu cầu sau M2 | Trung bình | Quy trình quản lý thay đổi, mọi thay đổi có ước lượng và ký duyệt |
| Thiếu nhân sự di động | Trung bình | Thuê ngoài có kiểm soát, ngân sách dự phòng 10% |
| Dữ liệu khách hàng cá nhân | Cao | Tuân thủ Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân; ẩn danh dữ liệu trên môi trường kiểm thử |

### 7. Điều khoản phạt và thanh toán (tóm tắt)
- Thanh toán theo 4 đợt: 20% khi ký hợp đồng, 30% khi đạt M2, 30% khi đạt M5, 20% khi đạt M6.
- Chậm tiến độ do lỗi của CTA: phạt 0,1% giá trị hợp đồng mỗi ngày, tối đa 8%.
