# Transcript họp tiến độ dự án PNC Portal – thứ Ba 17/11/2026, 14:00

> Bản gỡ băng tự động (giả lập), chưa biên tập: có từ đệm, nói chen, nhận dạng sai vài từ. Dùng làm đầu vào cho mini-app biên bản họp khi chưa làm phần speech-to-text.
> Người tham gia: Hoàng Minh Đức (PM), Trịnh Văn Sơn (Tech lead), Mai Thị Ngọc (BA), Phan Văn Lộc (Tester), Đặng Thị Yến (PNC, qua điện thoại – tín hiệu chập chờn).

[00:00:05] **Đức:** Ok mọi người vào đủ chưa nhỉ, chị Yến nghe rõ không ạ?
[00:00:09] **Yến:** Chị nghe… hơi rè nhưng được em ạ.
[00:00:12] **Đức:** Dạ vâng. Hôm nay mình chốt mấy việc trước UAT nhé. UAT theo kế hoạch là xong ngày 15 tháng 11 nhưng mình đang chậm, Lộc báo tình hình đi em.
[00:00:25] **Lộc:** Dạ, tổng cộng có 214 test case, đã chạy 180, còn 34. Có 11 lỗi mở, trong đó 3 lỗi mức cao. Một lỗi là thanh toán qua ví điện tử bị trừ tiền hai lần khi khách bấm lại nút, hai lỗi kia là hiển thị hóa đơn sai kỳ khi khách có hai hợp đồng điện.
[00:00:48] **Sơn:** Lỗi trừ tiền hai lần là do mình chưa có idempotency key khi gọi cổng thanh toán, bên em sửa được, chắc thứ Năm này xong.
[00:00:57] **Đức:** Thứ Năm là 19 nhé. Anh Sơn nhận lỗi này.
[00:01:02] **Sơn:** Ừ anh nhận, hạn 19/11.
[00:01:05] **Ngọc:** Lỗi hóa đơn hai hợp đồng thì em nghĩ là do API hóa đơn bên PNC trả về không có mã hợp đồng ạ, chị Yến ơi bên chị có thêm trường đó được không ạ?
[00:01:15] **Yến:** Cái này… chị phải hỏi bên vendor hệ thống hóa đơn, chị chưa hứa được. Chị sẽ trả lời trong tuần này.
[00:01:24] **Đức:** Vậy ghi là chị Yến phản hồi trước thứ Sáu 20/11 nhé chị. Nếu không thêm được thì mình phương án B là gọi thêm API hợp đồng rồi ghép bên mình, Ngọc ước lượng giúp anh phương án B.
[00:01:38] **Ngọc:** Dạ em ước lượng xong trong ngày mai, 18 ạ.
[00:01:42] **Đức:** Ok. Thế UAT lùi đến 27/11 được không mọi người? Go-live vẫn giữ 1/12.
[00:01:50] **Sơn:** Lùi UAT đến 27 mà go-live vẫn 1/12 thì chỉ còn 2 ngày làm việc để sửa lỗi phát sinh từ UAT, rủi ro lắm anh.
[00:01:58] **Đức:** Anh biết. Chị Yến, bên chị có chấp nhận go-live 8/12 không ạ?
[00:02:04] **Yến:** Chị không quyết được, phải anh Phúc. Nhưng mà… chị nghĩ anh Phúc muốn giữ 1/12 vì đã thông báo khách hàng rồi.
[00:02:12] **Đức:** Vậy thế này: UAT lùi đến 27/11 – chốt. Còn ngày go-live thì anh sẽ gửi email đề xuất anh Phúc hai phương án, 1/12 với điều kiện chỉ go-live tính năng tra cứu và thanh toán, còn yêu cầu sửa chữa đẩy sang 8/12. Anh gửi trong hôm nay.
[00:02:30] **Lộc:** Em cần thêm môi trường UAT thứ hai anh ạ, chạy song song cho kịp.
[00:02:35] **Sơn:** Môi trường thì bên anh dựng được, nhưng cần dữ liệu ẩn danh mới từ PNC, dữ liệu cũ hết hạn rồi.
[00:02:41] **Yến:** Ừ, chị gửi bộ dữ liệu ẩn danh mới, chậm nhất thứ Hai 23.
[00:02:46] **Đức:** Ok. À còn vụ nhà cung cấp SMS OTP, chị Yến chốt chưa ạ?
[00:02:51] **Yến:** Chốt rồi em, bên chị chọn bên Tín Hiệu Việt (giả lập), hợp đồng ký tuần trước rồi.
[00:02:57] **Đức:** Tuyệt, vậy vấn đề này đóng. Còn câu hỏi lưu log truy cập bao lâu thì pháp chế bên chị trả lời chưa?
[00:03:04] **Yến:** Chưa em, vẫn đang chờ.
[00:03:07] **Đức:** Dạ, vậy vẫn để mở. Mọi người còn gì không? Không thì mình kết thúc, cảm ơn cả nhà.
[00:03:13] **Lộc:** À anh ơi, em xin nghỉ chiều thứ Sáu nhé, em đã xin trên HRM rồi.
[00:03:17] **Đức:** Ok em, anh duyệt rồi.
