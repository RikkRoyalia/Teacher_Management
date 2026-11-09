import os
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta, timezone
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import select

from app.main import create_app
from app.models import (
    AuditLog,
    ChecklistItem,
    Department,
    EmploymentContract,
    EvidenceDocument,
    Notification,
    Teacher,
    TeacherChecklistRequirement,
    User,
    WorkHistory,
)
from app.security import SESSION_COOKIE, hash_password
from scripts.seed_demo import Api, ensure_lecturer_accounts


class TeacherManagementApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.iterations_patch = patch("app.security.PASSWORD_ITERATIONS", 1_000)
        self.iterations_patch.start()
        self.temporary_uploads = tempfile.TemporaryDirectory()
        self.client_context = TestClient(create_app("sqlite://"))
        self.client = self.client_context.__enter__()
        self.client.app.state.upload_dir = Path(self.temporary_uploads.name)
        password_hash = hash_password("Correct horse battery staple 2048!")
        with self.client.app.state.session_factory() as db:
            for username, role in (
                ("admin", "admin"),
                ("hr", "hr"),
                ("manager", "manager"),
            ):
                db.add(
                    User(
                        username=username,
                        full_name=username.title(),
                        password_hash=password_hash,
                        role=role,
                    )
                )
            db.commit()
        self.hr = self.login("hr")
        self.csrf = self.hr["csrf_token"]
        response = self.client.post(
            "/departments",
            json={"code": "IT", "name": "Information Technology"},
            headers=self.headers(),
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.department_id = response.json()["id"]
        with self.client.app.state.session_factory() as db:
            manager = db.scalar(select(User).where(User.username == "manager"))
            department = db.get(Department, self.department_id)
            self.assertIsNotNone(manager)
            self.assertIsNotNone(department)
            manager.managed_departments = [department]
            db.commit()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.temporary_uploads.cleanup()
        self.iterations_patch.stop()

    def login(
        self,
        username: str,
        password: str = "Correct horse battery staple 2048!",
    ) -> dict[str, object]:
        response = self.client.post(
            "/auth/login",
            json={"username": username, "password": password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def headers(self) -> dict[str, str]:
        return {"X-CSRF-Token": str(self.csrf)}

    def create_teacher(self, employee_code: str = "T001", **overrides: object):
        payload: dict[str, object] = {
            "employee_code": employee_code,
            "full_name": "Nguyen Van An",
            "department_id": self.department_id,
            "academic_degree": "Master",
        }
        payload.update(overrides)
        return self.client.post("/teachers", json=payload, headers=self.headers())

    def test_authentication_static_assets_and_api_access(self) -> None:
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Hệ thống Quản lý Giảng viên", page.text)
        self.assertIn('id="teacher-form"', page.text)
        self.assertIn('id="account-form"', page.text)
        self.assertIn('data-view="lecturer"', page.text)
        self.assertIn("Quản trị hệ thống", page.text)
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/static/app.js").status_code, 200)
        self.assertEqual(self.client.get("/static/styles.css").status_code, 200)
        self.assertEqual(self.client.get("/static/favicon.svg").status_code, 200)
        for path, nonce_element in (
            ("/docs", "<script nonce="),
            ("/redoc", "<style nonce="),
        ):
            with self.subTest(docs_path=path):
                docs = self.client.get(path)
                self.assertEqual(docs.status_code, 200)
                self.assertIn("/openapi.json", docs.text)
                csp = docs.headers["content-security-policy"]
                nonce_match = re.search(r"'nonce-([^']+)'", csp)
                self.assertIsNotNone(nonce_match)
                self.assertIn(f'{nonce_element}"{nonce_match.group(1)}"', docs.text)
                self.assertIn("https://cdn.jsdelivr.net", csp)
                self.assertNotIn("'unsafe-inline'", csp.split("script-src", 1)[1].split(";", 1)[0])
                style_policy = csp.split("style-src ", 1)[1].split(";", 1)[0]
                if path == "/redoc":
                    self.assertIn("'unsafe-inline'", style_policy)
                else:
                    self.assertNotIn("'unsafe-inline'", style_policy)
        openapi = self.client.get("/openapi.json")
        self.assertEqual(openapi.status_code, 200)
        self.assertIn("script-src 'self';", openapi.headers["content-security-policy"])
        session = self.client.get("/auth/session")
        self.assertEqual(session.status_code, 200)
        self.assertEqual(session.json()["csrf_token"], self.csrf)
        self.assertEqual(page.headers["x-content-type-options"], "nosniff")

        unauthenticated = TestClient(create_app("sqlite://"))
        try:
            self.assertEqual(unauthenticated.get("/teachers").status_code, 401)
        finally:
            unauthenticated.close()

    def test_login_activity_is_recorded_from_independent_browser_session(self) -> None:
        incognito_client = TestClient(self.client.app)
        login_response = incognito_client.post(
            "/auth/login",
            json={
                "username": "hr",
                "password": "Correct horse battery staple 2048!",
            },
        )
        self.assertEqual(login_response.status_code, 200, login_response.text)

        with self.client.app.state.session_factory() as db:
            hr_user = db.scalar(select(User).where(User.username == "hr"))
            self.assertIsNotNone(hr_user)
            hr_user_id = hr_user.id

        admin = self.login("admin")
        audit_response = self.client.get(
            "/audit-logs",
            params={"actor_id": hr_user_id, "action": "login"},
            headers={"X-CSRF-Token": str(admin["csrf_token"])},
        )
        self.assertEqual(audit_response.status_code, 200, audit_response.text)
        self.assertTrue(audit_response.json())

    def test_create_filter_and_duplicate_teacher_code(self) -> None:
        created = self.create_teacher()
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["employee_code"], "T001")
        self.assertEqual(
            self.create_teacher("T002", full_name="Other Person", email="").json()["email"],
            None,
        )
        invalid_email = self.create_teacher("T003", email="not-an-email")
        self.assertEqual(invalid_email.status_code, 422)
        invalid_email_update = self.client.patch(
            f"/teachers/{created.json()['id']}",
            json={"email": "not-an-email"},
            headers=self.headers(),
        )
        self.assertEqual(invalid_email_update.status_code, 422)
        response = self.client.get(
            "/teachers",
            params={"q": "Nguyen", "academic_degree": "Master"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

        duplicate = self.create_teacher()
        self.assertEqual(duplicate.status_code, 409)

    def test_teacher_list_pagination_and_degree_filter_options(self) -> None:
        teacher_ids = [
            self.create_teacher(f"T{index:03d}").json()["id"]
            for index in range(1, 6)
        ]
        first_page = self.client.get("/teachers", params={"limit": 2, "offset": 0})
        second_page = self.client.get("/teachers", params={"limit": 2, "offset": 2})
        self.assertEqual(first_page.status_code, 200, first_page.text)
        self.assertEqual(first_page.headers["x-total-count"], "5")
        self.assertEqual(
            [teacher["id"] for teacher in first_page.json()],
            teacher_ids[:2],
        )
        self.assertEqual(
            [teacher["id"] for teacher in second_page.json()],
            teacher_ids[2:4],
        )
        self.assertEqual(
            self.client.get("/teachers/degrees").json(),
            ["Master"],
        )
        invalid_limit = self.client.get("/teachers", params={"limit": 201})
        self.assertEqual(invalid_limit.status_code, 422)

    def test_teacher_export_includes_records_beyond_the_first_page(self) -> None:
        for index in range(1, 53):
            self.create_teacher(f"EXP{index:03d}")
        response = self.client.get("/teachers/export.xlsx")
        self.assertEqual(response.status_code, 200, response.text)
        workbook = load_workbook(BytesIO(response.content), read_only=True)
        rows = list(workbook["Giang vien"].iter_rows(values_only=True))
        workbook.close()
        self.assertEqual(len(rows), 53)
        self.assertIn("EXP052", [row[0] for row in rows[1:]])

    def test_session_cookie_secure_flag_follows_https_and_override(self) -> None:
        http_response = self.client.post(
            "/auth/login",
            json={
                "username": "hr",
                "password": "Correct horse battery staple 2048!",
            },
        )
        self.assertEqual(http_response.status_code, 200, http_response.text)
        self.assertNotIn("secure", http_response.headers["set-cookie"].lower())

        with patch.dict(os.environ, {"TEACHER_MANAGEMENT_COOKIE_SECURE": "true"}):
            secure_app = create_app("sqlite://")
        with TestClient(secure_app, base_url="https://testserver") as secure_client:
            secure_password_hash = hash_password("Correct horse battery staple 2048!")
            with secure_app.state.session_factory() as db:
                db.add(
                    User(
                        username="secure-user",
                        full_name="Secure User",
                        password_hash=secure_password_hash,
                        role="hr",
                    )
                )
                db.commit()
            response = secure_client.post(
                "/auth/login",
                json={
                    "username": "secure-user",
                    "password": "Correct horse battery staple 2048!",
                },
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIn("secure", response.headers["set-cookie"].lower())

    def test_report_contracts_follow_filtered_teacher_cohort(self) -> None:
        older_teacher = self.create_teacher("OLD001").json()
        current_teacher = self.create_teacher("NEW001").json()
        today = date.today()
        with self.client.app.state.session_factory() as db:
            old_record = db.get(Teacher, older_teacher["id"])
            old_record.created_at = datetime.combine(
                today - timedelta(days=30),
                datetime.min.time(),
                tzinfo=timezone.utc,
            )
            checklist_item = ChecklistItem(
                code="report-cohort-check",
                label="Report cohort requirement",
                category="qualification",
                classification="required",
            )
            db.add(checklist_item)
            db.flush()
            db.add(
                TeacherChecklistRequirement(
                    teacher_id=current_teacher["id"],
                    checklist_item_id=checklist_item.id,
                    status="required",
                )
            )
            for index, teacher in enumerate((older_teacher, current_teacher), start=1):
                db.add(
                    EmploymentContract(
                        teacher_id=teacher["id"],
                        contract_code=f"REPORT-{index}",
                        contract_type="Fixed term",
                        starts_on=today,
                        ends_on=today + timedelta(days=10),
                        status="active",
                    )
                )
            db.commit()

        summary = self.client.get(
            "/reports/summary",
            params={"start_date": today.isoformat()},
        )
        self.assertEqual(summary.status_code, 200, summary.text)
        self.assertEqual(summary.json()["total_teachers"], 1)
        self.assertEqual(summary.json()["incomplete_profiles"], 1)
        self.assertEqual(summary.json()["expiring_or_expired_contracts"], 1)

    def test_backend_role_enforcement_and_csrf(self) -> None:
        invalid_csrf = self.client.post(
            "/departments",
            json={"code": "OPS", "name": "Operations"},
            headers={"X-CSRF-Token": "invalid"},
        )
        self.assertEqual(invalid_csrf.status_code, 403)

        admin = self.login("admin")
        response = self.client.post(
            "/users",
            json={
                "username": "new-user",
                "full_name": "New User",
                "password": "Another safe password 456!",
                "role": "hr",
            },
            headers={"X-CSRF-Token": admin["csrf_token"]},
        )
        self.assertEqual(response.status_code, 201, response.text)
        account_id = response.json()["id"]
        updated_account = self.client.patch(
            f"/users/{account_id}",
            json={
                "full_name": "Updated User",
                "role": "manager",
                "managed_department_id": self.department_id,
            },
            headers={"X-CSRF-Token": admin["csrf_token"]},
        )
        self.assertEqual(updated_account.status_code, 200, updated_account.text)
        self.assertEqual(updated_account.json()["full_name"], "Updated User")
        self.assertEqual(updated_account.json()["role"], "manager")
        self.assertEqual(
            self.client.post(
                "/departments",
                json={"code": "HR", "name": "Human Resources"},
                headers={"X-CSRF-Token": admin["csrf_token"]},
            ).status_code,
            403,
        )
        manager = self.login("manager")
        self.assertEqual(self.client.get("/teachers").status_code, 403)
        self.assertEqual(
            self.client.get("/teachers/1/checklist-requirements").status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                "/reports/export.xlsx",
                headers={"X-CSRF-Token": manager["csrf_token"]},
            ).status_code,
            200,
        )

    def test_lecturer_account_scope_and_document_review(self) -> None:
        teacher_id = self.create_teacher().json()["id"]
        other_teacher_id = self.create_teacher("T002").json()["id"]
        checklist = self.client.post(
            "/checklist-items",
            json={
                "code": "lecturer-upload-proof",
                "label": "Minh chứng giảng viên",
                "category": "qualification",
                "classification": "required",
                "applicability": "Áp dụng cho hồ sơ này.",
            },
            headers=self.headers(),
        )
        self.assertEqual(checklist.status_code, 201, checklist.text)
        self.assertEqual(
            self.client.patch(
                f"/teachers/{teacher_id}/checklist-requirements/{checklist.json()['id']}",
                json={"status": "required"},
                headers=self.headers(),
            ).status_code,
            200,
        )
        other_document = self.client.post(
            f"/teachers/{other_teacher_id}/documents",
            files={"file": ("other.pdf", b"%PDF-1.4\nother", "application/pdf")},
            headers=self.headers(),
        )
        self.assertEqual(other_document.status_code, 201, other_document.text)

        admin = self.login("admin")
        self.csrf = str(admin["csrf_token"])
        linkable = self.client.get("/users/linkable-teachers")
        self.assertEqual(linkable.status_code, 200, linkable.text)
        self.assertEqual(
            {teacher["id"] for teacher in linkable.json()},
            {teacher_id, other_teacher_id},
        )
        account = self.client.post(
            "/users",
            json={
                "username": "lecturer-one",
                "full_name": "Lecturer One",
                "password": "Another safe password 456!",
                "role": "lecturer",
                "teacher_id": teacher_id,
            },
            headers=self.headers(),
        )
        self.assertEqual(account.status_code, 201, account.text)
        self.assertEqual(account.json()["teacher_id"], teacher_id)
        duplicate = self.client.post(
            "/users",
            json={
                "username": "lecturer-duplicate",
                "full_name": "Duplicate Lecturer",
                "password": "Another safe password 789!",
                "role": "lecturer",
                "teacher_id": teacher_id,
            },
            headers=self.headers(),
        )
        self.assertEqual(duplicate.status_code, 409)
        available = self.client.get("/users/linkable-teachers")
        self.assertEqual(
            {teacher["id"] for teacher in available.json()},
            {other_teacher_id},
        )

        lecturer = self.login("lecturer-one", "Another safe password 456!")
        self.csrf = str(lecturer["csrf_token"])
        self.assertEqual(lecturer["teacher_id"], teacher_id)
        self.assertEqual(
            self.client.get("/lecturer/profile").json()["id"], teacher_id
        )
        self.assertEqual(
            self.client.get("/lecturer/profile").json()["department_name"],
            "Information Technology",
        )
        self.assertEqual(self.client.get("/notifications").status_code, 200)
        self.assertEqual(self.client.get("/teachers").status_code, 403)
        self.assertEqual(
            self.client.get(f"/teachers/{other_teacher_id}/documents").status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                f"/documents/{other_document.json()['id']}/download"
            ).status_code,
            404,
        )
        first_upload = self.client.post(
            f"/teachers/{teacher_id}/documents",
            data={"checklist_item_id": checklist.json()["id"]},
            files={"file": ("proof.pdf", b"%PDF-1.4\nproof", "application/pdf")},
            headers=self.headers(),
        )
        self.assertEqual(first_upload.status_code, 201, first_upload.text)
        self.assertEqual(first_upload.json()["review_status"], "pending")
        self.assertIn(
            "Minh chứng giảng viên",
            self.client.get(f"/teachers/{teacher_id}/completeness").json()["missing"],
        )
        self.assertEqual(
            self.client.post(
                f"/teachers/{other_teacher_id}/documents",
                data={"checklist_item_id": checklist.json()["id"]},
                files={"file": ("proof.pdf", b"%PDF-1.4\nproof", "application/pdf")},
                headers=self.headers(),
            ).status_code,
            404,
        )

        self.assertEqual(
            self.client.post("/auth/logout", headers=self.headers()).status_code,
            200,
        )

        hr = self.login("hr")
        self.csrf = str(hr["csrf_token"])
        no_reason = self.client.patch(
            f"/documents/{first_upload.json()['id']}/review",
            json={"review_status": "rejected"},
            headers=self.headers(),
        )
        self.assertEqual(no_reason.status_code, 422)
        rejected = self.client.patch(
            f"/documents/{first_upload.json()['id']}/review",
            json={"review_status": "rejected", "reason": "Tệp chưa rõ nội dung."},
            headers=self.headers(),
        )
        self.assertEqual(rejected.status_code, 200, rejected.text)
        self.assertEqual(rejected.json()["review_status"], "rejected")
        self.assertEqual(
            self.client.patch(
                f"/documents/{first_upload.json()['id']}/review",
                json={"review_status": "approved"},
                headers=self.headers(),
            ).status_code,
            409,
        )

        lecturer = self.login("lecturer-one", "Another safe password 456!")
        self.csrf = str(lecturer["csrf_token"])
        second_upload = self.client.post(
            f"/teachers/{teacher_id}/documents",
            data={"checklist_item_id": checklist.json()["id"]},
            files={"file": ("proof.pdf", b"%PDF-1.4\nproof2", "application/pdf")},
            headers=self.headers(),
        )
        self.assertEqual(second_upload.status_code, 201, second_upload.text)
        self.assertEqual(
            self.client.patch(
                f"/documents/{second_upload.json()['id']}/review",
                json={"review_status": "approved"},
                headers=self.headers(),
            ).status_code,
            403,
        )
        self.client.post("/auth/logout", headers=self.headers())

        hr = self.login("hr")
        self.csrf = str(hr["csrf_token"])
        approved = self.client.patch(
            f"/documents/{second_upload.json()['id']}/review",
            json={"review_status": "approved"},
            headers=self.headers(),
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertTrue(
            self.client.get(f"/teachers/{teacher_id}/completeness").json()["is_complete"]
        )
        self.client.post("/auth/logout", headers=self.headers())

        lecturer = self.login("lecturer-one", "Another safe password 456!")
        self.csrf = str(lecturer["csrf_token"])
        self.assertEqual(
            self.client.delete(
                f"/documents/{second_upload.json()['id']}",
                headers=self.headers(),
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.delete(
                f"/documents/{other_document.json()['id']}",
                headers=self.headers(),
            ).status_code,
            404,
        )
        replaceable_upload = self.client.post(
            f"/teachers/{teacher_id}/documents",
            data={"checklist_item_id": checklist.json()["id"]},
            files={
                "file": (
                    "replaceable.pdf",
                    b"%PDF-1.4\nreplaceable",
                    "application/pdf",
                )
            },
            headers=self.headers(),
        )
        self.assertEqual(
            replaceable_upload.status_code, 201, replaceable_upload.text
        )
        withdrawn = self.client.delete(
            f"/documents/{replaceable_upload.json()['id']}",
            headers=self.headers(),
        )
        self.assertEqual(withdrawn.status_code, 200, withdrawn.text)
        self.assertEqual(withdrawn.json()["review_status"], "withdrawn")
        self.assertTrue(
            self.client.get(
                f"/teachers/{teacher_id}/completeness"
            ).json()["is_complete"]
        )
        self.client.post("/auth/logout", headers=self.headers())
        hr = self.login("hr")
        self.csrf = str(hr["csrf_token"])
        self.assertEqual(
            self.client.patch(
                f"/documents/{replaceable_upload.json()['id']}/review",
                json={"review_status": "approved"},
                headers=self.headers(),
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.post(
                f"/documents/{replaceable_upload.json()['id']}/analysis",
                headers=self.headers(),
            ).status_code,
            409,
        )
        self.client.post("/auth/logout", headers=self.headers())
        lecturer = self.login("lecturer-one", "Another safe password 456!")
        self.csrf = str(lecturer["csrf_token"])
        replacement_upload = self.client.post(
            f"/teachers/{teacher_id}/documents",
            data={"checklist_item_id": checklist.json()["id"]},
            files={
                "file": (
                    "replacement.pdf",
                    b"%PDF-1.4\nreplacement",
                    "application/pdf",
                )
            },
            headers=self.headers(),
        )
        self.assertEqual(
            replacement_upload.status_code, 201, replacement_upload.text
        )
        self.assertEqual(replacement_upload.json()["review_status"], "pending")
        self.client.post("/auth/logout", headers=self.headers())
        with self.client.app.state.session_factory() as db:
            withdrawn_document = db.get(
                EvidenceDocument, replaceable_upload.json()["id"]
            )
            self.assertTrue(
                (
                    self.client.app.state.upload_dir
                    / withdrawn_document.stored_name
                ).is_file()
            )
            self.assertIsNotNone(
                db.scalar(
                    select(AuditLog).where(
                        AuditLog.action == "document_withdrawn",
                        AuditLog.entity_id
                        == str(replaceable_upload.json()["id"]),
                    )
                )
            )

    def test_notifications_are_persistent_available_to_all_roles_and_private(self) -> None:
        teacher = self.create_teacher().json()
        teacher_id = teacher["id"]
        with TestClient(self.client.app) as admin_client:
            admin_response = admin_client.post(
                "/auth/login",
                json={
                    "username": "admin",
                    "password": "Correct horse battery staple 2048!",
                },
            )
            self.assertEqual(admin_response.status_code, 200, admin_response.text)
            admin_session = admin_response.json()
            admin_headers = {"X-CSRF-Token": admin_session["csrf_token"]}
            users = admin_client.get("/users").json()
            manager_user = next(user for user in users if user["role"] == "manager")
            assigned = admin_client.patch(
                f"/users/{manager_user['id']}",
                json={"managed_department_id": self.department_id},
                headers=admin_headers,
            )
            self.assertEqual(assigned.status_code, 200, assigned.text)
            self.assertEqual(
                assigned.json()["managed_department_id"], self.department_id
            )
            account = admin_client.post(
                "/users",
                json={
                    "username": "notification-lecturer",
                    "full_name": "Notification Lecturer",
                    "password": "Another safe password 456!",
                    "role": "lecturer",
                    "teacher_id": teacher_id,
                },
                headers=admin_headers,
            )
            self.assertEqual(account.status_code, 201, account.text)
            admin_notifications = admin_client.get("/notifications")
            self.assertEqual(admin_notifications.status_code, 200)
            self.assertIn(
                "Hồ sơ giảng viên mới",
                [item["title"] for item in admin_notifications.json()],
            )
            self.assertEqual(
                admin_client.post(
                    "/notifications/refresh", headers=admin_headers
                ).status_code,
                200,
            )

            with TestClient(self.client.app) as manager_client:
                manager_response = manager_client.post(
                    "/auth/login",
                    json={
                        "username": "manager",
                        "password": "Correct horse battery staple 2048!",
                    },
                )
                self.assertEqual(manager_response.status_code, 200)
                manager_headers = {
                    "X-CSRF-Token": manager_response.json()["csrf_token"]
                }
                manager_notifications = manager_client.get("/notifications")
                self.assertEqual(manager_notifications.status_code, 200)
                self.assertIn(
                    "Nhân sự mới thuộc đơn vị phụ trách",
                    [item["title"] for item in manager_notifications.json()],
                )
                self.assertEqual(
                    manager_client.post(
                        "/notifications/refresh", headers=manager_headers
                    ).status_code,
                    200,
                )

                with TestClient(self.client.app) as lecturer_client:
                    lecturer_response = lecturer_client.post(
                        "/auth/login",
                        json={
                            "username": "notification-lecturer",
                            "password": "Another safe password 456!",
                        },
                    )
                    self.assertEqual(lecturer_response.status_code, 200)
                    lecturer_headers = {
                        "X-CSRF-Token": lecturer_response.json()["csrf_token"]
                    }
                    lecturer_notifications = lecturer_client.get("/notifications")
                    self.assertEqual(lecturer_notifications.status_code, 200)
                    self.assertEqual(
                        lecturer_client.post(
                            "/notifications/refresh", headers=lecturer_headers
                        ).status_code,
                        200,
                    )
                    account_notification = next(
                        item
                        for item in lecturer_notifications.json()
                        if item["title"] == "Tài khoản giảng viên đã được cấp"
                    )
                    self.assertFalse(account_notification["is_read"])
                    self.assertEqual(
                        manager_client.patch(
                            f"/notifications/{account_notification['id']}/read",
                            headers=manager_headers,
                        ).status_code,
                        404,
                    )
                    marked = lecturer_client.patch(
                        f"/notifications/{account_notification['id']}/read",
                        headers=lecturer_headers,
                    )
                    self.assertEqual(marked.status_code, 200, marked.text)
                    updated = lecturer_client.get("/notifications").json()
                    self.assertTrue(
                        next(
                            item
                            for item in updated
                            if item["id"] == account_notification["id"]
                        )["is_read"]
                    )
                    self.assertEqual(
                        lecturer_client.post(
                            "/notifications/read-all", headers=lecturer_headers
                        ).status_code,
                        200,
                    )
                    self.assertTrue(
                        all(
                            item["is_read"]
                            for item in lecturer_client.get(
                                "/notifications"
                            ).json()
                        )
                    )
                    self.assertEqual(
                        self.client.get("/notifications").status_code, 200
                    )
                    self.assertEqual(
                        self.client.post(
                            "/notifications/refresh", headers=self.headers()
                        ).status_code,
                        200,
                    )

    def test_notification_workflows_cover_documents_changes_contracts_and_history(
        self,
    ) -> None:
        teacher = self.create_teacher().json()
        teacher_id = teacher["id"]
        upload_checklist = self.client.post(
            "/checklist-items",
            json={
                "code": "notification-upload-item",
                "label": "Tài liệu cần rà soát",
                "category": "qualification",
                "classification": "required",
                "applicability": "Áp dụng cho hồ sơ này.",
            },
            headers=self.headers(),
        )
        self.assertEqual(upload_checklist.status_code, 201, upload_checklist.text)
        admin_context = TestClient(self.client.app)
        manager_context = TestClient(self.client.app)
        lecturer_context = TestClient(self.client.app)
        with admin_context as admin_client, manager_context as manager_client, lecturer_context as lecturer_client:
            admin_response = admin_client.post(
                "/auth/login",
                json={
                    "username": "admin",
                    "password": "Correct horse battery staple 2048!",
                },
            )
            admin_headers = {
                "X-CSRF-Token": admin_response.json()["csrf_token"]
            }
            account = admin_client.post(
                "/users",
                json={
                    "username": "workflow-lecturer",
                    "full_name": "Workflow Lecturer",
                    "password": "Another safe password 456!",
                    "role": "lecturer",
                    "teacher_id": teacher_id,
                },
                headers=admin_headers,
            )
            self.assertEqual(account.status_code, 201, account.text)

            manager_response = manager_client.post(
                "/auth/login",
                json={
                    "username": "manager",
                    "password": "Correct horse battery staple 2048!",
                },
            )
            self.assertEqual(manager_response.status_code, 200)
            manager_headers = {
                "X-CSRF-Token": manager_response.json()["csrf_token"]
            }
            lecturer_response = lecturer_client.post(
                "/auth/login",
                json={
                    "username": "workflow-lecturer",
                    "password": "Another safe password 456!",
                },
            )
            self.assertEqual(lecturer_response.status_code, 200)
            lecturer_headers = {
                "X-CSRF-Token": lecturer_response.json()["csrf_token"]
            }

            upload = lecturer_client.post(
                f"/teachers/{teacher_id}/documents",
                data={"checklist_item_id": str(upload_checklist.json()["id"])},
                files={"file": ("notification.pdf", b"%PDF-1.4\nproof", "application/pdf")},
                headers=lecturer_headers,
            )
            self.assertEqual(upload.status_code, 201, upload.text)
            hr_items = self.client.get("/notifications").json()
            self.assertIn(
                "Tài liệu mới chờ rà soát", [item["title"] for item in hr_items]
            )

            reviewed = self.client.patch(
                f"/documents/{upload.json()['id']}/review",
                json={"review_status": "rejected", "reason": "Thiếu trang ký."},
                headers=self.headers(),
            )
            self.assertEqual(reviewed.status_code, 200, reviewed.text)
            lecturer_items = lecturer_client.get("/notifications").json()
            self.assertIn(
                "Tài liệu cần được bổ sung",
                [item["title"] for item in lecturer_items],
            )

            submitted = lecturer_client.post(
                f"/teachers/{teacher_id}/change-requests",
                json={
                    "change_type": "Thay đổi chức danh",
                    "proposed_value": {"academic_title": "Giảng viên chính"},
                    "reason": "Đề nghị cập nhật chức danh.",
                    "effective_on": (date.today() + timedelta(days=1)).isoformat(),
                },
                headers=lecturer_headers,
            )
            self.assertEqual(submitted.status_code, 201, submitted.text)
            request_id = submitted.json()["id"]
            self.assertIn(
                "Giảng viên gửi yêu cầu thay đổi",
                [item["title"] for item in self.client.get("/notifications").json()],
            )
            manager_items = manager_client.get("/notifications").json()
            self.assertIn(
                "Đề xuất nhân sự cần xem xét",
                [item["title"] for item in manager_items],
            )
            manager_client.post(
                "/notifications/refresh", headers=manager_headers
            )
            manager_items = manager_client.get("/notifications").json()
            self.assertEqual(
                sum(
                    item["title"] == "Đề xuất nhân sự cần xem xét"
                    and f"#{request_id}" in item["message"]
                    for item in manager_items
                ),
                1,
            )
            decision = manager_client.post(
                f"/change-requests/{request_id}/decision",
                json={"action": "approve"},
                headers=manager_headers,
            )
            self.assertEqual(decision.status_code, 200, decision.text)
            self.assertIn(
                "Yêu cầu thay đổi đã được duyệt",
                [item["title"] for item in lecturer_client.get("/notifications").json()],
            )
            rejected_request = lecturer_client.post(
                f"/teachers/{teacher_id}/change-requests",
                json={
                    "change_type": "Thay đổi trình độ",
                    "proposed_value": {"academic_degree": "Doctor"},
                    "reason": "Đề nghị cập nhật trình độ.",
                },
                headers=lecturer_headers,
            )
            self.assertEqual(
                rejected_request.status_code, 201, rejected_request.text
            )
            rejected = manager_client.post(
                f"/change-requests/{rejected_request.json()['id']}/decision",
                json={"action": "reject", "reason": "Chưa đủ căn cứ."},
                headers=manager_headers,
            )
            self.assertEqual(rejected.status_code, 200, rejected.text)
            self.assertIn(
                "Yêu cầu thay đổi bị từ chối",
                [item["title"] for item in lecturer_client.get("/notifications").json()],
            )
            needs_info_request = lecturer_client.post(
                f"/teachers/{teacher_id}/change-requests",
                json={
                    "change_type": "Thay đổi trình độ",
                    "proposed_value": {"academic_degree": "PhD"},
                    "reason": "Đề nghị cập nhật trình độ.",
                },
                headers=lecturer_headers,
            )
            self.assertEqual(
                needs_info_request.status_code, 201, needs_info_request.text
            )
            needs_info = manager_client.post(
                f"/change-requests/{needs_info_request.json()['id']}/decision",
                json={"action": "request_info", "reason": "Vui lòng bổ sung minh chứng."},
                headers=manager_headers,
            )
            self.assertEqual(needs_info.status_code, 200, needs_info.text)
            self.assertIn(
                "Yêu cầu thay đổi cần bổ sung",
                [item["title"] for item in lecturer_client.get("/notifications").json()],
            )
            resubmitted = lecturer_client.patch(
                f"/change-requests/{needs_info_request.json()['id']}",
                json={
                    "proposed_value": {"academic_degree": "PhD"},
                    "reason": "Đã bổ sung minh chứng.",
                },
                headers=lecturer_headers,
            )
            self.assertEqual(resubmitted.status_code, 200, resubmitted.text)
            self.assertIn(
                "Giảng viên đã bổ sung yêu cầu thay đổi",
                [item["title"] for item in self.client.get("/notifications").json()],
            )

            contract = self.client.post(
                f"/teachers/{teacher_id}/contracts",
                json={
                    "contract_code": "NOTICE-001",
                    "contract_type": "Fixed term",
                    "starts_on": date.today().isoformat(),
                    "ends_on": (date.today() + timedelta(days=5)).isoformat(),
                },
                headers=self.headers(),
            )
            self.assertEqual(contract.status_code, 201, contract.text)
            for _ in range(2):
                refreshed = self.client.post(
                    "/notifications/refresh", headers=self.headers()
                )
                self.assertEqual(refreshed.status_code, 200, refreshed.text)
            hr_items = self.client.get("/notifications").json()
            self.assertEqual(
                sum(
                    item["title"] == "Hợp đồng sắp hoặc đã hết hạn"
                    and "NOTICE-001" in item["message"]
                    for item in hr_items
                ),
                1,
            )

            with self.client.app.state.session_factory() as db:
                current_history = db.scalar(
                    select(WorkHistory).where(
                        WorkHistory.teacher_id == teacher_id,
                        WorkHistory.ends_on.is_(None),
                    )
                )
                current_history.ends_on = date.today() + timedelta(days=1)
                db.commit()
            history = self.client.post(
                f"/teachers/{teacher_id}/work-history",
                json={
                    "department_id": self.department_id,
                    "position_title": "Giảng viên",
                    "starts_on": (date.today() + timedelta(days=2)).isoformat(),
                    "reason": "Cập nhật quá trình công tác.",
                },
                headers=self.headers(),
            )
            self.assertEqual(history.status_code, 201, history.text)
            self.assertIn(
                "Quá trình công tác được cập nhật",
                [item["title"] for item in lecturer_client.get("/notifications").json()],
            )
            self.assertIn(
                "Quá trình công tác được cập nhật",
                [item["title"] for item in manager_client.get("/notifications").json()],
            )

            checklist = self.client.post(
                "/checklist-items",
                json={
                    "code": "notification-required-proof",
                    "label": "Minh chứng bổ sung",
                    "category": "qualification",
                    "classification": "optional",
                    "applicability": "Theo yêu cầu rà soát.",
                },
                headers=self.headers(),
            )
            self.assertEqual(checklist.status_code, 201, checklist.text)
            requirement = self.client.patch(
                f"/teachers/{teacher_id}/checklist-requirements/{checklist.json()['id']}",
                json={"status": "required"},
                headers=self.headers(),
            )
            self.assertEqual(requirement.status_code, 200, requirement.text)
            self.assertIn(
                "Hồ sơ cần bổ sung tài liệu",
                [item["title"] for item in lecturer_client.get("/notifications").json()],
            )

            update = self.client.patch(
                f"/teachers/{teacher_id}",
                json={"phone": "0912345678"},
                headers=self.headers(),
            )
            self.assertEqual(update.status_code, 200, update.text)
            self.assertIn(
                "Hồ sơ nhân sự được cập nhật",
                [item["title"] for item in manager_client.get("/notifications").json()],
            )
            other_department = self.client.post(
                "/departments",
                json={"code": "OTHER", "name": "Other Department"},
                headers=self.headers(),
            )
            self.assertEqual(other_department.status_code, 201, other_department.text)
            unrelated_teacher = self.create_teacher(
                "OTHER001", department_id=other_department.json()["id"]
            )
            self.assertEqual(unrelated_teacher.status_code, 201)
            self.assertEqual(
                self.client.patch(
                    f"/teachers/{unrelated_teacher.json()['id']}",
                    json={"phone": "0911111111"},
                    headers=self.headers(),
                ).status_code,
                200,
            )
            manager_messages = [
                item["message"] for item in manager_client.get("/notifications").json()
            ]
            self.assertFalse(any("OTHER001" in message for message in manager_messages))

    def test_demo_lecturer_seed_account_matches_existing_teacher(self) -> None:
        teacher_response = self.create_teacher(
            "DEMO-GV-001", full_name="Nguyễn An Bình"
        )
        self.assertEqual(teacher_response.status_code, 201, teacher_response.text)
        teacher = teacher_response.json()

        admin = self.login("admin")
        seed_api = Api(self.client)
        seed_api.csrf_token = str(admin["csrf_token"])
        passwords: dict[str, str] = {}
        with redirect_stdout(StringIO()):
            ensure_lecturer_accounts(seed_api, {"DEMO-GV-001": teacher}, passwords)
            ensure_lecturer_accounts(seed_api, {"DEMO-GV-001": teacher}, passwords)
        seeded_accounts = [
            user
            for user in seed_api.request("GET", "/users").json()
            if user["username"] == "lecturer_demo1"
        ]
        self.assertEqual(len(seeded_accounts), 1)
        self.assertEqual(seeded_accounts[0]["teacher_id"], teacher["id"])

        lecturer = self.login("lecturer_demo1", passwords["lecturer_demo1"])
        self.assertEqual(lecturer["role"], "lecturer")
        self.assertEqual(lecturer["teacher_id"], teacher["id"])
        profile = self.client.get("/lecturer/profile")
        self.assertEqual(profile.status_code, 200, profile.text)
        self.assertEqual(profile.json()["employee_code"], "DEMO-GV-001")
        self.assertEqual(profile.json()["full_name"], "Nguyễn An Bình")

    def test_account_access_changes_revoke_all_existing_sessions(self) -> None:
        def sign_in(username: str) -> tuple[dict[str, object], str]:
            response = self.client.post(
                "/auth/login",
                json={
                    "username": username,
                    "password": "Correct horse battery staple 2048!",
                },
            )
            self.assertEqual(response.status_code, 200, response.text)
            session_token = response.cookies.get(SESSION_COOKIE)
            self.assertIsNotNone(session_token)
            return response.json(), session_token

        _, first_hr_session = sign_in("hr")
        _, second_hr_session = sign_in("hr")
        admin, admin_session = sign_in("admin")
        admin_headers = {
            "X-CSRF-Token": admin["csrf_token"],
            "Cookie": f"{SESSION_COOKIE}={admin_session}",
        }
        users = self.client.get("/users", headers=admin_headers)
        self.assertEqual(users.status_code, 200, users.text)
        hr_id = next(user["id"] for user in users.json() if user["username"] == "hr")

        deactivated = self.client.patch(
            f"/users/{hr_id}",
            json={"is_active": False},
            headers=admin_headers,
        )
        self.assertEqual(deactivated.status_code, 200, deactivated.text)
        reactivated = self.client.patch(
            f"/users/{hr_id}",
            json={"is_active": True},
            headers=admin_headers,
        )
        self.assertEqual(reactivated.status_code, 200, reactivated.text)
        for old_session in (first_hr_session, second_hr_session):
            with self.subTest(session="revoked after reactivation"):
                response = self.client.get(
                    "/auth/session",
                    headers={"Cookie": f"{SESSION_COOKIE}={old_session}"},
                )
                self.assertEqual(response.status_code, 401)

        _, previous_hr_session = sign_in("hr")
        role_change = self.client.patch(
            f"/users/{hr_id}",
            json={
                "role": "manager",
                "managed_department_id": self.department_id,
            },
            headers=admin_headers,
        )
        self.assertEqual(role_change.status_code, 200, role_change.text)
        stale_role_session = self.client.get(
            "/auth/session",
            headers={"Cookie": f"{SESSION_COOKIE}={previous_hr_session}"},
        )
        self.assertEqual(stale_role_session.status_code, 401)
        manager, manager_session = sign_in("hr")
        self.assertEqual(manager["role"], "manager")
        manager_headers = {
            "X-CSRF-Token": manager["csrf_token"],
            "Cookie": f"{SESSION_COOKIE}={manager_session}",
        }
        self.assertEqual(self.client.get("/teachers", headers=manager_headers).status_code, 403)

    def test_department_hierarchy_and_deactivation(self) -> None:
        child = self.client.post(
            "/departments",
            json={"code": "SYS", "name": "Systems", "parent_id": self.department_id},
            headers=self.headers(),
        )
        self.assertEqual(child.status_code, 201, child.text)
        self.assertEqual(child.json()["parent_id"], self.department_id)

        cycle = self.client.patch(
            f"/departments/{self.department_id}",
            json={"parent_id": child.json()["id"]},
            headers=self.headers(),
        )
        self.assertEqual(cycle.status_code, 422)

        response = self.client.patch(
            f"/departments/{self.department_id}",
            json={"is_active": False},
            headers=self.headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.get("/departments").json()[0]["id"],
            child.json()["id"],
        )

    def test_important_changes_are_approved_and_preserve_history(self) -> None:
        created = self.create_teacher()
        teacher_id = created.json()["id"]
        new_department = self.client.post(
            "/departments",
            json={"code": "LAW", "name": "Law"},
            headers=self.headers(),
        ).json()
        direct_change = self.client.patch(
            f"/teachers/{teacher_id}",
            json={"department_id": new_department["id"]},
            headers=self.headers(),
        )
        self.assertEqual(direct_change.status_code, 409)

        effective_on = date.today() + timedelta(days=1)
        request_response = self.client.post(
            f"/teachers/{teacher_id}/change-requests",
            json={
                "change_type": "department_transfer",
                "current_value": {"department_id": 999},
                "proposed_value": {"department_id": new_department["id"]},
                "reason": "Approved organizational transfer",
                "effective_on": effective_on.isoformat(),
            },
            headers=self.headers(),
        )
        self.assertEqual(request_response.status_code, 201, request_response.text)
        request_id = request_response.json()["id"]
        self.assertEqual(
            request_response.json()["current_value"]["department_id"],
            self.department_id,
        )

        own_decision = self.client.post(
            f"/change-requests/{request_id}/decision",
            json={"action": "approve"},
            headers=self.headers(),
        )
        self.assertEqual(own_decision.status_code, 403)

        manager = self.login("manager")
        decision = self.client.post(
            f"/change-requests/{request_id}/decision",
            json={"action": "approve"},
            headers={"X-CSRF-Token": manager["csrf_token"]},
        )
        self.assertEqual(decision.status_code, 200, decision.text)
        self.assertEqual(decision.json()["status"], "approved")

        self.login("hr")
        teacher = self.client.get(f"/teachers/{teacher_id}")
        self.assertEqual(teacher.json()["department_id"], new_department["id"])
        history = self.client.get(f"/teachers/{teacher_id}/work-history")
        self.assertEqual(len(history.json()), 2)
        self.assertEqual(
            history.json()[0]["ends_on"],
            (effective_on - timedelta(days=1)).isoformat(),
        )
        self.assertEqual(history.json()[1]["starts_on"], effective_on.isoformat())
        manager = self.login("manager")
        repeated = self.client.post(
            f"/change-requests/{request_id}/decision",
            json={"action": "approve"},
            headers={"X-CSRF-Token": manager["csrf_token"]},
        )
        self.assertEqual(repeated.status_code, 409)

    def test_manager_change_requests_include_teacher_names_and_require_reasons(self) -> None:
        teacher = self.create_teacher(
            employee_code="REQUEST-001",
            full_name="Request Test Lecturer",
            academic_title="Lecturer",
        ).json()
        request_ids = []
        for proposed_title in ("Senior Lecturer", "Assistant Lecturer"):
            response = self.client.post(
                f"/teachers/{teacher['id']}/change-requests",
                json={
                    "change_type": "academic_title",
                    "current_value": {},
                    "proposed_value": {"academic_title": proposed_title},
                    "reason": "Test manager decision workflow",
                },
                headers=self.headers(),
            )
            self.assertEqual(response.status_code, 201, response.text)
            request_ids.append(response.json()["id"])

        manager = self.login("manager")
        manager_headers = {"X-CSRF-Token": manager["csrf_token"]}
        requests = self.client.get("/change-requests", headers=manager_headers)
        self.assertEqual(requests.status_code, 200, requests.text)
        request = next(item for item in requests.json() if item["id"] == request_ids[0])
        self.assertEqual(request["teacher_employee_code"], "REQUEST-001")
        self.assertEqual(request["teacher_full_name"], "Request Test Lecturer")

        for request_id, action, reason in (
            (request_ids[0], "reject", "Proposal needs more evidence."),
            (request_ids[1], "request_info", "Please clarify the effective date."),
        ):
            decision = self.client.post(
                f"/change-requests/{request_id}/decision",
                json={"action": action, "reason": reason},
                headers=manager_headers,
            )
            self.assertEqual(decision.status_code, 200, decision.text)
            self.assertEqual(decision.json()["resolution_reason"], reason)
            self.assertEqual(
                decision.json()["status"],
                "rejected" if action == "reject" else "needs_info",
            )

    def test_manager_scope_is_one_root_faculty_including_subdepartments(self) -> None:
        child = self.client.post(
            "/departments",
            json={
                "code": "IT-CHILD",
                "name": "Information Technology Department",
                "parent_id": self.department_id,
            },
            headers=self.headers(),
        ).json()
        grandchild = self.client.post(
            "/departments",
            json={
                "code": "IT-SUBCHILD",
                "name": "Information Systems Unit",
                "parent_id": child["id"],
            },
            headers=self.headers(),
        ).json()
        other_faculty = self.client.post(
            "/departments",
            json={"code": "LAW", "name": "Law Faculty"},
            headers=self.headers(),
        ).json()
        other_child = self.client.post(
            "/departments",
            json={
                "code": "LAW-CHILD",
                "name": "Law Department",
                "parent_id": other_faculty["id"],
            },
            headers=self.headers(),
        ).json()
        in_scope_teacher = self.create_teacher(
            "SCOPE-IT",
            full_name="Scoped Faculty Teacher",
            department_id=grandchild["id"],
        ).json()
        outside_teacher = self.create_teacher(
            "SCOPE-LAW",
            full_name="Outside Faculty Teacher",
            department_id=other_child["id"],
        ).json()

        admin = self.login("admin")
        admin_headers = {"X-CSRF-Token": admin["csrf_token"]}
        missing_faculty = self.client.post(
            "/users",
            json={
                "username": "manager-no-faculty",
                "full_name": "Manager Without Faculty",
                "password": "Another safe password 456!",
                "role": "manager",
            },
            headers=admin_headers,
        )
        self.assertEqual(missing_faculty.status_code, 422)
        child_assignment = self.client.post(
            "/users",
            json={
                "username": "manager-child-faculty",
                "full_name": "Manager Child Assignment",
                "password": "Another safe password 456!",
                "role": "manager",
                "managed_department_id": child["id"],
            },
            headers=admin_headers,
        )
        self.assertEqual(child_assignment.status_code, 422)
        same_faculty_manager = self.client.post(
            "/users",
            json={
                "username": "manager-deputy",
                "full_name": "Manager Deputy",
                "password": "Another safe password 456!",
                "role": "manager",
                "managed_department_id": self.department_id,
            },
            headers=admin_headers,
        )
        self.assertEqual(same_faculty_manager.status_code, 201)
        self.assertEqual(
            same_faculty_manager.json()["managed_department_id"],
            self.department_id,
        )
        updated_manager = self.client.patch(
            f"/users/{same_faculty_manager.json()['id']}",
            json={"managed_department_id": other_faculty["id"]},
            headers=admin_headers,
        )
        self.assertEqual(updated_manager.status_code, 200, updated_manager.text)
        self.assertEqual(
            updated_manager.json()["managed_department_id"], other_faculty["id"]
        )

        hr = self.login("hr")
        hr_headers = {"X-CSRF-Token": hr["csrf_token"]}
        scoped_request = self.client.post(
            f"/teachers/{in_scope_teacher['id']}/change-requests",
            json={
                "change_type": "department_transfer",
                "current_value": {},
                "proposed_value": {"department_id": other_faculty["id"]},
                "reason": "Scoped request",
                "effective_on": (date.today() + timedelta(days=1)).isoformat(),
            },
            headers=hr_headers,
        )
        self.assertEqual(scoped_request.status_code, 201, scoped_request.text)
        scoped_request = scoped_request.json()
        outside_request = self.client.post(
            f"/teachers/{outside_teacher['id']}/change-requests",
            json={
                "change_type": "academic_degree",
                "current_value": {},
                "proposed_value": {"academic_degree": "Doctor"},
                "reason": "Outside request",
            },
            headers=hr_headers,
        )
        self.assertEqual(outside_request.status_code, 201, outside_request.text)
        outside_request = outside_request.json()
        manager = self.login("manager")
        manager_headers = {"X-CSRF-Token": manager["csrf_token"]}
        with self.client.app.state.session_factory() as db:
            manager_user = db.scalar(
                select(User).where(User.username == "manager")
            )
            db.add_all(
                [
                    Notification(
                        user_id=manager_user.id,
                        event_key="legacy-null-scope",
                        title="Legacy unscoped manager notification",
                        message="Must not cross the new faculty boundary.",
                        level="info",
                        target_view="reports",
                    ),
                    Notification(
                        user_id=manager_user.id,
                        event_key="other-faculty-scope",
                        title="Other faculty notification",
                        message="Must stay hidden after reassignment.",
                        level="info",
                        target_view="reports",
                        manager_faculty_id=other_faculty["id"],
                    ),
                ]
            )
            db.commit()
        visible_departments = self.client.get(
            "/departments", headers=manager_headers
        ).json()
        visible_department_ids = {item["id"] for item in visible_departments}
        self.assertEqual(
            visible_department_ids,
            {self.department_id, child["id"], grandchild["id"]},
        )
        summary = self.client.get("/reports/summary", headers=manager_headers)
        self.assertEqual(summary.status_code, 200, summary.text)
        self.assertEqual(summary.json()["total_teachers"], 1)
        self.assertEqual(
            summary.json()["filters"]["faculty_scope_id"], self.department_id
        )
        root_filtered_summary = self.client.get(
            "/reports/summary",
            params={"department_id": self.department_id},
            headers=manager_headers,
        )
        self.assertEqual(root_filtered_summary.status_code, 200)
        self.assertEqual(root_filtered_summary.json()["total_teachers"], 1)
        child_filtered_summary = self.client.get(
            "/reports/summary",
            params={"department_id": child["id"]},
            headers=manager_headers,
        )
        self.assertEqual(child_filtered_summary.status_code, 200)
        self.assertEqual(child_filtered_summary.json()["total_teachers"], 1)
        manager_notifications = self.client.get(
            "/notifications", headers=manager_headers
        ).json()
        self.assertNotIn(
            "Legacy unscoped manager notification",
            [item["title"] for item in manager_notifications],
        )
        self.assertNotIn(
            "Other faculty notification",
            [item["title"] for item in manager_notifications],
        )
        self.assertIn(
            in_scope_teacher["id"],
            {
                int(item["target_id"])
                for item in manager_notifications
                if item["title"] == "Nhân sự mới thuộc đơn vị phụ trách"
            },
        )
        self.assertNotIn(
            outside_teacher["id"],
            {
                int(item["target_id"])
                for item in manager_notifications
                if item["title"] == "Nhân sự mới thuộc đơn vị phụ trách"
            },
        )
        outside_report = self.client.get(
            "/reports/summary",
            params={"department_id": other_faculty["id"]},
            headers=manager_headers,
        )
        self.assertEqual(outside_report.status_code, 403)
        outside_export = self.client.get(
            "/reports/export.xlsx",
            params={"department_id": other_faculty["id"]},
            headers=manager_headers,
        )
        self.assertEqual(outside_export.status_code, 403)
        requests = self.client.get("/change-requests", headers=manager_headers)
        self.assertEqual(requests.status_code, 200, requests.text)
        visible_request_ids = {item["id"] for item in requests.json()}
        self.assertIn(scoped_request["id"], visible_request_ids)
        self.assertNotIn(outside_request["id"], visible_request_ids)
        denied_decision = self.client.post(
            f"/change-requests/{outside_request['id']}/decision",
            json={"action": "reject", "reason": "Outside my faculty."},
            headers=manager_headers,
        )
        self.assertEqual(denied_decision.status_code, 403)
        outgoing_decision = self.client.post(
            f"/change-requests/{scoped_request['id']}/decision",
            json={
                "action": "approve",
                "reason": "Approve transfer outside faculty.",
            },
            headers=manager_headers,
        )
        self.assertEqual(outgoing_decision.status_code, 200, outgoing_decision.text)

        manager_export = self.client.get(
            "/reports/export.xlsx", headers=manager_headers
        )
        self.assertEqual(manager_export.status_code, 200, manager_export.text)
        workbook = load_workbook(BytesIO(manager_export.content), read_only=True)
        report_rows = list(workbook["Tong hop"].iter_rows(values_only=True))
        self.assertIn(("Tổng giảng viên", 0), report_rows)
        workbook.close()

        with self.client.app.state.session_factory() as db:
            manager_user = db.scalar(
                select(User).where(User.username == "manager")
            )
            assigned_faculty = db.get(Department, self.department_id)
            second_faculty = db.get(Department, other_faculty["id"])
            manager_user.managed_departments = [assigned_faculty, second_faculty]
            db.commit()
        self.assertEqual(
            self.client.get("/departments", headers=manager_headers).json(), []
        )
        self.assertEqual(
            self.client.get(
                "/reports/summary", headers=manager_headers
            ).json()["total_teachers"],
            0,
        )

    def test_contract_alerts_checklist_and_protected_upload(self) -> None:
        teacher_id = self.create_teacher().json()["id"]
        checklist = self.client.post(
            "/checklist-items",
            json={
                "code": "degree-proof",
                "label": "Bằng cấp minh chứng",
                "category": "qualification",
                "classification": "required",
                "applicability": "Theo yêu cầu vị trí.",
            },
            headers=self.headers(),
        )
        self.assertEqual(checklist.status_code, 201, checklist.text)
        requirements = self.client.get(
            f"/teachers/{teacher_id}/checklist-requirements"
        )
        self.assertEqual(requirements.status_code, 200)
        self.assertEqual(requirements.json()[0]["status"], "review")
        incomplete = self.client.get(f"/teachers/{teacher_id}/completeness").json()
        self.assertFalse(incomplete["is_complete"])
        self.assertIn("Bằng cấp minh chứng", incomplete["needs_review"])
        requirement = self.client.patch(
            f"/teachers/{teacher_id}/checklist-requirements/{checklist.json()['id']}",
            json={"status": "not_applicable"},
            headers=self.headers(),
        )
        self.assertEqual(requirement.status_code, 200, requirement.text)
        self.assertTrue(
            self.client.get(f"/teachers/{teacher_id}/completeness").json()["is_complete"]
        )
        requirement = self.client.patch(
            f"/teachers/{teacher_id}/checklist-requirements/{checklist.json()['id']}",
            json={"status": "required"},
            headers=self.headers(),
        )
        self.assertEqual(requirement.status_code, 200, requirement.text)
        incomplete = self.client.get(f"/teachers/{teacher_id}/completeness").json()
        self.assertIn("Bằng cấp minh chứng", incomplete["missing"])

        upload = self.client.post(
            f"/teachers/{teacher_id}/documents",
            data={"checklist_item_id": checklist.json()["id"]},
            files={"file": ("degree.pdf", b"%PDF-1.4\nproof", "application/pdf")},
            headers=self.headers(),
        )
        self.assertEqual(upload.status_code, 201, upload.text)
        document_id = upload.json()["id"]
        self.assertEqual(
            self.client.get(f"/teachers/{teacher_id}/completeness").json()["is_complete"],
            True,
        )
        downloaded = self.client.get(f"/documents/{document_id}/download")
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded.content, b"%PDF-1.4\nproof")
        self.assertEqual(downloaded.headers["cache-control"], "private, no-store")

        contract = self.client.post(
            f"/teachers/{teacher_id}/contracts",
            json={
                "contract_code": "HD-001",
                "contract_type": "Fixed term",
                "starts_on": date.today().isoformat(),
                "ends_on": (date.today() + timedelta(days=10)).isoformat(),
            },
            headers=self.headers(),
        )
        self.assertEqual(contract.status_code, 201, contract.text)
        alerts = self.client.get("/contracts/alerts")
        self.assertEqual(alerts.status_code, 200)
        self.assertEqual(alerts.json()[0]["status"], "expiring")
        contract_list = self.client.get(f"/teachers/{teacher_id}/contracts")
        self.assertEqual(contract_list.json()[0]["display_status"], "expiring")

    def test_local_document_analysis_is_hr_only_and_does_not_change_review(self) -> None:
        from docx import Document

        teacher_id = self.create_teacher().json()["id"]
        word_document = Document()
        word_document.add_paragraph("Thông tin minh chứng")
        word_content = BytesIO()
        word_document.save(word_content)
        upload = self.client.post(
            f"/teachers/{teacher_id}/documents",
            files={
                "file": (
                    "evidence.docx",
                    word_content.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            headers=self.headers(),
        )
        self.assertEqual(upload.status_code, 201, upload.text)
        document_id = upload.json()["id"]

        manager = self.login("manager")
        self.csrf = str(manager["csrf_token"])
        self.assertEqual(
            self.client.post(
                f"/documents/{document_id}/analysis",
                headers=self.headers(),
            ).status_code,
            403,
        )

        hr = self.login("hr")
        self.csrf = str(hr["csrf_token"])
        analysis = {
            "summary": "Tóm tắt minh chứng",
            "extracted_information": [
                {
                    "field": "Nội dung",
                    "value": "Thông tin minh chứng",
                    "source": "[Đoạn 1]",
                }
            ],
        }
        with (
            patch("app.main.extract_document_text", return_value="verified text"),
            patch(
                "app.main.analyze_document_text",
                new_callable=AsyncMock,
                return_value=analysis,
            ) as model_call,
        ):
            response = self.client.post(
                f"/documents/{document_id}/analysis",
                headers=self.headers(),
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), analysis)
        model_call.assert_awaited_once_with("verified text")
        with self.client.app.state.session_factory() as db:
            saved_document = db.get(EvidenceDocument, document_id)
            self.assertEqual(saved_document.review_status, "approved")
            audit = db.scalar(
                select(AuditLog).where(
                    AuditLog.action == "document_analysis_requested",
                    AuditLog.entity_id == str(document_id),
                )
            )
            self.assertIsNotNone(audit)
            self.assertNotIn("Thông tin minh chứng", audit.details or "")

        invalid_contract = self.client.post(
            f"/teachers/{teacher_id}/contracts",
            json={
                "contract_code": "HD-002",
                "contract_type": "Invalid",
                "starts_on": date.today().isoformat(),
                "ends_on": (date.today() - timedelta(days=1)).isoformat(),
            },
            headers=self.headers(),
        )
        self.assertEqual(invalid_contract.status_code, 422)

    def test_profile_review_expiry_rules_and_role_access(self) -> None:
        teacher_id = self.create_teacher().json()["id"]
        expiry = date.today() + timedelta(days=10)
        qualification = self.client.post(
            f"/teachers/{teacher_id}/qualifications",
            json={
                "qualification_type": "certificate",
                "title": "Chứng chỉ ngoại ngữ",
                "issued_on": (date.today() - timedelta(days=365)).isoformat(),
                "expires_on": expiry.isoformat(),
            },
            headers=self.headers(),
        )
        self.assertEqual(qualification.status_code, 201, qualification.text)
        self.assertEqual(qualification.json()["expires_on"], expiry.isoformat())
        self.assertEqual(
            self.client.get("/settings/certificate-warning-days").json(),
            {"days": 30},
        )

        review = self.client.get(f"/profile-reviews?teacher_id={teacher_id}")
        self.assertEqual(review.status_code, 200, review.text)
        self.assertEqual(review.json()["model"]["status"], "insufficient_data")
        certificate_alerts = review.json()["items"][0]["expiring_certificates"]
        self.assertEqual(len(certificate_alerts), 1)
        self.assertEqual(certificate_alerts[0]["days_remaining"], 10)
        self.assertEqual(certificate_alerts[0]["status"], "expiring")
        self.client.post("/notifications/refresh", headers=self.headers())
        notifications = self.client.get("/notifications")
        self.assertIn(
            "Chứng chỉ sắp hoặc đã hết hạn",
            [item["title"] for item in notifications.json()],
        )

        invalid_creation = self.client.post(
            f"/teachers/{teacher_id}/qualifications",
            json={
                "qualification_type": "certificate",
                "title": "Ngày hết hạn không hợp lệ",
                "issued_on": date.today().isoformat(),
                "expires_on": (date.today() - timedelta(days=1)).isoformat(),
            },
            headers=self.headers(),
        )
        self.assertEqual(invalid_creation.status_code, 422)
        invalid_update = self.client.patch(
            f"/qualifications/{qualification.json()['id']}",
            json={"expires_on": (date.today() - timedelta(days=500)).isoformat()},
            headers=self.headers(),
        )
        self.assertEqual(invalid_update.status_code, 422)

        configured = self.client.put(
            "/settings/certificate-warning-days?days=5",
            headers=self.headers(),
        )
        self.assertEqual(configured.status_code, 200, configured.text)
        self.assertEqual(configured.json(), {"days": 5})
        review_after_config = self.client.get(
            f"/profile-reviews?teacher_id={teacher_id}"
        )
        self.assertEqual(
            review_after_config.json()["items"][0]["expiring_certificates"],
            [],
        )
        stored_qualification = self.client.get(
            f"/teachers/{teacher_id}/qualifications"
        ).json()[0]
        self.assertEqual(stored_qualification["expires_on"], expiry.isoformat())

        manager = self.login("manager")
        manager_headers = {"X-CSRF-Token": manager["csrf_token"]}
        self.assertEqual(
            self.client.get("/profile-reviews", headers=manager_headers).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                "/settings/certificate-warning-days",
                headers=manager_headers,
            ).status_code,
            403,
        )

    def test_profile_review_classical_model_requires_sufficient_data(self) -> None:
        teacher_ids = [
            self.create_teacher(f"T{index:03d}").json()["id"]
            for index in range(20)
        ]
        for index in range(12):
            response = self.client.post(
                f"/teachers/{teacher_ids[-1]}/qualifications",
                json={
                    "qualification_type": "degree",
                    "title": f"Văn bằng bổ sung {index}",
                },
                headers=self.headers(),
            )
            self.assertEqual(response.status_code, 201, response.text)

        review = self.client.get("/profile-reviews")
        self.assertEqual(review.status_code, 200, review.text)
        result = review.json()
        self.assertEqual(result["model"]["status"], "ready")
        self.assertEqual(result["model"]["profile_count"], 20)
        anomaly_items = [item for item in result["items"] if item["anomaly"]]
        self.assertTrue(anomaly_items)
        self.assertTrue(anomaly_items[0]["anomaly"]["reasons"])

    def test_reports_export_and_audit_access(self) -> None:
        self.create_teacher()
        with patch(
            "app.main._missing_requirements",
            side_effect=AssertionError("Report completeness must be set-based."),
        ):
            summary = self.client.get("/reports/summary")
            self.assertEqual(summary.status_code, 200, summary.text)
            self.assertEqual(summary.json()["total_teachers"], 1)
            exported = self.client.get("/reports/export.xlsx")
        self.assertEqual(exported.status_code, 200)
        workbook = load_workbook(BytesIO(exported.content), read_only=True)
        self.assertIn("Giang vien", workbook.sheetnames)
        workbook.close()

        manager = self.login("manager")
        manager_export = self.client.get(
            "/reports/export.xlsx",
            headers={"X-CSRF-Token": manager["csrf_token"]},
        )
        self.assertEqual(manager_export.status_code, 200)
        manager_workbook = load_workbook(BytesIO(manager_export.content), read_only=True)
        manager_values = [
            cell.value
            for sheet in manager_workbook.worksheets
            for row in sheet.iter_rows()
            for cell in row
        ]
        self.assertNotIn("T001", manager_values)
        self.assertNotIn("Nguyen Van An", manager_values)
        manager_workbook.close()
        self.assertEqual(self.client.get("/audit-logs").status_code, 403)

        admin = self.login("admin")
        self.assertEqual(
            self.client.get(
                "/audit-logs",
                headers={"X-CSRF-Token": admin["csrf_token"]},
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.delete(
                "/audit-logs/1",
                headers={"X-CSRF-Token": admin["csrf_token"]},
            ).status_code,
            404,
        )

    def test_audit_logs_return_filtered_total_for_pagination(self) -> None:
        admin = self.login("admin")
        with self.client.app.state.session_factory() as db:
            admin_user = db.scalar(select(User).where(User.username == "admin"))
            self.assertIsNotNone(admin_user)
            db.add_all(
                [
                    AuditLog(
                        actor_id=admin_user.id,
                        action="audit_pagination_test",
                        entity_type="test",
                        entity_id=str(index),
                        outcome="success",
                    )
                    for index in range(205)
                ]
            )
            db.commit()

        headers = {"X-CSRF-Token": str(admin["csrf_token"])}
        first_page = self.client.get(
            "/audit-logs",
            params={"action": "audit_pagination_test", "limit": 20, "offset": 0},
            headers=headers,
        )
        self.assertEqual(first_page.status_code, 200, first_page.text)
        self.assertEqual(first_page.headers["x-total-count"], "205")
        self.assertEqual(len(first_page.json()), 20)

        last_page = self.client.get(
            "/audit-logs",
            params={"action": "audit_pagination_test", "limit": 20, "offset": 200},
            headers=headers,
        )
        self.assertEqual(last_page.status_code, 200, last_page.text)
        self.assertEqual(last_page.headers["x-total-count"], "205")
        self.assertEqual(len(last_page.json()), 5)

    def test_password_change_invalidates_session(self) -> None:
        response = self.client.post(
            "/auth/password",
            json={
                "current_password": "Correct horse battery staple 2048!",
                "new_password": "A different secure password 2049!",
            },
            headers=self.headers(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.get("/teachers").status_code, 401)
        new_login = self.login("hr", "A different secure password 2049!")
        self.assertTrue(new_login["csrf_token"])


if __name__ == "__main__":
    unittest.main()
