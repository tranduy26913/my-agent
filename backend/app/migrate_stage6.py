"""Migration giai đoạn 6 (docs/06): bỏ bảng `users`, lưu người nạp tài liệu bằng email.

DB không dùng alembic (create_all chỉ tạo bảng thiếu, không sửa bảng đã có), nên đổi cột phải chạy tay.

    python -m app.migrate_stage6                # chỉ in những việc sẽ làm (không đụng DB)
    python -m app.migrate_stage6 --apply        # bước A: đổi kiểu cột, gỡ khoá ngoại. KHÔNG xoá dữ liệu
    python -m app.migrate_stage6 --drop-users   # bước B: DROP TABLE users (xoá dữ liệu, không hoàn tác)

Bước A chạy lại nhiều lần được (kiểm trạng thái trước khi làm). Bước B từ chối chạy nếu còn khoá ngoại tới
`users` hoặc bảng `users` có dòng khác `portal-dev`; hãy sao lưu DB (pg_dump) trước khi chạy.
"""

import argparse
import sys

from sqlalchemy import text

from app.db import engine

FK_SQL = """
SELECT c.conname, c.conrelid::regclass::text AS tbl
FROM pg_constraint c
WHERE c.contype = 'f' AND c.confrelid = 'users'::regclass
"""


def _exists(conn, table: str) -> bool:
    return conn.execute(text("SELECT to_regclass(:t) IS NOT NULL"), {"t": table}).scalar_one()


def plan_a(conn) -> list[str]:
    steps: list[str] = []
    if not _exists(conn, "users"):
        col = conn.execute(text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name='documents' AND column_name='uploaded_by'")).scalar()
        if col != "character varying":
            steps.append("ALTER TABLE documents ALTER COLUMN uploaded_by TYPE varchar(255) USING NULL")
        return steps
    for name, tbl in conn.execute(text(FK_SQL)).all():
        steps.append(f"ALTER TABLE {tbl} DROP CONSTRAINT {name}")
    col = conn.execute(text(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name='documents' AND column_name='uploaded_by'")).scalar()
    if col != "character varying":
        n = conn.execute(text("SELECT count(*) FROM documents WHERE uploaded_by IS NOT NULL")).scalar_one()
        if n:
            raise SystemExit(f"{n} tài liệu có uploaded_by (id bảng users): cần backfill sang email trước.")
        steps.append("ALTER TABLE documents ALTER COLUMN uploaded_by TYPE varchar(255) USING NULL")
    return steps


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # console Windows mặc định cp1252
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="bước A: đổi kiểu cột, gỡ khoá ngoại")
    ap.add_argument("--drop-users", action="store_true", help="bước B: xoá bảng users (không hoàn tác)")
    args = ap.parse_args()

    with engine.begin() as conn:
        steps = plan_a(conn)
        if args.drop_users:
            if not _exists(conn, "users"):
                print("Bảng users không còn.")
                return
            if steps:
                raise SystemExit("Chạy --apply (bước A) trước:\n  " + "\n  ".join(steps))
            rows = conn.execute(text("SELECT username FROM users")).scalars().all()
            extra = [u for u in rows if u != "portal-dev"]
            if extra:
                raise SystemExit(f"Bảng users còn người dùng thật: {extra}. Không xoá.")
            print(f"DROP TABLE users  (đang có {len(rows)} dòng: {rows})")
            conn.execute(text("DROP TABLE users"))
            return
        if not steps:
            print("Bước A: không có gì để làm.")
            return
        for sql in steps:
            print(("ĐANG CHẠY: " if args.apply else "SẼ CHẠY:   ") + sql)
            if args.apply:
                conn.execute(text(sql))


if __name__ == "__main__":
    main()
