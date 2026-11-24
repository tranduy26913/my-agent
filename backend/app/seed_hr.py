"""Nạp dữ liệu nhân sự mô phỏng từ data/hr/*.csv vào DB. Đây là NGUỒN DANH TÍNH cho phân quyền tài liệu: knowledge-mcp
và /api/* tra phòng ban/vai trò ở bảng employees theo email trong token.
(Thực tế: đồng bộ định kỳ từ HRM/Entra ID, không để client tự khai vai trò.)

    python -m app.seed_hr [--csv ../data/hr/employees.csv] [--dry-run]

Nạp 4 thứ, cùng thư mục với employees.csv: employees (+ số điện thoại -> employee_contacts), leave_balances.csv,
leave_requests.csv. Chạy lại được nhiều lần (cập nhật theo khoá tự nhiên, không nhân đôi). Bảng mới được tạo bởi
`init_db()` (create_all chỉ tạo bảng còn thiếu, không đổi bảng đã có).

`--dry-run`: chỉ đọc CSV và in ra việc sẽ làm, kèm bảng nào chưa có trong DB; không ghi gì.
"""

import argparse
import csv
from datetime import date
from pathlib import Path

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.db import SessionLocal, engine, init_db

NEW_TABLES = ("leave_balances", "leave_requests", "employee_contacts")


def read(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_all(db: Session, employees: list[dict], balances: list[dict], requests: list[dict]) -> None:
    """Nạp (upsert) cả bốn thứ vào `db`; người gọi commit. Tách ra để test chạy được trong transaction rollback."""
    from app.models import Employee, EmployeeContact, LeaveBalance, LeaveRequest

    for row in employees:
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
    db.flush()  # khoá ngoại của ba bảng dưới trỏ tới employees.code

    for row in employees:
        phone = row.get("so_dien_thoai", "").strip()
        contact = db.get(EmployeeContact, row["ma_nv"])
        if phone:
            if contact is None:
                contact = EmployeeContact(employee_code=row["ma_nv"], phone=phone)
            contact.phone = phone
            db.add(contact)
        elif contact is not None:
            db.delete(contact)

    for row in balances:
        year = int(row["nam"])
        b = db.execute(
            select(LeaveBalance).where(LeaveBalance.employee_code == row["ma_nv"], LeaveBalance.year == year)
        ).scalar_one_or_none()
        b = b or LeaveBalance(employee_code=row["ma_nv"], year=year)
        b.entitled = float(row["phep_nam_duoc_huong"])
        b.carried_over = float(row["phep_ton_chuyen_sang"])
        b.carried_expired = float(row["phep_ton_da_huy"])
        b.used = float(row["da_su_dung"])
        b.remaining = float(row["con_lai"])
        db.add(b)

    for row in requests:
        r = db.execute(select(LeaveRequest).where(LeaveRequest.code == row["ma_don"])).scalar_one_or_none()
        r = r or LeaveRequest(code=row["ma_don"])
        r.employee_code = row["ma_nv"]
        r.kind = row["loai_nghi"]
        r.from_date = date.fromisoformat(row["tu_ngay"])
        r.to_date = date.fromisoformat(row["den_ngay"])
        r.days = float(row["so_ngay"])
        r.status = row["trang_thai"]
        r.approver_code = row["nguoi_duyet"] or None
        r.note = row["ghi_chu"]
        db.add(r)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="../data/hr/employees.csv")
    ap.add_argument("--dry-run", action="store_true", help="Chỉ in việc sẽ làm, không ghi vào DB")
    args = ap.parse_args()

    emp_csv = Path(args.csv)
    employees = read(emp_csv)
    balances = read(emp_csv.with_name("leave_balances.csv"))
    requests = read(emp_csv.with_name("leave_requests.csv"))

    if args.dry_run:
        have = set(inspect(engine).get_table_names())
        print(f"Sẽ nạp: {len(employees)} nhân viên, {len(balances)} số dư phép, {len(requests)} đơn nghỉ")
        print("Bảng chưa có (sẽ được tạo): " + (", ".join(t for t in NEW_TABLES if t not in have) or "không"))
        return

    init_db()
    with SessionLocal() as db:
        load_all(db, employees, balances, requests)
        db.commit()
    print(f"Đã nạp {len(employees)} nhân viên, {len(balances)} số dư phép, {len(requests)} đơn nghỉ")


if __name__ == "__main__":
    main()
