import re
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.main import create_app
from app.models import User
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
            json={"full_name": "Updated User", "role": "manager"},
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
            json={"role": "manager"},
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
