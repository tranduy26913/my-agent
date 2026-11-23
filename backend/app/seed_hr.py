"""Nạp danh bạ nhân sự (data/hr/employees.csv) -> bảng employees. Đây là NGUỒN DANH TÍNH cho
phân quyền tài liệu: knowledge-mcp nhận email từ LibreChat rồi tra phòng ban/vai trò ở đây.
(Thực tế: đồng bộ định kỳ từ HRM/Entra ID, không để client tự khai vai trò.)

    python -m app.seed_hr [--csv ../data/hr/employees.csv]
"""

import argparse
import csv

from sqlalchemy import select

from app.db import SessionLocal, init_db


def main() -> None:
    from app.models import Employee

    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="../data/hr/employees.csv")
    args = ap.parse_args()

    init_db()
    with SessionLocal() as db, open(args.csv, encoding="utf-8") as f:
        n = 0
        for row in csv.DictReader(f):
            emp = db.execute(select(Employee).where(Employee.code == row["ma_nv"])).scalar_one_or_none()
            emp = emp or Employee(code=row["ma_nv"])
            emp.full_name = row["ho_ten"]
            emp.email = row["email"].strip().lower()
            emp.department = row["phong_ban"]
            emp.title = row["chuc_danh"]
            emp.manager_code = row["ma_quan_ly"] or None
            emp.roles = [r for r in row["vai_tro"].split("|") if r]
            emp.status = row["trang_thai"]
            db.add(emp)
            n += 1
        db.commit()
    print(f"Đã nạp {n} nhân viên")


if __name__ == "__main__":
    main()
