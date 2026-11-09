from __future__ import annotations

import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import create_app
from app.models import Department, User
from app.security import hash_password
from scripts.seed_demo import Api, MANAGER_DEMO_FACULTIES, ensure_manager_accounts


class DemoManagerSeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.iterations_patch = patch("app.security.PASSWORD_ITERATIONS", 1_000)
        self.iterations_patch.start()
        self.client_context = TestClient(create_app("sqlite://"))
        self.client = self.client_context.__enter__()
        self.password = "Correct horse battery staple 2048!"
        with self.client.app.state.session_factory() as db:
            admin = User(
                username="demo-seed-admin",
                full_name="Demo Seed Admin",
                password_hash=hash_password(self.password),
                role="admin",
            )
            faculties = [
                Department(code=code, name=name)
                for code, name, _ in MANAGER_DEMO_FACULTIES
            ]
            db.add_all([admin, *faculties])
            db.flush()
            legacy_manager = User(
                username="manager_demo1",
                full_name="Legacy Demo Manager",
                password_hash=hash_password(self.password),
                role="manager",
                managed_departments=faculties[:2],
            )
            db.add(legacy_manager)
            self.faculties = {
                code: {"id": faculty.id}
                for (_, _, code), faculty in zip(
                    MANAGER_DEMO_FACULTIES, faculties
                )
            }
            db.commit()
        self.api = Api(self.client)
        self.api.login("demo-seed-admin", self.password)

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.iterations_patch.stop()

    def test_seed_reassigns_legacy_managers_and_is_idempotent(self) -> None:
        passwords: dict[str, str] = {}
        for _ in range(2):
            with redirect_stdout(StringIO()):
                ensure_manager_accounts(self.api, self.faculties, passwords)
            users = {
                user["username"]: user
                for user in self.api.request("GET", "/users").json()
            }
            self.assertEqual(len(passwords), 3)
            for username, _, faculty_code in MANAGER_DEMO_FACULTIES:
                self.assertEqual(users[username]["role"], "manager")
                self.assertEqual(
                    users[username]["managed_department_id"],
                    self.faculties[faculty_code]["id"],
                )
        self.assertEqual(
            self.api.request("GET", "/users").status_code,
            200,
        )


if __name__ == "__main__":
    unittest.main()
