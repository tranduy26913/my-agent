---
doc_id: CTA-HD-008
so_hieu: HD-CNTT-2026-01
tieu_de: Hướng dẫn sử dụng dịch vụ CNTT
loai: huong-dan
phong_ban_so_huu: CNTT
pham_vi_truy_cap: cong-khai
phong_ban_duoc_xem: []
vai_tro_duoc_xem: []
ngay_ban_hanh: 2026-01-05
hieu_luc_tu: 2026-01-05
het_hieu_luc: null
thay_the: null
phien_ban: 3
nguoi_ky: Đỗ Quang Huy – Trưởng phòng CNTT
---

# HƯỚNG DẪN SỬ DỤNG DỊCH VỤ CNTT

## 1. Kênh hỗ trợ
- Cổng yêu cầu hỗ trợ (helpdesk): **it.cty-a.example** – kênh chính thức cho mọi yêu cầu.
- Điện thoại khẩn cấp: máy lẻ **1900** (giờ hành chính), hotline trực ngoài giờ 0901 000 199 (chỉ cho sự cố mức P1).
- Báo cáo sự cố an toàn thông tin: security@cty-a.example hoặc máy lẻ 1999.

## 2. Mức ưu tiên và thời gian phản hồi (SLA)
| Mức | Định nghĩa | Phản hồi | Mục tiêu khắc phục |
|---|---|---|---|
| P1 | Hệ thống chính ngừng hoạt động, ảnh hưởng nhiều người | 30 phút | 4 giờ |
| P2 | Ảnh hưởng một phòng hoặc một nghiệp vụ quan trọng | 2 giờ | 1 ngày làm việc |
| P3 | Ảnh hưởng một người, có cách làm tạm | 1 ngày làm việc | 3 ngày làm việc |
| P4 | Yêu cầu dịch vụ (cấp quyền, cài phần mềm, thiết bị) | 1 ngày làm việc | Theo mục 5, 6 |

## 3. Đặt lại mật khẩu
1. Truy cập **id.cty-a.example**, chọn "Quên mật khẩu".
2. Xác thực bằng ứng dụng MFA đã đăng ký.
3. Đặt mật khẩu mới theo Chính sách an toàn thông tin (tối thiểu 12 ký tự).
4. Mất thiết bị MFA: tạo yêu cầu helpdesk mức P3 và đến trực tiếp Phòng CNTT (tầng 8) mang theo thẻ nhân viên.

## 4. Kết nối VPN
1. Cài ứng dụng **CTA Connect** từ Cổng phần mềm công ty (Software Center).
2. Đăng nhập bằng tài khoản công ty và xác thực MFA.
3. VPN bắt buộc khi truy cập HRM, hệ thống kế toán và kho mã nguồn từ ngoài văn phòng.
4. Lỗi thường gặp:
   - "Authentication failed": kiểm tra mật khẩu hết hạn hoặc tài khoản bị khóa sau 5 lần sai; tài khoản tự mở khóa sau 30 phút.
   - Kết nối được nhưng không vào được HRM: kiểm tra đã chọn cổng "CTA-HN" chưa; xóa bộ nhớ DNS (`ipconfig /flushdns` trên Windows).

## 5. Cấp quyền truy cập hệ thống
1. Tạo yêu cầu trên helpdesk, chọn loại "Cấp quyền", ghi rõ hệ thống, mức quyền và lý do.
2. Quản lý trực tiếp phê duyệt → Chủ sở hữu hệ thống phê duyệt → Phòng CNTT thực hiện.
3. Thời gian hoàn thành: **02 ngày làm việc** kể từ khi đủ phê duyệt.
4. Quyền truy cập hệ thống chứa thông tin Mật được rà soát 6 tháng/lần; quyền không còn cần thiết sẽ bị thu hồi.

## 6. Thiết bị
1. Nhân viên mới: Trưởng phòng đặt thiết bị trước ngày nhận việc ít nhất **05 ngày làm việc**.
2. Thay thế thiết bị hỏng: mang thiết bị đến Phòng CNTT; thiết bị dự phòng được cấp trong ngày nếu còn.
3. Không tự cài phần mềm ngoài Cổng phần mềm công ty. Phần mềm cần thêm: yêu cầu mức P4.

## 7. Email và lưu trữ
1. Hộp thư 50 GB; tệp đính kèm tối đa 25 MB. Tệp lớn hơn chia sẻ qua kho tài liệu nội bộ.
2. Email nghi lừa đảo: dùng nút "Báo cáo lừa đảo" trên Outlook, không bấm liên kết.
