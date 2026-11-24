"""Đổi domain email của tài khoản Zitadel tại chỗ (sau khi danh bạ đổi từ saoviet.example sang cty-a.example).

    .\\.venv\\Scripts\\python -m app.migrate_email_domain                 # chỉ in việc sẽ làm (không đụng Zitadel)
    .\\.venv\\Scripts\\python -m app.migrate_email_domain --apply         # đổi thật
    .\\.venv\\Scripts\\python -m app.migrate_email_domain --apply --only huy.do

- Email mới lấy từ data/hr/employees.csv (nguồn duy nhất); email cũ = phần tên + --old-domain.
- Đổi cả username lẫn email, GIỮ nguyên user id, mật khẩu, quyền (grant) và trạng thái khoá.
- Chạy lại được: tài khoản đã mang email mới thì bỏ qua; không có tài khoản cũ cũng không có mới thì chỉ báo.
- Cấu hình Zitadel giống app.seed_zitadel (ZITADEL_ADMIN_PAT, ZITADEL_URL, ZITADEL_HOST).
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

from app.auth.zitadel_admin import ZitadelAdmin

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "infra" / "zitadel" / "out"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(ROOT / "data" / "hr" / "employees.csv"))
    ap.add_argument("--old-domain", default="saoviet.example")
    ap.add_argument("--apply", action="store_true", help="đổi thật; không có cờ này chỉ in")
    ap.add_argument("--only", help="chỉ đổi một người, ví dụ huy.do")
    args = ap.parse_args()

    token = os.environ.get("ZITADEL_ADMIN_PAT")
    if not token:
        gen = OUT / "generated.json"
        if not gen.exists():
            raise SystemExit("Chưa có infra/zitadel/out/generated.json: chạy infra/zitadel/bootstrap.py trước.")
        token = json.loads(gen.read_text("utf-8"))["portalAdminApiPat"]
    z = ZitadelAdmin(
        os.environ.get("ZITADEL_URL", "http://127.0.0.1:8180"),
        token,
        host=os.environ.get("ZITADEL_HOST", "auth.tranduyai.id.vn"),
    )

    counts = {"đổi": 0, "đã đúng": 0, "không thấy": 0}
    with open(args.csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            new = row["email"].strip().lower()
            local = new.split("@", 1)[0]
            if args.only and local != args.only:
                continue
            old = f"{local}@{args.old_domain}"
            if z.find_by_username(new) is not None:
                counts["đã đúng"] += 1
                continue
            user = z.find_by_username(old)
            if user is None:
                print(f"  không thấy: {old} (cũng chưa có {new}); chạy app.seed_zitadel để tạo")
                counts["không thấy"] += 1
                continue
            print(f"  {'đổi' if args.apply else 'sẽ đổi'}: {old} -> {new} (id {user.id})")
            if args.apply:
                z.change_login(user.id, username=new, email=new)
            counts["đổi"] += 1
    print(", ".join(f"{k}: {v}" for k, v in counts.items()) + ("" if args.apply else "  [dry-run]"))


if __name__ == "__main__":
    main()
