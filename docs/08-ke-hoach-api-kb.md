# Kế hoạch làm API `/api/kb` (backend cho trang Kho tri thức)

- Giao diện đã có: `kb-admin/src/features/kb/`. Hợp đồng endpoint nằm ở đầu `api/http.ts`, kiểu dữ liệu ở `types.ts`.
- Quyết định liên quan: ADR-001 (phân quyền tài liệu), ADR-004 (portal, BFF, ngoại lệ cho admin xem tài liệu Mật), ADR-005 (khung FastAPI dùng chung).
- Kế hoạch này **không phụ thuộc** Zitadel. Làm trước bằng JWT cũ; xác thực chỉ đổi ở `app/api/deps.py` (docs/06, giai đoạn 4).

## Hiện trạng (2026-11-23)

Session OCR đã dựng khung dùng chung:
- `app/main.py`: `create_app()` gắn các router. Không bật CORS, vì portal gọi qua BFF.
- `app/api/deps.py`: điểm nối xác thực duy nhất. Hiện có `get_current_user`, `require_roles`, `get_db`.
- `app/api/health.py`: `/healthz`, `/readyz`.
- `app/api/ocr.py`: khuôn mẫu cho một router. Router chỉ nhận request, kiểm quyền, gọi service và ghi audit; schema Pydantic khai báo ngay trong file router.

`/api/kb` theo đúng khuôn đó: router mới, gắn vào `main.py` bằng **một dòng**, không sửa các file của OCR.

## Hợp đồng (giữ đúng `http.ts`)

| Method | Đường dẫn | Trả về |
|---|---|---|
| GET | `/documents` | `KbDocument[]` |
| GET | `/documents/{docId}` | `KbDocumentDetail` |
| POST | `/documents` (multipart: `file`, `meta?` là chuỗi JSON) | `KbDocument` |
| POST | `/documents:reindex` `{docIds}` | 204 |
| PUT | `/documents/{docId}/quarantine` `{on}` | 204 |
| POST | `/documents:delete` `{docIds}` | 204 |
| GET | `/documents/{docId}/access?email=` | `AccessCheck` |

JSON dùng **camelCase** như trong `types.ts`, còn Python dùng snake_case. Dùng `alias_generator=to_camel`, `populate_by_name=True`, và trả về `by_alias`.

## Backend đang thiếu những gì

| Frontend cần | Backend đang có | Cách xử lý |
|---|---|---|
| `status`: ready / processing / error / quarantined | Chỉ có cột `quarantined` | Suy ra: `quarantined` → "quarantined", còn lại → "ready". Chưa thêm cột |
| `history[]` | Bảng `audit_logs` (`event`, `detail` dạng JSONB) | Ghi các sự kiện `kb_upload`, `kb_reindex`, `kb_quarantine`, `kb_delete`, `kb_view_classified`, kèm `detail.doc_id` |
| `reindex` | `ingest_markdown(path)` nạp lại được | **Tệp upload không lưu bản gốc**, nên phải lưu file vào `settings.upload_dir` |
| Upload kèm `meta` (docType, classified, effectiveFrom, supersedes) | `ingest_document()` không nhận các trường này | Mở rộng ở tầng service mới. **Không sửa `ingest.py`** khi session OCR còn chạy; nếu buộc phải sửa thì báo người dùng trước |
| Upload `.md` có frontmatter | `ingest_markdown` chỉ đọc từ đường dẫn | Lưu file trước rồi gọi `ingest_markdown(path)` với đường dẫn đã lưu |
| `uploadedBy` là username | `uploaded_by` là khoá ngoại tới `users.id` | Join sang `users` |
| `fileKind` | Không có cột | Suy ra từ đuôi file trong `source` |
| `chunkCount` | | Subquery `count()`, tránh N+1 query |

## Cấu trúc file

```
app/api/kb.py            router + schema Pydantic (theo khuôn app/api/ocr.py)
app/rag/kb_service.py    nghiệp vụ, không phụ thuộc FastAPI -> test được mà không cần HTTP
app/main.py              thêm đúng 1 dòng: app.include_router(kb.router, prefix="/api/kb")
app/config.py            thêm upload_dir (mặc định data/uploads), max_upload_mb
tests/test_kb_api.py, tests/test_kb_service.py
```

## Các bước (mỗi bước xong thì dừng lại cho người dùng xem)

**Bước 1: Schema và hàm chuyển đổi.**
- Viết `to_kb_document(doc, username, chunk_count)`. Mọi trường suy ra (`status`, `fileKind`, `classified`) gom hết vào hàm này.
- Viết test thuần cho hàm này, không cần DB.

**Bước 2: Các endpoint chỉ đọc.**
- `GET /documents`: một query `select(Document, User.username, count chunk)` dùng `outerjoin`.
- `GET /documents/{docId}`:
  - trả chunk sắp theo `ordinal`, và `history` lấy từ `audit_logs` (lọc theo `detail->>'doc_id'`);
  - không tìm thấy thì trả 404;
  - **có ngoại lệ cho tài liệu Mật**, xem mục dưới.
- `GET /documents/{docId}/access?email=`: gọi `load_principal`, rồi `can_read`, rồi kiểm thêm `quarantined` và ngày hiệu lực. `reason` phải nói rõ lý do bằng tiếng Việt, ví dụ không có trong danh bạ, đã nghỉ việc, đang cách ly, chưa đến ngày hoặc đã hết hiệu lực, không thuộc phòng ban hay vai trò được xem. **Dùng lại `can_read`**, không viết lại quy tắc.

**Bước 3: Upload.**
- Lưu bản gốc vào `upload_dir/<sha256>.<ext>`, rồi ghi đường dẫn đó vào `source`.
- Chia nhánh xử lý:
  - file `.md` có frontmatter và `meta` là null: nạp bằng `ingest_markdown`;
  - các trường hợp khác: dùng metadata từ `meta`;
  - file `.md` không có frontmatter mà cũng không có `meta`: trả 422.
- Nếu `doc_id` đã tồn tại thì trả **409**. Không để lỗi IntegrityError nổ thành 500.
- Nếu có `supersedes = X` thì trong **cùng một transaction** gán `X.superseded_by` và `X.effective_to`.
- Giới hạn kích thước file, và so đuôi file với MIME.
- Viết endpoint bằng `def` thường (không `async def`), vì embed và OCR là việc nặng CPU.

**Bước 4: Các thao tác hàng loạt.**
- `reindex`: nạp lại từ `source` với `force=True`. Mỗi tài liệu chạy trong một transaction riêng, để một tài liệu lỗi không chặn cả lô.
- `quarantine`: chỉ đổi giá trị cờ. `retriever.py` đã lọc `quarantined` sẵn rồi.
- `delete`: xoá hẳn. Chunk tự xoá theo nhờ cascade. Xoá cả file đã lưu, gỡ liên kết `superseded_by` ở tài liệu khác, và ghi audit.
- Khai báo các route tĩnh `/documents:reindex` và `/documents:delete` **trước** route `/documents/{docId}`.

**Bước 5: Phân quyền.**
- Mọi endpoint dùng `require_roles("admin")` từ `app/api/deps.py`.
- Không import thẳng từ `app.security`.

**Bước 6: Kiểm thủ công với giao diện.**
- Đặt `NEXT_PUBLIC_KB_API_URL=http://localhost:8000/api/kb` cho kb-admin, rồi thử đủ 7 thao tác.
- Lưu ý: giai đoạn này kb-admin vẫn gọi thẳng FastAPI. Muốn tránh CORS thì thêm tạm `rewrites` trong `next.config.ts`, **không** bật CORS ở backend. Sau này BFF sẽ thay `rewrites`.

## Ngoại lệ: admin xem tài liệu Mật (ADR-004 mục 4)

- `GET /documents/{docId}` trả chunk của tài liệu `classification = "Mat"` cho admin, **kèm ghi** `audit_logs.event = "kb_view_classified"`.
- Ghi log và đọc dữ liệu nằm trong cùng một transaction. Ghi log thất bại thì trả 500 và không trả chunk (fail closed).
- Quy tắc đúng: chỉ ghi log khi admin **tự mình không** `can_read` tài liệu đó. Nhưng hiện tại admin là `UserInfo` lấy từ bảng `users`, chưa có `Principal`, nên **giai đoạn này luôn ghi log khi xem tài liệu Mật**. Cách này an toàn hơn. Khi đã có `get_principal` (Zitadel) thì mới áp đúng quy tắc.
- Thêm trường `accessLogged: true` vào `KbDocumentDetail`, đồng thời thêm vào `types.ts` và `mock.ts`, để giao diện hiện dòng "Lượt xem này đã được ghi nhật ký".
- `acl_sql` và `can_read` **không đổi**. Luồng chat và RAG vẫn không có ngoại lệ cho admin.

## Test bắt buộc

- `TestClient` cùng `app.dependency_overrides`, theo khuôn của `tests/test_ocr_api.py`.
- Các ca:
  - không có token thì trả 401; không phải admin thì trả 403;
  - sai `docId` thì trả 404; upload trùng thì trả 409; file `.md` không có frontmatter mà cũng không có `meta` thì trả 422;
  - `access` trả đúng `reason` cho từng trường hợp;
  - xem tài liệu Mật thì có đúng 1 dòng `kb_view_classified`; xem tài liệu thường thì không có dòng nào;
  - `reindex` một lô có một tài liệu lỗi: các tài liệu khác vẫn được nạp lại.
- Chạy: `.\.venv\Scripts\python -m pytest`, rồi `ruff check .`

## Để sau

- Trạng thái `processing` thật: trả 202, rồi embed bằng BackgroundTasks hoặc hàng đợi (cần thêm cột `status` và `status_note`).
- Tự gắn cờ cách ly cho tài liệu nghi chứa prompt injection (P2).
- Phân trang `GET /documents`.
- `GET /api/me`, dùng chung cho portal (ADR-005 có nhắc).
