"""Tạo tài khoản Zitadel cho từng nhân viên trong data/hr/employees.csv (docs/06, giai đoạn 2.6).

    .\\.venv\\Scripts\\python -m app.seed_zitadel [--csv ../data/hr/employees.csv]

- Chạy lại được: tài khoản đã có thì giữ nguyên (không đặt lại mật khẩu).
- Nhân viên `da-nghi-viec`: tạo xong thì khoá (deactivate); nhân viên quay lại đi làm thì mở lại.
- Mật khẩu tạm của tài khoản MỚI ghi vào infra/zitadel/out/user-passwords.txt (đã .gitignore); người dùng
  bị buộc đổi mật khẩu ở lần đăng nhập đầu.
- Dùng PAT của `portal-admin-api` (infra/zitadel/out/generated.json hoặc ZITADEL_ADMIN_PAT), không dùng PAT
  `bootstrap`.
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

from app.auth.zitadel_admin import ZitadelAdmin, temp_password

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "infra" / "zitadel" / "out"
LEFT = "da-nghi-viec"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(ROOT / "data" / "hr" / "employees.csv"))
    args = ap.parse_args()

    token = os.environ.get("ZITADEL_ADMIN_PAT")
    if not token:
        gen = OUT / "generated.json"
        if not gen.exists():
            raise SystemExit(
                "Chưa có infra/zitadel/out/generated.json: chạy infra/zitadel/bootstrap.py trước."
            )
        token = json.loads(gen.read_text("utf-8"))["portalAdminApiPat"]
    z = ZitadelAdmin(
        os.environ.get("ZITADEL_URL", "http://127.0.0.1:8180"),
        token,
        host=os.environ.get("ZITADEL_HOST", "auth.tranduyai.id.vn"),
    )

    created: list[tuple[str, str]] = []
    counts = {"tạo": 0, "có sẵn": 0, "khoá": 0, "mở lại": 0}
    with open(args.csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            email = row["email"].strip().lower()
            left = row["trang_thai"] == LEFT
            user = z.find_by_username(email)
            if user is None:
                pw = temp_password()
                uid = z.create_human(username=email, email=email, full_name=row["ho_ten"], password=pw)
                created.append((email, pw))
                counts["tạo"] += 1
            else:
                uid = user.id
                counts["có sẵn"] += 1
            inactive = user is not None and user.state == "USER_STATE_INACTIVE"
            if left and (user is None or not inactive):
                z.deactivate(uid)
                counts["khoá"] += 1
            elif not left and inactive:
                z.reactivate(uid)
                counts["mở lại"] += 1

    if created:
        OUT.mkdir(parents=True, exist_ok=True)
        with open(OUT / "user-passwords.txt", "a", encoding="utf-8") as f:
            for email, pw in created:
                f.write(f"{email}\t{pw}\n")
    print(", ".join(f"{k}: {v}" for k, v in counts.items()))
    if created:
        print(f"Mật khẩu tạm của {len(created)} tài khoản mới: infra/zitadel/out/user-passwords.txt")


if __name__ == "__main__":
    main()
