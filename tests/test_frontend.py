from __future__ import annotations

import importlib.util
import json
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
import uvicorn

from app.main import create_app
from app.models import (
    ChecklistItem,
    Department,
    ManagerDepartmentAssignment,
    Notification,
    Teacher,
    User,
)
from app.security import hash_password

PLAYWRIGHT_AVAILABLE = importlib.util.find_spec("playwright") is not None

if PLAYWRIGHT_AVAILABLE:
    from playwright.sync_api import Browser, Page, Playwright, expect, sync_playwright


@unittest.skipUnless(
    PLAYWRIGHT_AVAILABLE,
    "Install requirements-test.txt and run `python -m playwright install chromium`.",
)
class FrontendBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(cls.temporary_directory.name)
        database_url = f"sqlite:///{(root / 'browser-tests.db').as_posix()}"
        cls.app = create_app(database_url, secure_cookies=False)
        cls.app.state.upload_dir = root / "uploads"

        cls.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cls.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        cls.server_socket.bind(("127.0.0.1", 0))
        cls.server_socket.listen(128)
        cls.base_url = f"http://127.0.0.1:{cls.server_socket.getsockname()[1]}"
        config = uvicorn.Config(
            cls.app,
            log_level="error",
            access_log=False,
            lifespan="on",
        )
        cls.server = uvicorn.Server(config)
        cls.server_thread = threading.Thread(
            target=cls.server.run,
            kwargs={"sockets": [cls.server_socket]},
            daemon=True,
        )
        cls.server_thread.start()

        deadline = time.monotonic() + 20
        while not cls.server.started and time.monotonic() < deadline:
            if not cls.server_thread.is_alive():
                raise RuntimeError("The test server stopped before startup completed.")
            time.sleep(0.05)
        if not cls.server.started:
            cls.server.should_exit = True
            cls.server_thread.join(timeout=5)
            raise RuntimeError("The test server did not start in time.")

        with cls.app.state.session_factory() as db:
            password = "Browser test password 2048!"
            hr_user = User(
                username="browser-hr",
                full_name="Browser HR",
                password_hash=hash_password(password),
                role="hr",
            )
            manager_user = User(
                username="browser-manager",
                full_name="Browser Manager",
                password_hash=hash_password(password),
                role="manager",
            )
            admin_user = User(
                username="browser-admin",
                full_name="Browser Admin",
                password_hash=hash_password(password),
                role="admin",
            )
            db.add_all([hr_user, manager_user, admin_user])
            db.flush()
            db.add(
                Notification(
                    user_id=hr_user.id,
                    event_key="browser-notification",
                    title="Thông báo kiểm thử giao diện",
                    message="Thông báo phải được tải từ máy chủ.",
                    level="info",
                    target_view="overview",
                )
            )
            department = Department(code="UI-TEST", name="Browser test unit")
            db.add(department)
            db.flush()
            db.add(
                Department(
                    code="UI-TEST-CHILD",
                    name="Browser test subunit",
                    parent_id=department.id,
                )
            )
            checklist_item = ChecklistItem(
                code="browser-test-item",
                label="Browser test checklist item",
                category="qualification",
                classification="conditional",
                applicability="Initial condition",
            )
            db.add(checklist_item)
            db.flush()
            db.add(
                ManagerDepartmentAssignment(
                    manager_id=manager_user.id,
                    department_id=department.id,
                )
            )
            db.add_all(
                Teacher(
                    employee_code=f"UI-{index:03d}",
                    full_name=f"UI Lecturer {index:03d}",
                    department_id=department.id,
                    academic_degree="Master",
                )
                for index in range(1, 28)
            )
            db.commit()
            cls.department_id = department.id
            cls.checklist_item_id = checklist_item.id
        cls.password = password

        cls.playwright: Playwright = sync_playwright().start()
        cls.browser: Browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "browser"):
            cls.browser.close()
        if hasattr(cls, "playwright"):
            cls.playwright.stop()
        if hasattr(cls, "server"):
            cls.server.should_exit = True
            cls.server_thread.join(timeout=10)
        if hasattr(cls, "server_socket"):
            cls.server_socket.close()
        if hasattr(cls, "temporary_directory"):
            cls.temporary_directory.cleanup()

    def setUp(self) -> None:
        self.page: Page = self.browser.new_page()
        self.page.goto(self.base_url)
        self.page.locator('#login-form [name="username"]').fill("browser-hr")
        self.page.locator('#login-form [name="password"]').fill(self.password)
        self.page.locator("#login-form button[type=submit]").click()
        expect(self.page.locator("#profile-role")).to_have_text("Nhân viên nhân sự")

    def tearDown(self) -> None:
        self.page.close()

    def test_teacher_list_paginates_and_filters_in_browser(self) -> None:
        self.page.locator('.nav-link[data-view="teachers"]').click()
        pager = self.page.locator("#workspace-pager")
        expect(pager).to_contain_text("Trang 1/2 · 27 bản ghi")
        self.page.locator('[data-action="page-next"]').click()
        expect(pager).to_contain_text("Trang 2/2 · 27 bản ghi")
        expect(self.page.locator("#workspace-rows")).to_contain_text("UI-027")
        self.page.locator(".workspace-search").fill("UI-003")
        expect(self.page.locator("#workspace-rows")).to_contain_text("UI-003")
        expect(pager).to_have_class("pager hidden")
        self.page.locator('[data-action="edit-teacher"]').click()
        expect(
            self.page.locator('#teacher-form [name="full_name"]')
        ).to_have_value("UI Lecturer 003")

    def test_report_explains_date_filter_scope(self) -> None:
        manager_page = self.browser.new_page()
        try:
            manager_page.goto(self.base_url)
            manager_page.locator('#login-form [name="username"]').fill(
                "browser-manager"
            )
            manager_page.locator('#login-form [name="password"]').fill(self.password)
            manager_page.locator("#login-form button[type=submit]").click()
            expect(manager_page.locator("#profile-role")).to_have_text("Người quản lý")
            manager_page.locator('.nav-link[data-view="reports"]').click()
            expect(manager_page.locator("#workspace-filters")).to_contain_text(
                "Ngày tạo hồ sơ từ"
            )
            expect(manager_page.locator("#workspace-filters")).to_contain_text(
                "trong nhóm hồ sơ đã lọc"
            )
        finally:
            manager_page.close()

    def test_notification_bell_shows_persistent_items_and_marks_them_read(
        self,
    ) -> None:
        badge = self.page.locator("#notif-count")
        expect(badge).to_be_visible()
        self.page.locator("#notif-button").click()
        notification = self.page.locator(
            '[data-action="notif-open"][data-notif]'
        )
        expect(notification).to_contain_text("Thông báo kiểm thử giao diện")
        self.page.locator("#notif-read").click()
        expect(badge).to_have_class("notif-badge hidden")

    def test_manager_account_form_selects_one_root_faculty(self) -> None:
        admin_page = self.browser.new_page()
        try:
            admin_page.goto(self.base_url)
            admin_page.locator('#login-form [name="username"]').fill(
                "browser-admin"
            )
            admin_page.locator('#login-form [name="password"]').fill(self.password)
            admin_page.locator("#login-form button[type=submit]").click()
            expect(admin_page.locator("#profile-role")).to_have_text(
                "Quản trị viên"
            )
            admin_page.locator('.nav-link[data-view="accounts"]').click()
            role = admin_page.locator(
                '.admin-account-form select[name="role"]'
            )
            role.select_option("manager")
            department = admin_page.locator(
                '.admin-account-form select[name="managed_department_id"]'
            )
            expect(department).to_be_visible()
            expect(department).to_have_attribute("required", "")
            self.assertIsNone(department.get_attribute("multiple"))
            self.assertEqual(department.locator("option").count(), 2)
            self.assertEqual(
                department.locator("option").nth(1).text_content(),
                "Browser test unit",
            )
            manager_id = next(
                user["id"]
                for user in admin_page.request.get(
                    f"{self.base_url}/users"
                ).json()
                if user["username"] == "browser-manager"
            )
            admin_page.locator(
                f'#workspace-rows [data-action="edit-account"][data-id="{manager_id}"]'
            ).click()
            edit_department = admin_page.locator(
                '#account-form select[name="managed_department_id"]'
            )
            expect(edit_department).to_be_visible()
            expect(edit_department).to_have_value(str(self.department_id))
            self.assertIsNone(edit_department.get_attribute("multiple"))
        finally:
            admin_page.close()

    def test_checklist_edit_uses_an_in_app_form(self) -> None:
        self.page.locator('.nav-link[data-view="teachers"]').click()
        self.page.locator('[data-action="teacher-open"]').first.click()
        self.page.locator('[data-action="teacher-checklist"]').click()
        edit_button = self.page.locator(
            f'[data-action="edit-checklist-item"][data-id="{self.checklist_item_id}"]'
        )
        edit_button.click()
        dialog = self.page.get_by_role("dialog", name="Sửa mục checklist")
        dialog.locator('[name="classification"]').select_option("optional")
        dialog.locator('[name="applicability"]').fill("Updated in browser")
        dialog.get_by_role("button", name="Lưu thay đổi").click()
        expect(self.page.locator("#toast-region")).to_contain_text(
            "Đã cập nhật checklist"
        )
        expect(dialog).to_have_count(0)

    def test_data_loading_errors_are_visible_and_prompts_are_absent(self) -> None:
        self.page.route(
            "**/departments?include_inactive=true",
            lambda route: route.fulfill(
                status=503,
                content_type="application/json",
                body=json.dumps({"detail": "Simulated department failure"}),
            ),
        )
        self.page.locator('[data-view="departments"]').click()
        expect(self.page.locator("#toast-region")).to_contain_text(
            "Simulated department failure"
        )
        script = self.page.request.get(f"{self.base_url}/static/app.js").text()
        self.assertNotIn("window.prompt(", script)


if __name__ == "__main__":
    unittest.main()
