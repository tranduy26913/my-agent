# Quy trình chuẩn hóa công việc doanh nghiệp theo hướng tự động hóa với AI Agent

> **Mục đích:** một phương pháp từng bước để đưa một doanh nghiệp từ "công việc làm theo thói quen, mỗi người một kiểu" đến "quy trình chuẩn, có dữ liệu, có điểm kiểm soát, và được AI Agent thực hiện một phần hoặc toàn bộ một cách an toàn, đo được".
>
> **Đối tượng:** AI Agent Engineer, trưởng nhóm chuyển đổi số, chủ quy trình ở các phòng ban, Ban Giám đốc.
>
> **Ví dụ xuyên suốt:** Công ty SVT (hư cấu, `data/README.md`) với hai quy trình: **(A) Trả lời câu hỏi nghỉ phép** của Phòng HCNS và **(B) Kiểm tra phiếu công tác phí** của Phòng TCKT.

---

## Mục lục
1. [Nguyên tắc nền tảng](#1-nguyên-tắc-nền-tảng)
2. [Tổng quan lộ trình 9 giai đoạn](#2-tổng-quan-lộ-trình-9-giai-đoạn)
3. [G0 – Khởi động và thiết lập quản trị](#g0--khởi-động-và-thiết-lập-quản-trị)
4. [G1 – Khảo sát và lập danh mục quy trình](#g1--khảo-sát-và-lập-danh-mục-quy-trình)
5. [G2 – Đánh giá và ưu tiên](#g2--đánh-giá-và-ưu-tiên)
6. [G3 – Chuẩn hóa quy trình](#g3--chuẩn-hóa-quy-trình)
7. [G4 – Thiết kế giải pháp Agent](#g4--thiết-kế-giải-pháp-agent)
8. [G5 – Chuẩn bị dữ liệu, tích hợp và xây dựng](#g5--chuẩn-bị-dữ-liệu-tích-hợp-và-xây-dựng)
9. [G6 – Kiểm thử, đánh giá và thí điểm (pilot)](#g6--kiểm-thử-đánh-giá-và-thí-điểm-pilot)
10. [G7 – Triển khai mở rộng và quản lý thay đổi](#g7--triển-khai-mở-rộng-và-quản-lý-thay-đổi)
11. [G8 – Vận hành, đo lường và cải tiến liên tục](#g8--vận-hành-đo-lường-và-cải-tiến-liên-tục)
12. [Thang mức độ tự động hóa và ma trận người duyệt](#12-thang-mức-độ-tự-động-hóa-và-ma-trận-người-duyệt)
13. [Mô hình tổ chức và vai trò](#13-mô-hình-tổ-chức-và-vai-trò)
14. [Bộ biểu mẫu M1–M15](#14-bộ-biểu-mẫu-m1m15)
15. [Sai lầm thường gặp](#15-sai-lầm-thường-gặp)
16. [Dùng tài liệu này khi phỏng vấn](#16-dùng-tài-liệu-này-khi-phỏng-vấn)

---

## 1. Nguyên tắc nền tảng

| # | Nguyên tắc | Ý nghĩa thực tế |
|---|---|---|
| 1 | **Chuẩn hóa trước, tự động hóa sau** | Tự động hóa một quy trình hỗn loạn chỉ tạo ra hỗn loạn nhanh hơn. Nếu 3 người làm 3 kiểu, agent không biết làm theo kiểu nào. |
| 2 | **Đơn giản nhất chạy được** | Ưu tiên: bỏ bước thừa → biểu mẫu/quy tắc → tự động hóa tất định (code, RPA) → LLM một bước → workflow nhiều bước có LLM → agent tự chủ. Chỉ leo bậc khi bậc dưới không đủ. |
| 3 | **Tách phần tất định và phần cần phán đoán** | Định mức, hạn mức, phép tính → code. Đọc hiểu văn bản tự do, phân loại, tóm tắt, soạn thảo → LLM. Quyết định có hệ quả pháp lý/con người → người. |
| 4 | **Một nguồn sự thật** | Mỗi loại dữ liệu/quy định có một chủ sở hữu và một nơi lưu chính thức. Agent đọc từ đó, không từ bản sao. |
| 5 | **Quyền đi theo người dùng** | Agent không bao giờ làm được nhiều hơn quyền của người đang ra lệnh. Kiểm soát đặt trong hệ thống, không đặt trong prompt. |
| 6 | **Con người chịu trách nhiệm cuối cùng** | Mỗi quy trình có chủ sở hữu nghiệp vụ. AI hỗ trợ, gắn cờ, đề xuất; người quyết ở các điểm có rủi ro. |
| 7 | **Đo được trước khi làm** | Không có số liệu nền (baseline) thì không chứng minh được giá trị và không biết khi nào hệ thống tệ đi. |
| 8 | **Lặp nhỏ, mở rộng dần** | Pilot một quy trình, một nhóm người dùng, đo, rồi mới mở rộng. |
| 9 | **Tri thức tích lũy thành tài sản** | Mỗi lần chạy sinh dữ liệu (ngoại lệ, bài học) → cập nhật SOP, kỹ năng (skill), bộ eval. |

---

## 2. Tổng quan lộ trình 9 giai đoạn

```
 G0 Khởi động & quản trị ─► G1 Khảo sát ─► G2 Ưu tiên ─► G3 Chuẩn hóa ─► G4 Thiết kế Agent
                                                                              │
 G8 Vận hành & cải tiến ◄─ G7 Mở rộng ◄─ G6 Kiểm thử & Pilot ◄─ G5 Dữ liệu, tích hợp, xây dựng
        │
        └──► phản hồi ngược về G1 (quy trình mới) và G3 (cập nhật SOP)
```

| Giai đoạn | Thời lượng gợi ý (đợt đầu) | Đầu ra chính | Cổng kiểm soát |
|---|---|---|---|
| G0 Khởi động | 1–2 tuần | Điều lệ chương trình, nhóm quản trị, chính sách AI | Ban Giám đốc phê duyệt |
| G1 Khảo sát | 1–2 tuần | Danh mục quy trình (M1), Process Canvas (M4) | Đủ dữ liệu để chấm điểm |
| G2 Ưu tiên | 1 tuần | Ma trận chấm điểm (M3), business case (M15) | Chọn 1–3 quy trình pilot |
| G3 Chuẩn hóa | 2–3 tuần | SOP sẵn sàng cho agent (M5), bảng quy tắc (M6), danh mục ngoại lệ (M7) | Chủ quy trình ký duyệt SOP |
| G4 Thiết kế | 1–2 tuần | Agent Spec Card (M8), kiến trúc, mô hình rủi ro | Review bảo mật & kiến trúc |
| G5 Xây dựng | 2–4 tuần | Dữ liệu sẵn sàng (M9), tool/MCP, agent, bộ eval (M10) | Đạt ngưỡng eval offline |
| G6 Pilot | 3–6 tuần | Kết quả pilot (M11), số liệu so baseline | Quyết định Go / Điều chỉnh / Dừng |
| G7 Mở rộng | Liên tục theo đợt | Kế hoạch triển khai, đào tạo, hỗ trợ | Đạt chỉ số chấp nhận |
| G8 Vận hành | Liên tục | Dashboard (M14), eval hồi quy, cập nhật SOP/kỹ năng | Rà soát định kỳ hằng quý |

> Đợt đầu (pilot) thường 10–14 tuần. Các đợt sau nhanh hơn nhiều vì đã có nền tảng, quản trị và biểu mẫu.

---

## G0 – Khởi động và thiết lập quản trị

**Mục tiêu:** có sự bảo trợ của lãnh đạo, phạm vi rõ ràng, luật chơi về dữ liệu và AI trước khi động vào quy trình nào.

**Đầu vào:** chiến lược công ty, các sáng kiến AI tự phát đang có (shadow AI), chính sách bảo mật hiện hành.

### Các bước

**Bước 0.1 – Xác định mục tiêu chương trình bằng con số**
- Ví dụ: "Giảm 30% thời gian xử lý các yêu cầu nội bộ lặp lại trong 6 tháng", "Không có sự cố lộ dữ liệu Mật do AI".
- Tránh mục tiêu kiểu "ứng dụng AI vào mọi phòng ban".

**Bước 0.2 – Lập nhóm quản trị (AI Steering / CoE)**
- Thành phần tối thiểu: lãnh đạo bảo trợ (Sponsor), đại diện CNTT/bảo mật, pháp chế/tuân thủ, đại diện 2–3 phòng nghiệp vụ, AI Agent Engineer.
- Nhịp họp: 2 tuần/lần trong pilot, hằng tháng khi ổn định.

**Bước 0.3 – Ban hành chính sách sử dụng AI** (ví dụ SVT: `data/knowledge/SVT-CS-007`)
- Phân loại dữ liệu và loại model được phép cho từng cấp.
- Công cụ được phê duyệt; cấm dùng công cụ ngoài với dữ liệu nội bộ.
- Trách nhiệm với đầu ra AI; danh sách quyết định **không được** giao cho AI (tuyển dụng, kỷ luật, đánh giá nhân sự…).
- Quy tắc với agent có hành động: xác nhận trước, quyền theo người dùng, nhật ký.

**Bước 0.4 – Chọn nền tảng và kiến trúc tham chiếu**
- Nền tảng chat/agent (ví dụ LibreChat), lớp tích hợp (MCP), kho tri thức, model (cloud/on-prem), đăng nhập (SSO), quan sát (tracing), chi phí.
- Ghi quyết định thành ADR.

**Bước 0.5 – Lập điều lệ chương trình** (1–2 trang): mục tiêu, phạm vi, ngoài phạm vi, nhóm, ngân sách, mốc, chỉ số thành công, rủi ro chính.

**Bước 0.6 – Truyền thông ban đầu**: vì sao làm, AI **hỗ trợ** chứ không thay thế, mời các phòng đề xuất quy trình. Giảm lo ngại sớm sẽ dễ khảo sát hơn.

**Đầu ra:** điều lệ chương trình, danh sách nhóm quản trị, chính sách AI, ADR nền tảng.

**Cổng G0 (đủ điều kiện sang G1):**
- [ ] Có Sponsor cấp Ban Giám đốc và ngân sách đợt đầu.
- [ ] Chính sách AI và phân loại dữ liệu đã ban hành (ít nhất bản tạm thời).
- [ ] Có kênh để các phòng gửi đề xuất quy trình.

---

## G1 – Khảo sát và lập danh mục quy trình

**Mục tiêu:** biết doanh nghiệp đang có những công việc lặp lại nào, tốn bao nhiêu công, đau ở đâu – bằng số liệu, không bằng cảm giác.

### Các bước

**Bước 1.1 – Thu thập danh sách ứng viên**
- Nguồn: đề xuất của phòng ban; ticket helpdesk/email hỏi đáp lặp lại; nhật ký hệ thống (HRM, ERP); phỏng vấn trưởng phòng; quan sát (job shadowing).
- Ghi vào **M1 – Danh mục quy trình**.

**Bước 1.2 – Phỏng vấn khảo sát** (dùng **M2 – Bộ câu hỏi khảo sát**)
- Gặp **cả** người quản lý (biết mục tiêu, ngoại lệ chính sách) **và** người làm hằng ngày (biết thao tác thật, mẹo, đường tắt).
- Hỏi số liệu cụ thể: "tháng trước bao nhiêu?", "lần gần nhất mất bao lâu?" thay vì "thường thì thế nào?".

**Bước 1.3 – Quan sát và thu thập mẫu thật**
- Xin 20–50 mẫu thật (email hỏi, phiếu, hồ sơ) đã ẩn danh. Đây vừa là dữ liệu hiểu quy trình, vừa là nguyên liệu cho bộ eval ở G5.
- Ghi lại cách làm *thực tế* (as-is), kể cả khác với quy định trên giấy.

**Bước 1.4 – Mô tả quy trình hiện tại (as-is)** bằng **M4 – Process Canvas** (SIPOC + bước + số liệu + điểm đau).
- SIPOC: Supplier (ai cung cấp đầu vào) – Input – Process – Output – Customer.
- Vẽ sơ đồ swimlane (làn theo vai trò) nếu có từ 3 vai trò trở lên.

**Bước 1.5 – Đo baseline**
| Chỉ số | Cách đo |
|---|---|
| Khối lượng | số yêu cầu/tháng (từ hệ thống, email, ticket) |
| Thời gian xử lý | phút/yêu cầu (bấm giờ 10–20 mẫu) |
| Thời gian chờ (lead time) | từ lúc yêu cầu đến lúc xong |
| Tỉ lệ lỗi / làm lại | % hồ sơ bị trả lại, sai sót |
| Mức hài lòng | khảo sát nhanh 1–5 |

**Ví dụ SVT**

| | (A) Câu hỏi nghỉ phép | (B) Kiểm tra phiếu công tác phí |
|---|---|---|
| Khối lượng | ~120 câu/tháng | ~80 phiếu/tháng |
| Thời gian | ~8 phút/câu (tra HRM, tra quy chế, trả lời) | ~15 phút/phiếu (gõ lại, đối chiếu định mức) |
| Tổng công | ~16 giờ/tháng | ~20 giờ/tháng |
| Lỗi | ~5% trả lời theo quy chế cũ | ~15% phiếu sai sót, phát hiện muộn |
| Điểm đau | Lặp lại, quy chế mới đổi nhiều | Phiếu là ảnh/scan, quy tắc nhiều, dễ sót |

**Đầu ra:** M1 đã điền cho 10–30 quy trình; M4 cho các quy trình có tiềm năng.

**Cổng G1:** mỗi quy trình ứng viên có đủ số liệu khối lượng, thời gian, chủ sở hữu, dữ liệu đầu vào ở đâu.

---

## G2 – Đánh giá và ưu tiên

**Mục tiêu:** chọn đúng 1–3 quy trình cho pilot: đủ giá trị để đáng làm, đủ khả thi để thành công, đủ an toàn để học.

### Các bước

**Bước 2.1 – Lọc loại trừ (knock-out)** – loại ngay nếu:
- Quy trình sắp thay đổi lớn hoặc sắp bị bỏ.
- Quyết định có hệ quả pháp lý/con người mà chính sách cấm giao cho AI (vẫn có thể làm phần hỗ trợ thông tin).
- Dữ liệu không được phép xử lý bằng công nghệ đang có (ví dụ dữ liệu Tuyệt mật).
- Không có chủ sở hữu nghiệp vụ sẵn sàng tham gia.

**Bước 2.2 – Chấm điểm** bằng **M3 – Ma trận ưu tiên** (thang 1–5, có trọng số):

| Tiêu chí | Trọng số | 1 điểm | 5 điểm |
|---|---|---|---|
| Khối lượng, tần suất | 20% | Vài lần/tháng | Hàng trăm lần/tháng |
| Công sức mỗi lần | 15% | < 2 phút | > 15 phút |
| Mức độ quy tắc rõ ràng | 15% | Toàn phán đoán cảm tính | Quy tắc viết được thành văn |
| Dữ liệu số hóa, truy cập được | 15% | Giấy, rải rác | Có hệ thống/API, có cấu trúc |
| Rủi ro khi sai (đảo chiều) | 15% | Sai gây thiệt hại lớn, không sửa được | Sai dễ phát hiện, dễ sửa |
| Giá trị nghiệp vụ | 10% | Chỉ tiện hơn | Ảnh hưởng doanh thu/tuân thủ/trải nghiệm |
| Mức sẵn sàng của chủ quy trình | 10% | Phản đối | Chủ động đề xuất, có người tham gia |

**Bước 2.3 – Đặt lên ma trận Giá trị × Khả thi**

```
 Giá trị cao │  Chiến lược (làm có kế hoạch)  │  Thắng nhanh (chọn cho pilot) ★
             │────────────────────────────────┼────────────────────────────────
 Giá trị thấp│  Tránh                          │  Lấp chỗ trống (làm khi rảnh)
             └──────── Khả thi thấp ────────────┴──────── Khả thi cao ───────────
```

**Bước 2.4 – Ước lượng business case** bằng **M15**:
- Giờ tiết kiệm/tháng = khối lượng × (thời gian cũ − thời gian mới, gồm cả thời gian người kiểm tra).
- Giá trị khác: giảm lỗi, rút ngắn thời gian chờ, tuân thủ tốt hơn.
- Chi phí: xây dựng (công), vận hành (token, hạ tầng), duy trì (cập nhật tài liệu, eval).
- Thời gian hoàn vốn = chi phí xây dựng / (giá trị ròng mỗi tháng).

**Ví dụ SVT – chấm điểm**

| Tiêu chí (trọng số) | (A) Hỏi nghỉ phép | (B) Phiếu công tác phí | (C) Sàng lọc CV tự động |
|---|---|---|---|
| Khối lượng (20%) | 4 | 3 | 3 |
| Công sức (15%) | 3 | 5 | 4 |
| Quy tắc rõ (15%) | 5 | 5 | 2 |
| Dữ liệu (15%) | 5 | 3 | 3 |
| Rủi ro khi sai (15%) | 4 | 4 | 1 |
| Giá trị (10%) | 3 | 4 | 4 |
| Sẵn sàng (10%) | 5 | 4 | 3 |
| **Tổng có trọng số** | **4,15** | **3,95** | **2,80** |
| Kết luận | Pilot đợt 1 | Pilot đợt 1 (bước người duyệt) | **Loại** phần "loại tự động" theo chính sách; chỉ làm "tóm tắt CV" |

**Đầu ra:** danh sách ưu tiên, business case cho quy trình được chọn, phê duyệt của nhóm quản trị.

**Cổng G2:** Sponsor và chủ quy trình đồng ý phạm vi pilot, chỉ số thành công và ngưỡng dừng.

---

## G3 – Chuẩn hóa quy trình

**Mục tiêu:** biến quy trình as-is thành quy trình chuẩn (to-be) **đủ rõ để một người mới làm đúng ngay lần đầu** – khi đó agent cũng làm được. Đây là giai đoạn quyết định thành bại và thường bị bỏ qua.

### Các bước

**Bước 3.1 – Loại bỏ, đơn giản hóa trước khi tự động hóa (ECRS)**
- **E**liminate – bỏ bước không tạo giá trị (ký duyệt trùng, nhập liệu hai lần).
- **C**ombine – gộp bước do cùng một người làm liên tiếp.
- **R**earrange – đổi thứ tự để kiểm tra sớm (ví dụ kiểm tra hạn quyết toán trước khi đọc chi tiết).
- **S**implify – chuẩn hóa biểu mẫu, bỏ trường không ai dùng.

**Bước 3.2 – Chuẩn hóa đầu vào**
- Mọi yêu cầu vào qua kênh xác định (HRM, form, chat với trợ lý) thay vì email/Zalo tự do.
- Biểu mẫu có cấu trúc, trường bắt buộc, định dạng (ngày `YYYY-MM-DD`, số tiền số nguyên).
- Định nghĩa **schema** đầu vào ngay ở bước này – nó sẽ là `input_schema` của tool hoặc JSON schema trích xuất sau này.

**Bước 3.3 – Xác định một nguồn sự thật cho từng loại thông tin**

| Thông tin | Nguồn chính thức | Chủ sở hữu | Agent truy cập bằng |
|---|---|---|---|
| Số dư phép | HRM | HCNS | Tool `get_leave_balance` (hr-mcp) |
| Quy chế nghỉ phép | Quy chế 01/2026/QĐ-SVT | HCNS | Kho tri thức (knowledge-mcp) |
| Định mức công tác phí | Quy định 08/2025/QĐ-SVT | TCKT | **Bảng tham số trong code** + kho tri thức để trích dẫn |

**Bước 3.4 – Viết quy tắc quyết định thành bảng** (**M6 – Decision table**)
- Mọi "nếu… thì…" trong đầu người làm phải viết ra. Ví dụ phiếu công tác phí:

| Điều kiện | Kết quả | Nguồn |
|---|---|---|
| Khách sạn ở HN/HCM/ĐN > 1.200.000 đ/đêm và cấp < L5 | Vượt định mức – gắn cờ | QĐ 08/2025 Điều 5 |
| Khách sạn ở HN/HCM/ĐN > 1.560.000 đ/đêm và cấp ≥ L5 | Vượt định mức – gắn cờ | Điều 5 khoản 3 |
| Taxi > 500.000 đ × số ngày | Vượt định mức – gắn cờ | Điều 4 khoản 4 |
| Ngày lập − ngày về > 7 ngày làm việc | Quá hạn quyết toán – gắn cờ | Điều 7 khoản 1 |
| Khoản có hóa đơn = Không (trừ phụ cấp lưu trú) | Thiếu chứng từ – gắn cờ | Điều 7 khoản 2 |
| Tổng ≤ 20 triệu | Người duyệt: Kế toán trưởng | Điều 8 |
| Tổng > 20 triệu | Người duyệt: Giám đốc Tài chính | Điều 8 |

**Bước 3.5 – Lập danh mục ngoại lệ** (**M7**)
- Ngoại lệ là nơi tự động hóa thất bại. Với mỗi ngoại lệ ghi: tần suất, cách nhận biết, cách xử lý, ai quyết.
- Quy tắc ngón tay cái: nếu > 20% trường hợp là ngoại lệ, quy trình chưa đủ chuẩn để tự động hóa sâu – quay lại 3.1.

**Bước 3.6 – Phân rã từng bước và gắn nhãn "ai/cái gì làm"**

Mỗi bước của quy trình to-be được gắn một nhãn:

| Nhãn | Dùng khi | Ví dụ |
|---|---|---|
| **[NGƯỜI]** | Cần phán đoán có trách nhiệm, quyết định có hệ quả, ngoại lệ hiếm | Duyệt chi vượt định mức |
| **[CODE]** | Quy tắc rõ, tính toán, tra cứu có cấu trúc, gọi API | So khớp định mức, tính ngày làm việc |
| **[LLM]** | Hiểu/tạo ngôn ngữ ở một bước cố định (trích xuất, phân loại, tóm tắt, soạn thảo) | Đọc ảnh phiếu → JSON; soạn câu trả lời có trích dẫn |
| **[AGENT]** | Số bước và thứ tự phụ thuộc tình huống, cần tự chọn công cụ | Trả lời câu hỏi mở cần tra nhiều nguồn |

> Nếu hầu hết các bước là [CODE] và [LLM] theo thứ tự cố định → đây là **workflow**, không cần agent. Đó là tin tốt: rẻ hơn, ổn định hơn, dễ kiểm toán hơn.

**Bước 3.7 – Viết SOP sẵn sàng cho agent** (**M5**)
Khác SOP truyền thống ở chỗ mỗi bước có: đầu vào/đầu ra có cấu trúc, công cụ cần, quyền cần, điều kiện chuyển người, cách xử lý khi lỗi, và tiêu chí "xong". SOP này về sau có thể chuyển gần như nguyên văn thành `SKILL.md` cho agent.

**Bước 3.8 – Định nghĩa chỉ số và SLA của quy trình to-be**
Thời gian xử lý mục tiêu, tỉ lệ tự động trọn vẹn (straight-through), tỉ lệ chuyển người, tỉ lệ lỗi chấp nhận được.

**Bước 3.9 – Chủ quy trình ký duyệt SOP**, ban hành chính thức (thay đổi quy trình là quyết định quản lý, không phải quyết định kỹ thuật).

**Đầu ra:** M5, M6, M7 đã duyệt; sơ đồ to-be; schema đầu vào/đầu ra.

**Cổng G3:**
- [ ] Một người mới đọc SOP xử lý đúng ≥ 90% mẫu thật (thử với 10 mẫu).
- [ ] Mọi quy tắc có nguồn (Điều/khoản văn bản).
- [ ] Ngoại lệ phổ biến đều có cách xử lý.
- [ ] Chủ quy trình đã ký.

---

## G4 – Thiết kế giải pháp Agent

**Mục tiêu:** từ SOP chuẩn, thiết kế giải pháp kỹ thuật **ở mức tự động hóa phù hợp**, an toàn theo thiết kế.

### Các bước

**Bước 4.1 – Chọn mức tự động hóa mục tiêu** (xem [mục 12](#12-thang-mức-độ-tự-động-hóa-và-ma-trận-người-duyệt)). Pilot nên bắt đầu thấp hơn mục tiêu một bậc.
- (A) Hỏi nghỉ phép: **L1–L2** (trả lời thông tin, có trích dẫn; số liệu cá nhân lấy trực tiếp từ HRM).
- (B) Phiếu công tác phí: **L3** (agent đọc, đối chiếu, gắn cờ; kế toán duyệt).

**Bước 4.2 – Chọn mẫu kiến trúc**

| Đặc điểm quy trình | Mẫu phù hợp |
|---|---|
| Bước cố định, LLM ở 1–2 bước | Workflow / prompt chaining |
| Nhiều loại yêu cầu khác nhau | Routing → nhánh chuyên biệt |
| Câu hỏi mở, cần tra nhiều nguồn | Agent (ReAct) với bộ tool hẹp |
| Việc lớn chia được thành phần độc lập | Orchestrator–workers / sub-agent |
| Đầu ra cần đạt chuẩn chất lượng | Evaluator–optimizer |

- (A) → agent nhỏ với 3 tool: `search_knowledge`, `get_leave_balance`, `get_leave_requests`.
- (B) → workflow: `OCR` → `[LLM] trích xuất JSON` → `[CODE] validate schema` → `[CODE] áp bảng quy tắc M6` → `[LLM] viết giải thích có trích dẫn` → `[NGƯỜI] kế toán duyệt`.

**Bước 4.3 – Thiết kế tool / MCP server**
- Tool theo **nhiệm vụ**, không theo bảng dữ liệu; tên có namespace; mô tả nói khi nào dùng/không dùng; schema chặt; lỗi có hướng dẫn sửa.
- Tách server đọc và server ghi; tool ghi luôn qua bước xác nhận.

**Bước 4.4 – Thiết kế danh tính, quyền và nhật ký**
- Danh tính người dùng đi từ SSO → nền tảng → MCP server; server tự kiểm tra quyền.
- Lọc quyền dữ liệu ngay trong truy vấn.
- Nhật ký mức tool: ai, lúc nào, tool gì, tham số, quyết định allow/deny, bản ghi nào.

**Bước 4.5 – Phân tích rủi ro** (**M12**): với mỗi rủi ro (sai thông tin, lộ dữ liệu, injection, hành động sai, chi phí vượt, phụ thuộc nhà cung cấp) ghi xác suất, tác động, biện pháp, người chịu trách nhiệm.

**Bước 4.6 – Chọn model theo dữ liệu và nhiệm vụ**
- Dữ liệu Mật → model on-prem (hoặc chỉ gửi dữ liệu đã lọc).
- Bước đơn giản (phân loại, trích xuất, phản tư) → model nhỏ; suy luận khó → model lớn.

**Bước 4.7 – Thiết kế trải nghiệm người dùng**
- Kênh (web, Teams), cách hiển thị trích dẫn, nút 👍/👎, cách hiển thị "đang chờ duyệt", cách người dùng sửa kết quả (feedback quý nhất).

**Bước 4.8 – Viết Agent Spec Card** (**M8**) – một trang mô tả đầy đủ agent: mục đích, người dùng, mức tự động hóa, tool, quyền, điểm người duyệt, giới hạn, chỉ số, chủ sở hữu.

**Đầu ra:** M8, M12, sơ đồ kiến trúc, ADR.

**Cổng G4:** review kiến trúc và bảo mật thông qua (CNTT/bảo mật ký), chủ quy trình đồng ý điểm người duyệt.

---

## G5 – Chuẩn bị dữ liệu, tích hợp và xây dựng

**Mục tiêu:** dữ liệu sạch và truy cập được, tool chạy đúng, agent đạt ngưỡng chất lượng **offline** trước khi người thật dùng.

### Các bước

**Bước 5.1 – Kiểm tra mức sẵn sàng dữ liệu** (**M9**): đầy đủ, chính xác, cập nhật, có chủ sở hữu, có metadata (phòng ban, quyền, hiệu lực, phiên bản), định dạng xử lý được (scan cần OCR), được phép xử lý theo chính sách.

**Bước 5.2 – Chuẩn bị kho tri thức**: số hóa/OCR, gắn metadata, đánh dấu văn bản hết hiệu lực, loại bản trùng, quét nội dung đáng ngờ (injection) lúc nạp.

**Bước 5.3 – Xây tích hợp**: MCP server/tool với tài khoản dịch vụ quyền tối thiểu (thường read-only), timeout, retry, idempotency cho thao tác ghi.

**Bước 5.4 – Xây bộ eval trước khi tối ưu** (**M10**)
- Từ mẫu thật thu ở G1: 30–100 ca, gồm ca thường, ca ngoại lệ, ca phải từ chối, ca không có thông tin, ca tấn công.
- Chỉ số theo tầng: truy xuất (recall@k), trích xuất (độ chính xác từng trường), quy tắc (đúng/sai cờ), câu trả lời (đúng, bám nguồn, có trích dẫn), hành vi (từ chối đúng), chi phí và độ trễ.
- Ví dụ có sẵn: `data/eval/golden-set.jsonl`, `data/scan/ground-truth.md`.

**Bước 5.5 – Xây agent/workflow**, viết prompt hệ thống từ SOP (M5), đóng gói quy trình thành kỹ năng (`SKILL.md`) nếu dùng lại nhiều nơi.

**Bước 5.6 – Lặp cải tiến theo eval**: đổi một biến mỗi lần (chunking, hybrid, prompt, model), ghi bảng trước/sau.

**Bước 5.7 – Kiểm thử bảo mật**: giả mạo danh tính, vượt quyền, injection qua tài liệu/web, vòng lặp vô hạn, đầu vào cực lớn.

**Đầu ra:** dữ liệu sẵn sàng, tool/agent chạy được, báo cáo eval offline.

**Cổng G5 (ngưỡng ví dụ – thống nhất với chủ quy trình ở G2):**
- [ ] (A) recall@5 ≥ 0,9; câu trả lời đúng ≥ 90%; 100% ca phân quyền đúng; 0 ca làm theo injection.
- [ ] (B) trích xuất đúng ≥ 95% trường; phát hiện cờ vi phạm ≥ 95%; cảnh báo sai ≤ 10%.
- [ ] Không có lỗi bảo mật mức cao chưa xử lý.

---

## G6 – Kiểm thử, đánh giá và thí điểm (pilot)

**Mục tiêu:** chứng minh giá trị trên người dùng thật, trong phạm vi nhỏ, có kiểm soát; quyết định dựa trên số liệu.

### Các bước

**Bước 6.1 – Lập kế hoạch pilot** (**M11**): nhóm người dùng (10–30 người), thời gian (3–6 tuần), chỉ số, ngưỡng thành công, **ngưỡng dừng** (ví dụ: 1 sự cố lộ dữ liệu Mật → dừng ngay), kênh hỗ trợ.

**Bước 6.2 – Chạy song song (shadow mode) 1–2 tuần** nếu rủi ro cao: agent xử lý nhưng kết quả chỉ để so sánh, người vẫn làm như cũ. Với (B): agent gắn cờ, kế toán vẫn kiểm tra tay, đo độ khớp.

**Bước 6.3 – Đào tạo nhóm pilot** 30 phút: làm được gì, không làm được gì, cách báo lỗi, quy tắc dữ liệu.

**Bước 6.4 – Vận hành pilot và thu thập**
- Số liệu tự động: số lượt, tỉ lệ 👍/👎, tỉ lệ chuyển người, thời gian xử lý, chi phí.
- Định tính: phỏng vấn 5 người dùng giữa và cuối pilot.
- Review hằng tuần các ca 👎 và ngoại lệ → sửa → thêm vào bộ eval.

**Bước 6.5 – So sánh với baseline (G1)** và business case (G2).

**Bước 6.6 – Họp quyết định Go / Điều chỉnh / Dừng** với Sponsor và chủ quy trình.

**Ví dụ kết quả pilot (giả định để minh họa cách trình bày)**

| Chỉ số | Baseline | Pilot (B) | Ghi chú |
|---|---|---|---|
| Thời gian/phiếu | 15 phút | 4 phút (kế toán review) | Bao gồm thời gian kiểm tra cờ |
| Sai sót lọt qua | ~15% phát hiện muộn | 2% | Ca lọt: hóa đơn chụp mờ |
| Tỉ lệ phiếu không có cờ, duyệt thẳng | – | 62% | |
| Chi phí vận hành | – | ~6 USD/tháng | 80 phiếu × OCR on-prem + 2 lần gọi LLM |

**Đầu ra:** báo cáo pilot, danh sách cải tiến, quyết định.

**Cổng G6:** đạt ngưỡng thành công, không chạm ngưỡng dừng, chủ quy trình đồng ý mở rộng.

---

## G7 – Triển khai mở rộng và quản lý thay đổi

**Mục tiêu:** đưa giải pháp đến toàn bộ người dùng mục tiêu và làm cho họ **thực sự dùng**.

### Các bước

**Bước 7.1 – Kế hoạch triển khai theo đợt**: theo phòng ban hoặc chi nhánh; mỗi đợt có người hỗ trợ tại chỗ (champion).

**Bước 7.2 – Quản lý thay đổi (mô hình ADKAR)**
| Yếu tố | Hành động |
|---|---|
| Awareness – hiểu vì sao | Thông báo từ lãnh đạo, chia sẻ số liệu pilot |
| Desire – muốn dùng | Nêu lợi ích cho chính người dùng (bớt việc lặp), cam kết không dùng số liệu để đánh giá cá nhân |
| Knowledge – biết cách | Hướng dẫn 1 trang, video 3 phút, prompt mẫu trong thư viện |
| Ability – làm được | Champion mỗi phòng, giờ hỗ trợ trực tiếp tuần đầu |
| Reinforcement – duy trì | Chia sẻ câu chuyện thành công, đưa vào quy trình chính thức (bỏ kênh cũ) |

**Bước 7.3 – Cập nhật quy trình chính thức**: SOP mới thay SOP cũ; kênh cũ (email hỏi HCNS) chuyển hướng sang trợ lý; mô tả công việc thay đổi nếu cần.

**Bước 7.4 – Thiết lập hỗ trợ và vận hành**: runbook, người trực, SLA hỗ trợ, quy trình xử lý sự cố, quy trình cập nhật tài liệu nguồn.

**Bước 7.5 – Bàn giao vận hành** cho chủ quy trình (nội dung) và CNTT (hạ tầng); AI Engineer chuyển sang quy trình tiếp theo.

**Cổng G7:** tỉ lệ sử dụng đạt mục tiêu (ví dụ ≥ 60% người dùng mục tiêu hoạt động hằng tuần), hài lòng ≥ 4/5, có người chịu trách nhiệm vận hành.

---

## G8 – Vận hành, đo lường và cải tiến liên tục

**Mục tiêu:** giữ chất lượng khi dữ liệu, quy định, model thay đổi; biến kinh nghiệm thành tài sản dùng chung.

### Các hoạt động định kỳ

| Tần suất | Hoạt động |
|---|---|
| Hằng ngày | Cảnh báo tự động: lỗi tool, độ trễ, chi phí vượt ngưỡng |
| Hằng tuần | Review ca 👎, ca chuyển người, ngoại lệ mới → cập nhật SOP/eval/kỹ năng |
| Mỗi lần thay đổi | Đổi prompt, model, cách chunk, tài liệu nguồn → chạy eval hồi quy trong CI |
| Hằng tháng | Dashboard (**M14**): sử dụng, chất lượng, chi phí theo phòng ban, giờ tiết kiệm |
| Hằng quý | Rà soát quyền truy cập, kỹ năng hết hạn, tài liệu hết hiệu lực, business case thực tế; chọn đợt quy trình tiếp theo |

### Vòng tích lũy tri thức

```
Ca thực tế → trace → phản tư tự động → kinh nghiệm (phạm vi nhóm)
   → đủ bằng chứng → đề xuất cập nhật SOP / kỹ năng mới
   → chủ quy trình duyệt → xuất bản phiên bản mới → eval hồi quy → dùng toàn tổ chức
```

Kiểm soát: bài học không chứa dữ liệu cá nhân; không tự xuất bản toàn tổ chức; mỗi kỹ năng có chủ sở hữu, phiên bản, ngày rà soát, liên kết tài liệu nguồn (xem `01-chuyen-nganh/05-skills-va-experience-memory.md`).

### Khi nào nâng mức tự động hóa
Chỉ nâng một bậc (ví dụ L3 → L4) khi đủ cả ba: (1) 3 tháng liên tiếp đạt ngưỡng chất lượng; (2) tỉ lệ người duyệt sửa kết quả của agent < 2%; (3) chủ quy trình và bảo mật đồng ý, có cơ chế kiểm tra mẫu ngẫu nhiên thay cho duyệt từng ca.

---

## 12. Thang mức độ tự động hóa và ma trận người duyệt

### 12.1 Thang L0–L5

| Mức | Tên | Agent làm | Người làm | Ví dụ SVT |
|---|---|---|---|---|
| L0 | Thủ công | – | Toàn bộ | Hiện trạng |
| L1 | Hỗ trợ thông tin | Tra cứu, trả lời có trích dẫn | Tự quyết và tự làm | Hỏi quy chế nghỉ phép |
| L2 | Soạn nháp / gợi ý | Soạn email, điền sẵn form, đề xuất | Sửa, bấm gửi | Soạn đơn nghỉ trên HRM cho người dùng bấm nộp |
| L3 | Thực hiện có duyệt | Chuẩn bị hành động trọn vẹn | Duyệt từng ca trước khi thực hiện | Kiểm tra phiếu công tác phí, kế toán duyệt |
| L4 | Tự động có giám sát | Tự thực hiện ca bình thường; ca ngoại lệ chuyển người | Kiểm tra mẫu ngẫu nhiên, xử lý ngoại lệ | Phiếu không có cờ & < 5 triệu được duyệt tự động |
| L5 | Tự chủ | Toàn bộ, kể cả ngoại lệ | Giám sát chỉ số | Hiếm khi phù hợp trong doanh nghiệp |

### 12.2 Ma trận quyết định mức người duyệt

| Tác động khi sai \ Khả năng đảo ngược | Dễ đảo ngược | Khó đảo ngược | Không đảo ngược |
|---|---|---|---|
| **Thấp** (bất tiện nội bộ) | L4 – tự động | L3 – duyệt | L3 – duyệt |
| **Trung bình** (tiền nhỏ, ảnh hưởng một người) | L3 – duyệt | L3 – duyệt | L2 – người thực hiện |
| **Cao** (tiền lớn, pháp lý, dữ liệu Mật, ra bên ngoài) | L2 – người thực hiện | L1–L2 | L1 – chỉ hỗ trợ thông tin |

Ví dụ: gửi email cho khách hàng (ra bên ngoài, không thu hồi được) → tối đa L2. Đặt phòng họp (thấp, dễ hủy) → L3 rồi L4. Chuyển tiền cho nhà cung cấp → L1–L2.

### 12.3 Danh sách hành động luôn cần xác nhận của người
Gửi ra bên ngoài; thay đổi dữ liệu tài chính, nhân sự; xóa; thanh toán; thay đổi quyền truy cập; bất kỳ hành động nào được gợi ý từ nội dung tài liệu/web/email (nguồn không tin cậy).

---

## 13. Mô hình tổ chức và vai trò

| Vai trò | Trách nhiệm |
|---|---|
| Sponsor (Ban Giám đốc) | Mục tiêu, ngân sách, quyết định Go/Dừng, gỡ vướng liên phòng |
| Nhóm quản trị AI (CoE) | Chính sách, tiêu chuẩn, danh mục quy trình, ưu tiên, rà soát rủi ro |
| Chủ quy trình (Process owner) | Nội dung SOP, quy tắc, duyệt ngoại lệ, chấp nhận kết quả, chịu trách nhiệm nghiệp vụ |
| Chuyên gia nghiệp vụ (SME) | Cung cấp mẫu thật, kiểm tra eval, xử lý ca chuyển người |
| AI Agent Engineer | Phân tích, thiết kế, xây tool/agent, eval, tối ưu, vận hành kỹ thuật |
| CNTT / Bảo mật | Hạ tầng, tích hợp, danh tính, review bảo mật, giám sát |
| Pháp chế / Tuân thủ | Dữ liệu cá nhân, hợp đồng nhà cung cấp AI, quyết định không giao cho AI |
| Champion phòng ban | Hỗ trợ đồng nghiệp, thu thập phản hồi |

**RACI theo giai đoạn** (R: thực hiện, A: chịu trách nhiệm cuối, C: tham vấn, I: được thông báo)

| Giai đoạn | Sponsor | CoE | Chủ quy trình | AI Engineer | CNTT/Bảo mật | Pháp chế |
|---|---|---|---|---|---|---|
| G0 Khởi động | A | R | C | C | C | C |
| G1 Khảo sát | I | A | C | R | I | – |
| G2 Ưu tiên | A | R | C | R | C | C |
| G3 Chuẩn hóa | I | C | **A** | R | I | C |
| G4 Thiết kế | I | C | C | **A/R** | C | C |
| G5 Xây dựng | I | I | C | **A/R** | C | – |
| G6 Pilot | A | C | R | R | C | I |
| G7 Mở rộng | A | C | R | C | R | I |
| G8 Vận hành | I | A | R | R | R | I |

---

## 14. Bộ biểu mẫu M1–M15

> Sao chép từng mẫu vào file riêng khi dùng. Ví dụ điền sẵn lấy từ quy trình (B) Kiểm tra phiếu công tác phí.

### M1 – Danh mục quy trình

| Mã | Tên quy trình | Phòng | Chủ quy trình | Khối lượng/tháng | Phút/lần | Hệ thống liên quan | Dữ liệu đầu vào | Điểm đau | Trạng thái |
|---|---|---|---|---|---|---|---|---|---|
| QT-TCKT-05 | Kiểm tra phiếu công tác phí | TCKT | Bùi Văn Tâm | 80 | 15 | HRM, Excel | Ảnh/scan phiếu, hóa đơn | Gõ lại, soi định mức, sót lỗi | Ứng viên |

### M2 – Bộ câu hỏi khảo sát

**Bối cảnh và mục tiêu**
1. Quy trình này phục vụ ai, kết quả cuối là gì?
2. Nếu quy trình chậm/sai thì ai bị ảnh hưởng, thiệt hại gì?

**Khối lượng và thời gian**
3. Tháng trước có bao nhiêu yêu cầu? Tháng cao điểm?
4. Lần gần nhất anh/chị làm mất bao lâu? Phần nào tốn thời gian nhất?
5. Thời gian từ lúc nhận đến lúc xong là bao lâu? Chờ ở đâu?

**Các bước và quy tắc**
6. Mô tả từng bước lần gần nhất anh/chị làm (mở màn hình, làm thật nếu được).
7. Anh/chị dựa vào văn bản/quy định nào? Có điều gì "ai cũng biết" nhưng không viết ra?
8. Những trường hợp nào anh/chị phải hỏi cấp trên?

**Ngoại lệ và lỗi**
9. Kể 3 trường hợp khó nhất gần đây. Bao nhiêu % là trường hợp khó?
10. Lỗi hay gặp là gì? Phát hiện khi nào, bởi ai?

**Dữ liệu và hệ thống**
11. Dữ liệu đầu vào ở đâu, định dạng gì, ai cập nhật?
12. Có dữ liệu nhạy cảm không (lương, cá nhân, khách hàng)?

**Mong muốn và lo ngại**
13. Nếu có trợ lý làm hộ một phần, anh/chị muốn nó làm phần nào? Tuyệt đối không muốn nó làm phần nào?
14. Làm sao anh/chị biết trợ lý đang làm đúng?

### M3 – Ma trận ưu tiên
Xem bảng tiêu chí ở [G2](#g2--đánh-giá-và-ưu-tiên). Công thức: `Điểm = Σ (điểm tiêu chí × trọng số)`. Ngưỡng gợi ý: ≥ 3,8 ứng viên pilot; 3,0–3,8 đưa vào đợt sau; < 3,0 tạm gác.

### M4 – Process Canvas (as-is)

```
Tên quy trình: Kiểm tra phiếu công tác phí            Chủ quy trình: Kế toán trưởng
S – Nhà cung cấp: nhân viên đi công tác, quản lý trực tiếp
I – Đầu vào: phiếu BM-CTP-03 (ảnh/scan), hóa đơn, giấy đề nghị công tác đã duyệt
P – Các bước: nhận phiếu → gõ vào Excel → đối chiếu định mức → kiểm tra hóa đơn → kiểm tra hạn
              → trả lại nếu sai / trình duyệt → thanh toán
O – Đầu ra: phiếu đã kiểm tra + ý kiến; ủy nhiệm chi
C – Khách hàng: nhân viên (nhận tiền), Kế toán trưởng/GĐ Tài chính (duyệt)
Số liệu: 80 phiếu/tháng · 15 phút/phiếu · 15% sai sót · lead time 6 ngày
Điểm đau: gõ lại từ ảnh; nhớ định mức theo cấp bậc và địa điểm; sót hạn quyết toán
Ngoại lệ: phiếu công tác nước ngoài (tỷ giá); đi cùng sếp (định mức khác); hóa đơn mờ
Hệ thống: HRM (giấy đề nghị công tác), Excel, phần mềm kế toán
```

### M5 – SOP sẵn sàng cho agent

```markdown
# SOP: <Tên quy trình> – v<phiên bản>
Chủ quy trình: <tên>   Ngày hiệu lực: <>   Nguồn quy định: <số hiệu, Điều>
Mục tiêu & SLA: <thời gian, tỉ lệ đúng>
Phạm vi: áp dụng cho <>; không áp dụng cho <>

## Đầu vào (schema)
| Trường | Kiểu | Bắt buộc | Nguồn | Kiểm tra |

## Các bước
| # | Bước | Nhãn | Công cụ/Tool | Quyền cần | Đầu ra | Khi lỗi / không chắc chắn | Xong khi |
| 1 | Đọc phiếu → JSON theo schema | [LLM] | ocr_extract | – | JSON | độ tin cậy < 0,8 → chuyển người | JSON hợp lệ |
| 2 | Kiểm tra định mức theo bảng M6 | [CODE] | check_travel_policy | đọc cấp bậc NV | danh sách cờ | thiếu dữ liệu cấp bậc → hỏi HCNS | mọi khoản đã xét |
| 3 | Viết giải thích có trích dẫn Điều | [LLM] | – | – | đoạn giải thích | – | mỗi cờ có trích dẫn |
| 4 | Duyệt | [NGƯỜI] | màn hình duyệt | Kế toán | quyết định | – | có quyết định |

## Ngoại lệ (tham chiếu M7)
## Điểm người duyệt bắt buộc
## Dữ liệu nhạy cảm và quy tắc xử lý
## Chỉ số theo dõi
## Lịch sử thay đổi
```

### M6 – Bảng quy tắc quyết định
| # | Điều kiện (IF) | Kết quả (THEN) | Ưu tiên | Nguồn quy định | Ví dụ kiểm thử |
|---|---|---|---|---|---|
| R1 | loai = khách sạn AND địa điểm ∈ {HN, HCM, ĐN} AND đơn giá > 1.200.000 AND cấp < L5 | Cờ "vượt định mức khách sạn", số tiền vượt = (đơn giá − 1.200.000) × số đêm | Cao | QĐ 08/2025 Điều 5 | Phiếu NV018 → vượt 750.000 |

### M7 – Danh mục ngoại lệ
| Mã | Ngoại lệ | Tần suất | Nhận biết | Xử lý | Người quyết | Tự động hóa được? |
|---|---|---|---|---|---|---|
| EX-01 | Hóa đơn chụp mờ, OCR không đọc được số tiền | 5% | độ tin cậy trường `thanh_tien` < 0,8 | Yêu cầu chụp lại | Kế toán | Có (phát hiện + yêu cầu) |
| EX-02 | Công tác nước ngoài, tiền USD | 3% | `noi_cong_tac` ngoài VN | Quy đổi theo tỷ giá ngày tạm ứng | Kế toán | Một phần |
| EX-03 | Khoản không thuộc công tác phí (tiếp khách) | 4% | phân loại nội dung | Tách sang thủ tục khác | Kế toán | Có (gắn cờ) |

### M8 – Agent Spec Card

```markdown
# Agent: Kiểm tra phiếu công tác phí (travel-expense-checker) – v0.3
Mục đích: giảm thời gian kiểm tra phiếu, phát hiện vi phạm định mức sớm
Người dùng: kế toán thanh toán (TCKT)     Chủ sở hữu nghiệp vụ: Kế toán trưởng
Mức tự động hóa: L3 (mọi kết quả qua kế toán duyệt)
Kiểu: workflow (OCR → LLM trích xuất → code kiểm tra → LLM giải thích → người duyệt)
Model: OCR on-prem; LLM nội bộ cho trích xuất (dữ liệu Nội bộ); không gửi ra ngoài
Tools: ocr_extract (đọc), get_employee_grade (đọc, hr-mcp), check_travel_policy (code), search_knowledge (đọc)
Quyền: chạy với danh tính kế toán; không có tool ghi vào phần mềm kế toán
Điểm người duyệt: mọi phiếu; phiếu có cờ hiển thị nổi bật
Giới hạn đã biết: không xử lý phiếu viết tay; công tác nước ngoài chỉ gắn cờ "cần kiểm tra tỷ giá"
Không được làm: tự duyệt chi; liên hệ nhân viên; sửa số liệu phiếu
Chỉ số: độ chính xác trích xuất ≥ 95%; recall cờ ≥ 95%; cảnh báo sai ≤ 10%; thời gian xử lý < 30 giây/phiếu
Nhật ký: mọi lần chạy (người chạy, phiếu, cờ, quyết định cuối) lưu 12 tháng
Eval: data/scan/ground-truth.md + 50 phiếu lịch sử ẩn danh
Phiên bản & thay đổi: v0.3 thêm quy tắc R5 (hạn quyết toán theo ngày làm việc)
```

### M9 – Checklist sẵn sàng dữ liệu
- [ ] Biết nguồn chính thức và chủ sở hữu của từng loại dữ liệu
- [ ] Dữ liệu cập nhật đến hiện tại; biết tần suất cập nhật
- [ ] Có metadata: phòng ban, phạm vi truy cập, ngày hiệu lực, phiên bản
- [ ] Văn bản hết hiệu lực được đánh dấu
- [ ] Scan/ảnh đã OCR và kiểm tra mẫu chất lượng
- [ ] Có phân loại bảo mật; dữ liệu Mật có cách xử lý riêng
- [ ] Có cách truy cập máy (API/DB view/file) với tài khoản quyền tối thiểu
- [ ] Đã ẩn danh dữ liệu dùng cho eval/kiểm thử
- [ ] Được pháp chế đồng ý nếu có dữ liệu cá nhân

### M10 – Kế hoạch đánh giá (eval)
| Tầng | Chỉ số | Ngưỡng | Bộ dữ liệu | Cách chấm | Tần suất |
|---|---|---|---|---|---|
| Trích xuất | % trường đúng | ≥ 95% | 50 phiếu lịch sử | so khớp tự động | mỗi thay đổi |
| Quy tắc | recall cờ / cảnh báo sai | ≥ 95% / ≤ 10% | 50 phiếu có nhãn | so khớp | mỗi thay đổi |
| Giải thích | có trích dẫn đúng Điều | 100% | 20 phiếu | LLM-as-judge + chấm tay 20% | hằng tuần |
| Bảo mật | ca vượt quyền bị chặn | 100% | 10 ca tấn công | tự động | mỗi thay đổi |
| Vận hành | p95 độ trễ, chi phí/phiếu | < 30 s, < 0,1 USD | log | dashboard | hằng ngày |

### M11 – Kế hoạch pilot
```
Phạm vi: <quy trình, phòng, số người, thời gian>
Mục tiêu & ngưỡng thành công: <chỉ số – ngưỡng>
Ngưỡng dừng: <ví dụ: 1 sự cố lộ dữ liệu Mật; tỉ lệ sai > 10% trong 1 tuần>
Chế độ: shadow (tuần 1–2) → L3 (tuần 3–6)
Hỗ trợ: <kênh, người trực>     Thu thập phản hồi: <👍/👎, phỏng vấn tuần 3 và tuần 6>
Họp review: <hằng tuần, ai tham dự>     Quyết định cuối: <ngày, người quyết>
```

### M12 – Sổ đăng ký rủi ro
| Mã | Rủi ro | Xác suất | Tác động | Biện pháp | Chủ rủi ro | Trạng thái |
|---|---|---|---|---|---|---|
| RK-01 | Trả lời theo quy chế hết hiệu lực | TB | TB | Lọc `het_hieu_luc`; ca kiểm thử Q01–Q03 | AI Engineer | Đã xử lý |
| RK-02 | Lộ thông tin lương qua trợ lý | Thấp | Cao | Lọc quyền ở SQL; audit; eval phân quyền | AI Engineer + Bảo mật | Theo dõi |
| RK-03 | Prompt injection qua tài liệu | TB | Cao | Quét lúc nạp; phân định dữ liệu; không tool ghi; kiểm tra URL đầu ra | AI Engineer | Theo dõi |
| RK-04 | Người dùng tin tuyệt đối vào AI | Cao | TB | Trích dẫn nguồn; đào tạo; L3 cho việc có tiền | Chủ quy trình | Theo dõi |
| RK-05 | Chi phí vượt ngân sách | TB | TB | Balance theo phòng; cảnh báo 80%; routing model | CNTT | Theo dõi |

### M13 – RACI
Xem [mục 13](#13-mô-hình-tổ-chức-và-vai-trò).

### M14 – Dashboard chỉ số
| Nhóm | Chỉ số |
|---|---|
| Sử dụng | Người dùng hoạt động tuần/tháng; lượt dùng theo phòng; tỉ lệ quay lại |
| Chất lượng | 👍/👎; tỉ lệ người duyệt sửa kết quả; điểm eval hồi quy; số ca chuyển người |
| Hiệu quả | Giờ tiết kiệm (ước tính = lượt × phút tiết kiệm); thời gian chờ trung bình; tỉ lệ straight-through |
| Chi phí | Token và USD theo phòng/agent/model; chi phí mỗi lượt; tỉ lệ cache hit |
| An toàn | Số lượt deny; sự cố; ca injection bị chặn; truy cập dữ liệu Mật |

### M15 – Business case

| Hạng mục | (B) Phiếu công tác phí – ước tính |
|---|---|
| Giờ tiết kiệm/tháng | 80 × (15 − 4) phút ≈ 14,7 giờ |
| Giá trị giờ công (giả định 200.000 đ/giờ đã gồm chi phí) | ≈ 2,9 triệu đ/tháng |
| Giá trị giảm sai sót | Ước tính số tiền chi sai tránh được/tháng (lấy từ dữ liệu kiểm toán) |
| Chi phí xây dựng | ~10 ngày công AI Engineer + 2 ngày chủ quy trình |
| Chi phí vận hành | Token + hạ tầng + 2 giờ/tháng review |
| Hoàn vốn | = chi phí xây dựng / (giá trị tháng − chi phí vận hành tháng) |
| Lợi ích khó lượng hóa | Kế toán bớt việc nhàm chán; nhân viên được thanh toán nhanh hơn; dữ liệu chi phí có cấu trúc để phân tích |

> Lưu ý trung thực: quy trình nhỏ có thể hoàn vốn chậm; giá trị thật thường đến từ **nền tảng dùng chung** (danh tính, MCP, kho tri thức, eval) phục vụ nhiều quy trình sau.

---

## 15. Sai lầm thường gặp

| Sai lầm | Hậu quả | Cách tránh |
|---|---|---|
| Tự động hóa quy trình chưa chuẩn hóa | Agent làm "đúng" theo một trong nhiều cách, người dùng mất niềm tin | G3 bắt buộc; cổng "người mới làm đúng 90%" |
| Bắt đầu bằng agent tự chủ | Đắt, khó kiểm soát, khó kiểm toán | Thang L0–L5; workflow trước |
| Để LLM áp quy tắc số học/định mức | Sai không tất định | Quy tắc → code; LLM chỉ đọc và giải thích |
| Không đo baseline | Không chứng minh được giá trị | G1 bước 1.5 |
| Không có bộ eval | Mỗi lần sửa lại hỏng chỗ khác | M10 trước khi tối ưu |
| Đặt kiểm soát quyền trong prompt | Bị vượt bằng injection | Quyền kiểm tra trong MCP server/SQL |
| Bỏ quên ngoại lệ | Pilot đẹp, vận hành thật vỡ | M7; ngưỡng 20% ngoại lệ |
| Chủ quy trình đứng ngoài | Không ai chịu trách nhiệm nội dung | RACI: chủ quy trình là A ở G3 |
| Không có kế hoạch cập nhật tài liệu | Trả lời theo quy định cũ | Quy trình xuất bản tài liệu; cờ "cần rà soát" cho kỹ năng liên quan |
| Đo "số câu hỏi" thay vì kết quả nghiệp vụ | Tối ưu sai mục tiêu | Chỉ số giờ tiết kiệm, lỗi giảm, thời gian chờ |
| Chạy song song kênh cũ vĩnh viễn | Không ai đổi thói quen | G7 bước 7.3: chuyển hướng kênh cũ |

---

## 16. Dùng tài liệu này khi phỏng vấn

Câu hỏi trong kế hoạch: *"Phòng Nhân sự muốn tự động hóa; bạn làm việc với họ thế nào để chọn bài toán?"* – trả lời theo khung 2 phút:

1. **Khảo sát có số liệu** (G1): gặp cả trưởng phòng và người làm, lấy mẫu thật, đo khối lượng × thời gian × tỉ lệ lỗi.
2. **Chấm điểm và chọn** (G2): giá trị × khả thi × rủi ro; loại những gì chính sách không cho giao AI; chọn thắng nhanh rủi ro thấp.
3. **Chuẩn hóa trước** (G3): quy tắc thành bảng, ngoại lệ thành danh mục, tách phần code/LLM/người.
4. **Mức tự động hóa phù hợp** (G4): bắt đầu L1–L3, người duyệt ở điểm rủi ro, quyền theo người dùng.
5. **Eval và pilot** (G5–G6): ngưỡng thống nhất từ đầu, shadow mode, so baseline, quyết định bằng số liệu.
6. **Mở rộng và duy trì** (G7–G8): quản lý thay đổi, dashboard, eval hồi quy, tri thức tích lũy thành kỹ năng có người duyệt.

Câu hỏi *"Bài toán nào không nên dùng AI agent?"*: quy trình chưa chuẩn hóa; quy tắc tất định đã viết được bằng code; khối lượng quá nhỏ; sai không thể đảo ngược và không có người duyệt; quyết định về con người (tuyển dụng, kỷ luật); dữ liệu không được phép xử lý; khi một biểu mẫu tốt hơn hoặc bỏ bước giải quyết được vấn đề.
