---
doc_id: SVT-CS-007
so_hieu: 04/2026/CS-SVT
tieu_de: Chính sách an toàn thông tin và sử dụng trí tuệ nhân tạo
loai: chinh-sach
phong_ban_so_huu: CNTT
pham_vi_truy_cap: cong-khai
phong_ban_duoc_xem: []
vai_tro_duoc_xem: []
ngay_ban_hanh: 2026-02-20
hieu_luc_tu: 2026-03-01
het_hieu_luc: null
thay_the: null
phien_ban: 1
nguoi_ky: Phạm Đức Long – Tổng Giám đốc
---

# CHÍNH SÁCH AN TOÀN THÔNG TIN VÀ SỬ DỤNG TRÍ TUỆ NHÂN TẠO

## Phần 1. Phân loại thông tin

### Điều 1. Các cấp độ phân loại
| Cấp độ | Định nghĩa | Ví dụ |
|---|---|---|
| Công khai | Được phép công bố ra bên ngoài | Thông cáo báo chí, tin tuyển dụng, tài liệu marketing |
| Nội bộ | Dùng trong Công ty, không gây thiệt hại đáng kể nếu lộ | Nội quy, quy chế nghỉ phép, hướng dẫn CNTT |
| Mật | Lộ ra gây thiệt hại cho Công ty, khách hàng hoặc người lao động | Tiền lương, hồ sơ nhân sự, hợp đồng khách hàng, giá chào thầu, mã nguồn sản phẩm |
| Tuyệt mật | Lộ ra gây thiệt hại nghiêm trọng | Kế hoạch M&A, khóa mã hóa, mật khẩu quản trị hệ thống |

### Điều 2. Trách nhiệm phân loại
Chủ sở hữu tài liệu (phòng ban ban hành) chịu trách nhiệm gán cấp độ khi tạo tài liệu. Tài liệu chưa được gán cấp độ được xem là **Nội bộ**.

## Phần 2. Tài khoản và mật khẩu

### Điều 3. Mật khẩu và xác thực
1. Mật khẩu tối thiểu **12 ký tự**, không trùng với 5 mật khẩu gần nhất.
2. Xác thực đa yếu tố (MFA) **bắt buộc** cho email, VPN và mọi hệ thống chứa thông tin Mật.
3. Không bắt buộc đổi mật khẩu định kỳ; phải đổi ngay khi nghi ngờ bị lộ.
4. Tuyệt đối không cung cấp mật khẩu cho bất kỳ ai, kể cả người tự xưng là nhân viên CNTT. Phòng CNTT không bao giờ hỏi mật khẩu của người dùng.

## Phần 3. Sử dụng trí tuệ nhân tạo (AI)

### Điều 4. Công cụ AI được phê duyệt
1. Công cụ AI được phê duyệt sử dụng với dữ liệu Công ty là **Trợ lý số SVT** (chat.saoviet.example) và các công cụ khác có trong danh mục do Phòng CNTT công bố.
2. Sử dụng công cụ AI công cộng (miễn phí, cá nhân) chỉ được phép với thông tin **Công khai**.

### Điều 5. Quy tắc dữ liệu khi dùng AI
| Cấp độ thông tin | Trợ lý số SVT (model cloud) | Trợ lý số SVT (model nội bộ on-prem) | Công cụ AI công cộng |
|---|---|---|---|
| Công khai | Được phép | Được phép | Được phép |
| Nội bộ | Được phép | Được phép | **Không** |
| Mật | **Không** | Được phép | **Không** |
| Tuyệt mật | **Không** | **Không** | **Không** |

### Điều 6. Trách nhiệm với kết quả do AI tạo ra
1. Người sử dụng chịu trách nhiệm kiểm tra tính chính xác của kết quả do AI tạo ra trước khi sử dụng.
2. Văn bản gửi ra bên ngoài (khách hàng, cơ quan nhà nước) có sử dụng AI hỗ trợ soạn thảo phải được người có thẩm quyền rà soát trước khi phát hành.
3. Không sử dụng AI để ra quyết định cuối cùng về tuyển dụng, kỷ luật, đánh giá nhân sự.

### Điều 7. Trợ lý AI có khả năng thực hiện hành động
1. Trợ lý AI chỉ được thực hiện hành động thay đổi dữ liệu (tạo đơn, gửi email, cập nhật hệ thống) sau khi người dùng xác nhận.
2. Trợ lý AI chỉ được truy cập dữ liệu trong phạm vi quyền của người dùng đang sử dụng.
3. Mọi lần trợ lý AI truy cập dữ liệu Mật phải được ghi nhật ký và lưu tối thiểu **12 tháng**.

## Phần 4. Sự cố an toàn thông tin

### Điều 8. Báo cáo sự cố
1. Người lao động phát hiện sự cố (mất thiết bị, email lừa đảo, nghi lộ dữ liệu, AI trả lời chứa thông tin không được phép) phải báo trong vòng **01 giờ** qua email security@saoviet.example hoặc số máy lẻ **1999**.
2. Không tự ý xóa bằng chứng (email, tệp, lịch sử chat) trước khi Phòng CNTT xác nhận.
