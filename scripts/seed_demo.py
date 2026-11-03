#!/usr/bin/env python
"""Tạo dữ liệu minh họa qua API của Teacher Management."""

from __future__ import annotations

import argparse
import getpass
from io import BytesIO
import os
import secrets
import struct
import sys
import zlib
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx
from openpyxl import Workbook, load_workbook


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_WORKBOOK = ROOT / "sample_data" / "mau_nhap_giang_vien.xlsx"
DEMO_ACCOUNTS = (
    ("hr_demo1", "Nhân viên nhân sự demo 1", "hr", False),
    ("hr_demo2", "Nhân viên nhân sự demo 2", "hr", False),
    ("manager_demo1", "Người quản lý demo 1", "manager", False),
    ("manager_demo2", "Người quản lý demo 2", "manager", False),
    ("hr_demolocked", "Tài khoản nhân sự demo đã khóa", "hr", True),
)
DEMO_LECTURER_ACCOUNTS = (("lecturer_demo1", "DEMO-GV-001"),)
DEGREES = ("Cử nhân", "Thạc sĩ", "Tiến sĩ", "Phó giáo sư")
TITLES = ("Trợ giảng", "Giảng viên", "Giảng viên chính")
FICTIONAL_NAMES = (
    "Nguyễn An Bình", "Trần Minh Châu", "Lê Hoàng Duy", "Phạm Thu Giang",
    "Hoàng Quốc Huy", "Vũ Ngọc Khánh", "Đặng Mai Lan", "Bùi Đức Minh",
    "Đỗ Thanh Nga", "Ngô Quang Phúc", "Dương Hải Quân", "Lý Bảo Trang",
    "Mai Khánh Uyên", "Phan Gia Việt", "Trịnh Hà Yến", "Cao Anh Tú",
    "Hồ Minh Khoa", "Tạ Ngọc Linh", "Chu Đức Long", "Đinh Thảo My",
    "La Quốc Nam", "Tô Hồng Nhung", "Quách Gia Phong", "Lâm Bảo Quyên",
    "Thái Minh Sơn", "Nông Thu Thủy", "Vi Quốc Toàn", "Lương Hải Vân",
    "Tăng Đức Vinh", "Kim Ngọc Xuân",
)


class SeedError(RuntimeError):
    """Lỗi có thông báo trực tiếp cho người chạy script."""


class Api:
    def __init__(self, client: httpx.Client) -> None:
        self.client = client
        self.csrf_token = ""

    def login(self, username: str, password: str) -> dict[str, Any]:
        response = self.client.post(
            "/auth/login",
            json={"username": username, "password": password},
        )
        self._check(response)
        payload = response.json()
        self.csrf_token = payload["csrf_token"]
        return payload

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = dict(kwargs.pop("headers", {}))
        if method.upper() not in {"GET", "HEAD", "OPTIONS"}:
            headers["X-CSRF-Token"] = self.csrf_token
        response = self.client.request(method, path, headers=headers, **kwargs)
        self._check(response)
        return response

    @staticmethod
    def _check(response: httpx.Response) -> None:
        if response.is_error:
            detail = response.text[:1200]
            raise SeedError(
                f"API {response.request.method} {response.request.url.path} "
                f"trả HTTP {response.status_code}: {detail}"
            )


def new_demo_password() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%_-"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(24))
        if (
            any(character.islower() for character in password)
            and any(character.isupper() for character in password)
            and any(character.isdigit() for character in password)
            and any(character in "!@#$%_-" for character in password)
        ):
            return password


def admin_credentials() -> tuple[str, str]:
    username = os.getenv("SEED_ADMIN_USER", "").strip()
    if not username:
        username = input("Tài khoản quản trị viên hiện có: ").strip()
    password = os.getenv("SEED_ADMIN_PASSWORD", "")
    if not password:
        password = getpass.getpass("Mật khẩu quản trị viên: ")
    if not username or not password:
        raise SeedError("Cần cung cấp SEED_ADMIN_USER và SEED_ADMIN_PASSWORD.")
    return username, password


def write_sample_workbook(headers: list[str], department_code: str) -> None:
    SAMPLE_WORKBOOK.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Mau nhap"
    sheet.append(headers)

    for index in range(1, 11):
        sheet.append(
            [
                f"DEMO-XLS-{index:03d}",
                f"Giảng viên mẫu nhập {index:02d}",
                department_code,
                f"{1970 + index}-0{index % 9 + 1}-15",
                "Nam" if index % 2 else "Nữ",
                f"mau.nhap{index:02d}@example.edu.vn",
                f"090000{index:04d}",
                f"Khu vực giả lập {index:02d}, Hà Nội",
                DEGREES[index % len(DEGREES)],
                TITLES[index % len(TITLES)],
                "Đang công tác",
            ]
        )
    sheet.append(
        [
            "DEMO-XLS-ERR-UNIT",
            "Giảng viên lỗi mã đơn vị",
            "DEMO-UNIT-SAI",
            "1985-05-20",
            "Nam",
            "loi.donvi@example.edu.vn",
            "0900009001",
            "Khu vực giả lập",
            "Thạc sĩ",
            "Giảng viên",
            "Đang công tác",
        ]
    )
    sheet.append(
        [
            "DEMO-XLS-001",
            "Giảng viên lỗi mã trùng",
            department_code,
            "1984-06-21",
            "Nữ",
            "loi.trung@example.edu.vn",
            "0900009002",
            "Khu vực giả lập",
            "Thạc sĩ",
            "Giảng viên",
            "Đang công tác",
        ]
    )
    sheet.append(
        [
            "DEMO-XLS-ERR-DATE",
            "Giảng viên lỗi ngày sinh",
            department_code,
            "31/13/1985",
            "Nam",
            "loi.ngaysinh@example.edu.vn",
            "0900009003",
            "Khu vực giả lập",
            "Cử nhân",
            "Trợ giảng",
            "Đang công tác",
        ]
    )
    workbook.save(SAMPLE_WORKBOOK)


def demo_departments(api: Api) -> tuple[list[dict[str, Any]], str]:
    department_specs = (
        ("DEMO-KHOA-CNTT", "Khoa Công nghệ thông tin", None),
        ("DEMO-KHOA-KT", "Khoa Kinh tế", None),
        ("DEMO-KHOA-NN", "Khoa Ngoại ngữ", None),
    )
    subdepartment_specs = (
        ("DEMO-CNTT-HTTT", "Bộ môn Hệ thống thông tin", "DEMO-KHOA-CNTT"),
        ("DEMO-CNTT-KHMT", "Bộ môn Khoa học máy tính", "DEMO-KHOA-CNTT"),
        ("DEMO-CNTT-MMT", "Bộ môn Mạng máy tính", "DEMO-KHOA-CNTT"),
        ("DEMO-KT-QT", "Bộ môn Quản trị", "DEMO-KHOA-KT"),
        ("DEMO-KT-TC", "Bộ môn Tài chính", "DEMO-KHOA-KT"),
        ("DEMO-NN-ANH", "Bộ môn Ngôn ngữ Anh", "DEMO-KHOA-NN"),
        ("DEMO-NN-TRUNG", "Bộ môn Ngôn ngữ Trung", "DEMO-KHOA-NN"),
    )
    existing = {
        department["code"]: department
        for department in api.request(
            "GET", "/departments", params={"include_inactive": "true"}
        ).json()
    }

    def ensure_department(
        code: str, name: str, parent_id: int | None
    ) -> dict[str, Any]:
        department = existing.get(code)
        if department is None:
            payload: dict[str, Any] = {"code": code, "name": name}
            if parent_id is not None:
                payload["parent_id"] = parent_id
            department = api.request("POST", "/departments", json=payload).json()
            print(f"  Đã tạo đơn vị: {name}")
        else:
            changes: dict[str, Any] = {}
            if department["name"] != name:
                changes["name"] = name
            if department["parent_id"] != parent_id:
                changes["parent_id"] = parent_id
            if not department["is_active"]:
                changes["is_active"] = True
            if changes:
                department = api.request(
                    "PATCH",
                    f"/departments/{department['id']}",
                    json=changes,
                ).json()
                print(f"  Đã cập nhật đơn vị demo: {name}")
            else:
                print(f"  Đơn vị đã có: {name}")
        existing[code] = department
        return department

    faculties: dict[str, dict[str, Any]] = {}
    for code, name, _ in department_specs:
        faculties[code] = ensure_department(code, name, None)
    units = [
        ensure_department(code, name, faculties[parent_code]["id"])
        for code, name, parent_code in subdepartment_specs
    ]

    inactive_code = "DEMO-DONVI-NGUNG"
    inactive = existing.get(inactive_code)
    if inactive is None:
        inactive = api.request(
            "POST",
            "/departments",
            json={
                "code": inactive_code,
                "name": "Bộ môn demo đã ngừng hoạt động",
                "parent_id": faculties["DEMO-KHOA-CNTT"]["id"],
                "description": "Đơn vị minh họa trạng thái ngừng hoạt động.",
            },
        ).json()
        print("  Đã tạo đơn vị demo đã ngừng hoạt động.")
    if inactive["is_active"]:
        inactive = api.request(
            "PATCH",
            f"/departments/{inactive['id']}",
            json={"is_active": False},
        ).json()
        print("  Đã ngừng hoạt động đơn vị demo.")
    else:
        print("  Đơn vị ngừng hoạt động đã có.")
    return units, units[0]["code"]


def teacher_specs(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    today = date.today()
    teachers = []
    for index, name in enumerate(FICTIONAL_NAMES):
        year = 1960 + (index * 7 % 41)
        month = index % 12 + 1
        day = index % 25 + 1
        teachers.append(
            {
                "employee_code": f"DEMO-GV-{index + 1:03d}",
                "full_name": name,
                "department_id": units[index % len(units)]["id"],
                "date_of_birth": date(year, month, day).isoformat(),
                "gender": "Nữ" if index % 2 else "Nam",
                "email": (
                    None
                    if index in {4, 11, 19, 26}
                    else f"giangvien{index + 1:03d}@example.edu.vn"
                ),
                "phone": (
                    None
                    if index in {7, 17, 25}
                    else f"090000{index + 1:04d}"
                ),
                "address": f"Khu vực giả lập {index + 1:03d}, Hà Nội",
                "academic_degree": DEGREES[index % len(DEGREES)],
                "academic_title": TITLES[(index // 2) % len(TITLES)],
                "employment_status": (
                    "active" if index < 24 else "paused" if index < 28 else "ended"
                ),
            }
        )
    teachers.extend(
        [
            {
                "employee_code": "DEMO-BT-1950",
                "full_name": "Nguyễn Minh Khang",
                "department_id": units[0]["id"],
                "date_of_birth": "1950-04-12",
                "gender": "Nam",
                "email": "batthuong1950@example.edu.vn",
                "phone": "0900009500",
                "address": "Khu vực giả lập đặc biệt A",
                "academic_degree": None,
                "academic_title": "Giảng viên",
                "employment_status": "active",
            },
            {
                "employee_code": "DEMO-BT-2003",
                "full_name": "Trần Ngọc Hân",
                "department_id": units[1]["id"],
                "date_of_birth": "2003-08-22",
                "gender": "Nữ",
                "email": "batthuong2003@example.edu.vn",
                "phone": "0900002003",
                "address": "Khu vực giả lập đặc biệt B",
                "academic_degree": "Tiến sĩ",
                "academic_title": "Giảng viên chính",
                "employment_status": "paused",
            },
        ]
    )
    return teachers


def ensure_teachers(api: Api, specs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    existing_teachers = {
        teacher["employee_code"]: teacher
        for teacher in api.request("GET", "/teachers").json()
        if teacher["employee_code"].startswith("DEMO-")
    }
    teachers: dict[str, dict[str, Any]] = {}
    created = 0
    existing = 0
    for payload in specs:
        code = payload["employee_code"]
        teacher = existing_teachers.get(code)
        if teacher is not None:
            existing += 1
        else:
            teacher = api.request("POST", "/teachers", json=payload).json()
            created += 1
        teachers[code] = teacher
    print(f"  Hồ sơ giảng viên: tạo {created}, đã có {existing}.")
    return teachers


def ensure_lecturer_accounts(
    api: Api,
    teachers: dict[str, dict[str, Any]],
    passwords: dict[str, str],
) -> None:
    existing_users = {
        user["username"]: user for user in api.request("GET", "/users").json()
    }
    for username, employee_code in DEMO_LECTURER_ACCOUNTS:
        teacher = teachers[employee_code]
        full_name = teacher["full_name"]
        password = new_demo_password()
        user = existing_users.get(username)
        if user is None:
            user = api.request(
                "POST",
                "/users",
                json={
                    "username": username,
                    "full_name": full_name,
                    "password": password,
                    "role": "lecturer",
                    "teacher_id": teacher["id"],
                },
            ).json()
            print(f"  Đã tạo tài khoản demo: {username} (lecturer).")
        else:
            changes: dict[str, Any] = {}
            if user["full_name"] != full_name:
                changes["full_name"] = full_name
            if user["role"] != "lecturer":
                changes["role"] = "lecturer"
            if user["teacher_id"] != teacher["id"]:
                changes["teacher_id"] = teacher["id"]
            if changes:
                user = api.request(
                    "PATCH", f"/users/{user['id']}", json=changes
                ).json()
            api.request(
                "POST",
                f"/users/{user['id']}/reset-password",
                json={"new_password": password},
            )
            print(f"  Tài khoản demo đã có, đã đặt lại mật khẩu: {username}.")
        if not user["is_active"]:
            api.request(
                "PATCH", f"/users/{user['id']}", json={"is_active": True}
            )
        passwords[username] = password


def ensure_qualifications(
    api: Api, teachers: dict[str, dict[str, Any]]
) -> dict[int, list[dict[str, Any]]]:
    today = date.today()
    by_teacher: dict[int, list[dict[str, Any]]] = {}
    created = 0
    existing = 0
    for index, (code, teacher) in enumerate(teachers.items()):
        teacher_id = teacher["id"]
        qualifications = api.request(
            "GET", f"/teachers/{teacher_id}/qualifications"
        ).json()
        titles = {item["title"] for item in qualifications}
        wanted: list[dict[str, Any]] = []
        if code != "DEMO-BT-1950":
            wanted.append(
                {
                    "qualification_type": "degree",
                    "title": f"DEMO-Bằng cấp chuyên môn {code}",
                    "specialty": "Chuyên ngành giả lập",
                    "institution": "Trường đại học giả lập",
                    "issued_year": 2000 + index % 20,
                }
            )
        if code != "DEMO-BT-1950" and index % 3 != 1:
            if index % 3 == 0:
                expiry = today - timedelta(days=12 + index)
            elif index % 3 == 2 and index < 20:
                expiry = today + timedelta(days=2 + index % 27)
            else:
                expiry = today + timedelta(days=180 + index)
            wanted.append(
                {
                    "qualification_type": "certificate",
                    "title": f"DEMO-Chứng chỉ ngoại ngữ {code}",
                    "specialty": "Ngoại ngữ giả lập",
                    "institution": "Trung tâm đào tạo giả lập",
                    "issued_on": (expiry - timedelta(days=365)).isoformat(),
                    "issued_year": expiry.year - 1,
                    "expires_on": expiry.isoformat(),
                }
            )
        if code != "DEMO-BT-1950" and index % 5 == 0:
            wanted.append(
                {
                    "qualification_type": "certificate",
                    "title": f"DEMO-Nghiệp vụ sư phạm {code}",
                    "specialty": "Sư phạm giả lập",
                    "institution": "Trung tâm đào tạo giả lập",
                    "issued_year": 2018 + index % 6,
                }
            )
        for payload in wanted:
            if payload["title"] in titles:
                existing += 1
                continue
            item = api.request(
                "POST",
                f"/teachers/{teacher_id}/qualifications",
                json=payload,
            ).json()
            qualifications.append(item)
            titles.add(payload["title"])
            created += 1
        by_teacher[teacher_id] = qualifications
    print(f"  Bằng cấp/chứng chỉ: tạo {created}, đã có {existing}.")
    return by_teacher


def ensure_contracts(
    api: Api, teachers: dict[str, dict[str, Any]]
) -> dict[int, list[dict[str, Any]]]:
    today = date.today()
    created = 0
    existing = 0
    by_teacher: dict[int, list[dict[str, Any]]] = {}
    expiring_days = (4, 9, 15, 21, 27, 30)

    for index, (code, teacher) in enumerate(teachers.items()):
        teacher_id = teacher["id"]
        contracts = api.request("GET", f"/teachers/{teacher_id}/contracts").json()
        contract_codes = {item["contract_code"] for item in contracts}

        wanted: list[dict[str, Any]] = []
        if code == "DEMO-BT-1950":
            for number in range(6):
                starts_on = today - timedelta(days=(6 - number) * 365)
                ends_on = (
                    None
                    if number == 5
                    else (starts_on + timedelta(days=364)).isoformat()
                )
                wanted.append(
                    {
                        "contract_code": f"DEMO-HD-{code}-{number + 1:02d}",
                        "contract_type": (
                            "Không xác định thời hạn"
                            if number == 5
                            else "Xác định thời hạn"
                        ),
                        "signed_on": starts_on.isoformat(),
                        "starts_on": starts_on.isoformat(),
                        "ends_on": ends_on,
                        "status": "active" if number == 5 else "terminated",
                    }
                )
        elif teacher["employment_status"] == "active":
            if index < 6:
                ends_on = (today + timedelta(days=expiring_days[index])).isoformat()
            elif index < 9:
                ends_on = (today - timedelta(days=index - 5)).isoformat()
            else:
                ends_on = (today + timedelta(days=365 * 3)).isoformat()
            starts_on = today - timedelta(days=365 * (2 + index % 4))
            wanted.append(
                {
                    "contract_code": f"DEMO-HD-{code}-01",
                    "contract_type": (
                        "Thỉnh giảng"
                        if index % 3 == 0
                        else "Không xác định thời hạn"
                        if index % 3 == 1
                        else "Xác định thời hạn"
                    ),
                    "signed_on": starts_on.isoformat(),
                    "starts_on": starts_on.isoformat(),
                    "ends_on": ends_on,
                    "status": "active",
                }
            )
        for payload in wanted:
            if payload["contract_code"] in contract_codes:
                existing += 1
                continue
            contract = api.request(
                "POST",
                f"/teachers/{teacher_id}/contracts",
                json=payload,
            ).json()
            contracts.append(contract)
            contract_codes.add(payload["contract_code"])
            created += 1
        by_teacher[teacher_id] = contracts
    print(f"  Hợp đồng: tạo {created}, đã có {existing}.")
    return by_teacher


def ensure_work_history(
    api: Api,
    teachers: dict[str, dict[str, Any]],
    units: list[dict[str, Any]],
) -> None:
    today = date.today()
    created = 0
    existing = 0
    for index, (code, teacher) in enumerate(teachers.items()):
        teacher_id = teacher["id"]
        history = api.request(
            "GET", f"/teachers/{teacher_id}/work-history"
        ).json()
        reasons = {item["reason"] for item in history}
        additional_periods = index % 3
        for period in range(additional_periods):
            reason = f"DEMO-LICH-SU-{code}-{period + 1}"
            if reason in reasons:
                existing += 1
                continue
            start = today - timedelta(days=(additional_periods - period + 1) * 365)
            end = start + timedelta(days=364)
            previous_department = units[(index + period + 1) % len(units)]
            api.request(
                "POST",
                f"/teachers/{teacher_id}/work-history",
                json={
                    "department_id": previous_department["id"],
                    "position_title": TITLES[(index + period + 1) % len(TITLES)],
                    "starts_on": start.isoformat(),
                    "ends_on": end.isoformat(),
                    "reason": reason,
                },
            )
            reasons.add(reason)
            created += 1
    print(f"  Quá trình công tác bổ sung: tạo {created}, đã có {existing}.")


def ensure_checklist_statuses(api: Api, teachers: dict[str, dict[str, Any]]) -> None:
    items = api.request("GET", "/checklist-items").json()
    active_items = [item for item in items if item["is_active"]]
    required_ids = [
        item["id"] for item in active_items if item["classification"] == "required"
    ]
    conditional_ids = [
        item["id"]
        for item in active_items
        if item["classification"] != "optional"
    ]
    if not required_ids or not conditional_ids:
        raise SeedError("Danh mục checklist hiện hành không có mục bắt buộc/có điều kiện.")

    updates = 0
    unchanged = 0
    for index, teacher in enumerate(teachers.values()):
        teacher_id = teacher["id"]
        requirements = api.request(
            "GET", f"/teachers/{teacher_id}/checklist-requirements"
        ).json()
        if index < 12 or teacher["employee_code"] == "DEMO-BT-1950":
            expected = {item["item_id"]: "optional" for item in requirements}
        elif 12 <= index < 22:
            count = 1 + (index % 3)
            expected = {item["item_id"]: "optional" for item in requirements}
            for item_id in required_ids[:count]:
                expected[item_id] = "required"
        elif 22 <= index < 27 or teacher["employee_code"] == "DEMO-BT-2003":
            expected = {item["item_id"]: "optional" for item in requirements}
            expected[conditional_ids[0]] = "review"
        elif 27 <= index < 30:
            expected = {
                item["item_id"]: "not_applicable" for item in requirements
            }
        else:
            expected = {item["item_id"]: "optional" for item in requirements}

        for item in requirements:
            desired = expected.get(item["item_id"], "optional")
            if item["status"] == desired:
                unchanged += 1
                continue
            api.request(
                "PATCH",
                f"/teachers/{teacher_id}/checklist-requirements/{item['item_id']}",
                json={"status": desired},
            )
            updates += 1
    print(f"  Rà soát checklist: cập nhật {updates}, đã đúng {unchanged}.")


def png_chunk(kind: bytes, content: bytes) -> bytes:
    checksum = zlib.crc32(kind + content) & 0xFFFFFFFF
    return struct.pack(">I", len(content)) + kind + content + struct.pack(">I", checksum)


def demo_png(label: str) -> bytes:
    metadata = b"Description\x00Minh chung demo " + label.encode("ascii")
    metadata += b" x" * 700
    image = b"\x89PNG\r\n\x1a\n"
    image += png_chunk(
        b"IHDR",
        struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0),
    )
    image += png_chunk(b"tEXt", metadata)
    image += png_chunk(b"IDAT", zlib.compress(b"\x00\x4a\x82\xc8"))
    image += png_chunk(b"IEND", b"")
    return image


def demo_pdf(label: str) -> bytes:
    safe_label = label.encode("ascii", "replace").decode("ascii")
    safe_label = safe_label.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = (
        f"BT /F1 16 Tf 72 720 Td (Demo evidence: {safe_label}) Tj ET\n"
    ).encode("ascii")
    objects = (
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"endstream",
    )
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, content in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(content)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(output)


def ensure_documents(
    api: Api,
    teachers: dict[str, dict[str, Any]],
    qualifications: dict[int, list[dict[str, Any]]],
    contracts: dict[int, list[dict[str, Any]]],
) -> None:
    checklists = {
        item["code"]: item for item in api.request("GET", "/checklist-items").json()
    }
    checklist_codes = ("identity-document", "portrait-photo")
    if any(code not in checklists or not checklists[code]["is_active"] for code in checklist_codes):
        raise SeedError("Thiếu mục checklist định danh hoặc ảnh chân dung đang hoạt động.")

    eligible = [
        teacher
        for index, teacher in enumerate(teachers.values())
        if index < 12
    ]
    created = 0
    existing = 0
    kinds = ("degree", "contract", "identity", "portrait")
    for number in range(40):
        teacher = eligible[number % len(eligible)]
        teacher_id = teacher["id"]
        kind = kinds[number % len(kinds)]
        extension = ".png" if number % 2 == 0 else ".pdf"
        filename = f"DEMO-minh-chung-{number + 1:02d}-{kind}{extension}"
        documents = api.request(
            "GET", f"/teachers/{teacher_id}/documents"
        ).json()
        if any(item["original_name"] == filename for item in documents):
            existing += 1
            continue

        form_data: dict[str, str] = {}
        if kind == "degree":
            qualification = qualifications[teacher_id][0]
            form_data["qualification_id"] = str(qualification["id"])
        elif kind == "contract":
            teacher_contracts = contracts.get(teacher_id, [])
            if not teacher_contracts:
                raise SeedError(f"Thiếu hợp đồng demo cho {teacher['employee_code']}.")
            form_data["contract_id"] = str(teacher_contracts[0]["id"])
        else:
            checklist_code = (
                "identity-document" if kind == "identity" else "portrait-photo"
            )
            form_data["checklist_item_id"] = str(checklists[checklist_code]["id"])

        label = f"minh-chung-{number + 1:02d}"
        contents = demo_png(label) if extension == ".png" else demo_pdf(label)
        content_type = "image/png" if extension == ".png" else "application/pdf"
        api.request(
            "POST",
            f"/teachers/{teacher_id}/documents",
            data=form_data,
            files={"file": (filename, contents, content_type)},
        )
        created += 1
    print(f"  Tài liệu minh chứng: tải lên {created}, đã có {existing}.")


def ensure_change_requests(
    hr_api: Api,
    manager_apis: tuple[Api, Api],
    teachers: dict[str, dict[str, Any]],
    units: list[dict[str, Any]],
) -> None:
    current_requests = hr_api.request("GET", "/change-requests").json()
    demo_requests = {
        item["reason"].split("|", 1)[0]: item
        for item in current_requests
        if item["reason"].startswith("DEMO-YEUCAU-")
    }
    manager_one, manager_two = manager_apis
    managers = (manager_one, manager_two)
    teacher_values = list(teachers.values())
    today = date.today()
    created = 0
    processed = 0
    target_statuses = (
        ("approved", "approve", None),
        ("approved", "approve", None),
        ("approved", "approve", None),
        ("rejected", "reject", "Từ chối theo tình huống minh họa."),
        ("rejected", "reject", "Đề xuất chưa phù hợp với tình huống giả lập."),
        ("rejected", "reject", "Thiếu căn cứ nghiệp vụ trong ví dụ demo."),
        ("needs_info", "request_info", "Vui lòng bổ sung nội dung minh chứng giả lập."),
        ("needs_info", "request_info", "Cần bổ sung lý do và thời điểm áp dụng."),
        ("pending", "", None),
        ("pending", "", None),
        ("pending", "", None),
        ("pending", "", None),
    )
    for number, (target_status, action, resolution_reason) in enumerate(
        target_statuses, start=1
    ):
        marker = f"DEMO-YEUCAU-{number:02d}"
        item = demo_requests.get(marker)
        if item is None:
            teacher = teacher_values[number - 1]
            field_index = (number - 1) % 3
            if field_index == 0:
                old_department = teacher["department_id"]
                new_department = units[(number + 2) % len(units)]["id"]
                if new_department == old_department:
                    new_department = units[(number + 3) % len(units)]["id"]
                proposed = {"department_id": new_department}
                change_type = "Thay đổi đơn vị công tác"
                effective_on = (today + timedelta(days=14)).isoformat()
            elif field_index == 1:
                proposed = {
                    "academic_degree": DEGREES[
                        (DEGREES.index(teacher["academic_degree"]) + 1)
                        % len(DEGREES)
                    ]
                }
                change_type = "Thay đổi trình độ chuyên môn"
                effective_on = None
            else:
                proposed = {
                    "academic_title": TITLES[
                        (TITLES.index(teacher["academic_title"]) + 1)
                        % len(TITLES)
                    ]
                }
                change_type = "Thay đổi chức danh"
                effective_on = (today + timedelta(days=14)).isoformat()
            item = hr_api.request(
                "POST",
                f"/teachers/{teacher['id']}/change-requests",
                json={
                    "change_type": change_type,
                    "proposed_value": proposed,
                    "reason": f"{marker}| Đề nghị thay đổi để minh họa quy trình.",
                    "effective_on": effective_on,
                },
            ).json()
            demo_requests[marker] = item
            created += 1
        if item["status"] != "pending" or target_status == "pending":
            continue
        manager = managers[(number - 1) % len(managers)]
        manager.request(
            "POST",
            f"/change-requests/{item['id']}/decision",
            json={"action": action, "reason": resolution_reason},
        )
        processed += 1
    print(
        f"  Yêu cầu thay đổi: tạo {created}, xử lý mới {processed}; "
        "trạng thái gồm chờ duyệt, đã duyệt, từ chối, cần bổ sung."
    )


def record_failed_logins(
    base_url: str,
    usernames: list[str],
    correct_passwords: dict[str, str],
) -> None:
    for username in usernames:
        with httpx.Client(base_url=base_url, timeout=30) as client:
            failed = client.post(
                "/auth/login",
                json={
                    "username": username,
                    "password": f"sai-{secrets.token_urlsafe(12)}",
                },
            )
            if failed.status_code not in {401, 429}:
                raise SeedError(
                    f"Đăng nhập sai minh họa cho {username} trả "
                    f"HTTP {failed.status_code}: {failed.text[:500]}"
                )
            successful = client.post(
                "/auth/login",
                json={
                    "username": username,
                    "password": correct_passwords[username],
                },
            )
            Api._check(successful)
    print(f"  Nhật ký đăng nhập sai: đã ghi {len(usernames)} lần, không khóa tài khoản.")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")

    parser = argparse.ArgumentParser(
        description="Tạo dữ liệu giả lập qua API Teacher Management."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Địa chỉ server đang chạy (mặc định: http://127.0.0.1:8000).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Bỏ qua xác nhận trước khi ghi dữ liệu demo.",
    )
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    try:
        with httpx.Client(base_url=base_url, timeout=30) as health_client:
            health = health_client.get("/health")
    except httpx.ConnectError:
        print(
            "Không kết nối được server. Hãy khởi chạy ứng dụng bằng "
            r".\scripts\start_local.ps1 rồi chạy lại script.",
            file=sys.stderr,
        )
        return 1
    if health.is_error:
        raise SeedError(f"Health check thất bại: HTTP {health.status_code}.")

    print(f"Server: {base_url}")
    print("Script sẽ tạo/cập nhật dữ liệu demo qua API; không ghi trực tiếp SQLite.")
    if not args.yes and input("Tiếp tục? [y/N]: ").strip().lower() not in {"y", "yes"}:
        print("Đã hủy, không tạo dữ liệu.")
        return 0

    admin_user, admin_password = admin_credentials()
    admin_passwords: dict[str, str] = {}
    lecturer_passwords: dict[str, str] = {}
    with httpx.Client(base_url=base_url, timeout=60) as admin_client:
        admin_api = Api(admin_client)
        admin_api.login(admin_user, admin_password)
        existing_users = {
            user["username"]: user for user in admin_api.request("GET", "/users").json()
        }
        for username, full_name, role, is_locked in DEMO_ACCOUNTS:
            password = new_demo_password()
            user = existing_users.get(username)
            if user is None:
                user = admin_api.request(
                    "POST",
                    "/users",
                    json={
                        "username": username,
                        "full_name": full_name,
                        "password": password,
                        "role": role,
                    },
                ).json()
                print(f"  Đã tạo tài khoản demo: {username} ({role}).")
            else:
                changes: dict[str, Any] = {}
                if user["full_name"] != full_name:
                    changes["full_name"] = full_name
                if user["role"] != role:
                    changes["role"] = role
                if changes:
                    user = admin_api.request(
                        "PATCH", f"/users/{user['id']}", json=changes
                    ).json()
                admin_api.request(
                    "POST",
                    f"/users/{user['id']}/reset-password",
                    json={"new_password": password},
                )
                print(f"  Tài khoản demo đã có, đã đặt lại mật khẩu: {username}.")
            if user["is_active"] == is_locked:
                user = admin_api.request(
                    "PATCH",
                    f"/users/{user['id']}",
                    json={"is_active": not is_locked},
                ).json()
            admin_passwords[username] = password
        for username, _, _, is_locked in DEMO_ACCOUNTS:
            user = next(
                item
                for item in admin_api.request("GET", "/users").json()
                if item["username"] == username
            )
            if user["is_active"] == is_locked:
                admin_api.request(
                    "PATCH",
                    f"/users/{user['id']}",
                    json={"is_active": not is_locked},
                )
        print("Nhóm tài khoản demo: hoàn tất.")

    with httpx.Client(base_url=base_url, timeout=60) as hr_client:
        hr_api = Api(hr_client)
        hr_api.login("hr_demo1", admin_passwords["hr_demo1"])
        print("Nhóm khoa và bộ môn:")
        units, sample_department_code = demo_departments(hr_api)

        print("Nhóm hồ sơ giảng viên:")
        specs = teacher_specs(units)
        teachers = ensure_teachers(hr_api, specs)

        print("Nhóm tài khoản giảng viên:")
        with httpx.Client(base_url=base_url, timeout=60) as lecturer_admin_client:
            lecturer_admin_api = Api(lecturer_admin_client)
            lecturer_admin_api.login(admin_user, admin_password)
            ensure_lecturer_accounts(
                lecturer_admin_api, teachers, lecturer_passwords
            )

        print("Nhóm bằng cấp và chứng chỉ:")
        qualifications = ensure_qualifications(hr_api, teachers)

        print("Nhóm hợp đồng:")
        contracts = ensure_contracts(hr_api, teachers)

        print("Nhóm quá trình công tác:")
        ensure_work_history(hr_api, teachers, units)

        print("Nhóm checklist:")
        ensure_checklist_statuses(hr_api, teachers)

        print("Nhóm tài liệu minh chứng:")
        ensure_documents(hr_api, teachers, qualifications, contracts)

        print("Nhóm yêu cầu thay đổi:")
        manager_apis = []
        manager_clients = []
        for username in ("manager_demo1", "manager_demo2"):
            client = httpx.Client(base_url=base_url, timeout=60)
            manager_clients.append(client)
            manager_api = Api(client)
            manager_api.login(username, admin_passwords[username])
            manager_apis.append(manager_api)
        try:
            ensure_change_requests(
                hr_api,
                (manager_apis[0], manager_apis[1]),
                teachers,
                units,
            )

            print("Nhóm thông báo và báo cáo:")
            hr_notifications = hr_api.request("GET", "/notifications").json()
            manager_notifications = manager_apis[0].request(
                "GET", "/notifications"
            ).json()
            summary = hr_api.request("GET", "/reports/summary").json()
            if not summary["total_teachers"]:
                raise SeedError("Báo cáo không có hồ sơ giảng viên.")
            if not summary["incomplete_profiles"]:
                raise SeedError("Báo cáo không có hồ sơ chưa đầy đủ.")
            if not summary["expiring_or_expired_contracts"]:
                raise SeedError("Báo cáo không có hợp đồng cần theo dõi.")
            if not summary["change_requests_by_status"]:
                raise SeedError("Báo cáo không có yêu cầu thay đổi.")

            sample_response = hr_api.request("GET", "/teachers/import-template.xlsx")
            template = load_workbook(
                BytesIO(sample_response.content),
                read_only=True,
                data_only=True,
            )
            headers = [
                str(value) if value is not None else ""
                for value in next(template.worksheets[0].iter_rows(values_only=True))
            ]
            write_sample_workbook(headers, sample_department_code)
            template.close()
        finally:
            for client in manager_clients:
                client.close()

        locked_client = httpx.Client(base_url=base_url, timeout=30)
        try:
            locked_response = locked_client.post(
                "/auth/login",
                json={
                    "username": "hr_demolocked",
                    "password": f"sai-{secrets.token_urlsafe(12)}",
                },
            )
            if locked_response.status_code not in {401, 429}:
                raise SeedError(
                    "Tài khoản demo bị khóa có kết quả đăng nhập không mong đợi: "
                    f"HTTP {locked_response.status_code}."
                )
        finally:
            locked_client.close()

    record_failed_logins(
        base_url,
        ["hr_demo1", "hr_demo2", "manager_demo1", "manager_demo2", admin_user],
        {
            "hr_demo1": admin_passwords["hr_demo1"],
            "hr_demo2": admin_passwords["hr_demo2"],
            "manager_demo1": admin_passwords["manager_demo1"],
            "manager_demo2": admin_passwords["manager_demo2"],
            admin_user: admin_password,
        },
    )

    print("\nTỔNG KẾT")
    print(f"- Tệp nhập Excel: {SAMPLE_WORKBOOK}")
    print(f"- Tổng giảng viên: {summary['total_teachers']}")
    print(f"- Hồ sơ chưa đầy đủ: {summary['incomplete_profiles']}")
    print(
        "- Hợp đồng sắp/đã hết hạn: "
        f"{summary['expiring_or_expired_contracts']}"
    )
    print(f"- Yêu cầu theo trạng thái: {summary['change_requests_by_status']}")
    print(f"- Thông báo HR: {len(hr_notifications)}")
    print(f"- Thông báo quản lý: {len(manager_notifications)}")
    print("- Tài khoản demo (mật khẩu được đặt lại mỗi lần chạy):")
    for username, full_name, role, is_locked in DEMO_ACCOUNTS:
        suffix = " (đã khóa)" if is_locked else ""
        print(f"  {username} | {full_name} | {role}{suffix}")
        print(f"    Mật khẩu: {admin_passwords[username]}")
    for username, employee_code in DEMO_LECTURER_ACCOUNTS:
        teacher = teachers[employee_code]
        print(
            f"  {username} | {teacher['full_name']} | lecturer "
            f"({employee_code})"
        )
        print(f"    Mật khẩu: {lecturer_passwords[username]}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SeedError as error:
        print(f"Lỗi seed dữ liệu: {error}", file=sys.stderr)
        raise SystemExit(1) from error
