import unittest

from fastapi.testclient import TestClient

from app.main import create_app


class TeacherManagementApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client_context = TestClient(create_app("sqlite://"))
        self.client = self.client_context.__enter__()
        response = self.client.post(
            "/departments",
            json={"code": "IT", "name": "Information Technology"},
        )
        self.assertEqual(response.status_code, 201)
        self.department_id = response.json()["id"]

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)

    def test_frontend_and_static_assets_are_served(self) -> None:
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("TeacherHub", page.text)
        self.assertIn('id="teacher-form"', page.text)

        script = self.client.get("/static/app.js")
        stylesheet = self.client.get("/static/styles.css")
        favicon = self.client.get("/static/favicon.svg")
        self.assertEqual(script.status_code, 200)
        self.assertIn("refreshData", script.text)
        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn(".app-shell", stylesheet.text)
        self.assertEqual(favicon.status_code, 200)

    def create_teacher(self, employee_code: str = "T001", **overrides: object):
        payload: dict[str, object] = {
            "employee_code": employee_code,
            "full_name": "Nguyen Van An",
            "department_id": self.department_id,
            "academic_degree": "Master",
        }
        payload.update(overrides)
        return self.client.post("/teachers", json=payload)

    def test_create_and_filter_teacher(self) -> None:
        created = self.create_teacher()
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["employee_code"], "T001")

        response = self.client.get("/teachers", params={"q": "Nguyen", "academic_degree": "Master"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_duplicate_employee_code_is_rejected(self) -> None:
        self.assertEqual(self.create_teacher().status_code, 201)
        duplicate = self.create_teacher()
        self.assertEqual(duplicate.status_code, 409)

    def test_department_reference_must_exist(self) -> None:
        response = self.create_teacher(department_id=999)
        self.assertEqual(response.status_code, 404)

    def test_teacher_status_can_be_paused(self) -> None:
        created = self.create_teacher()
        response = self.client.patch(
            f"/teachers/{created.json()['id']}",
            json={"employment_status": "paused"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["employment_status"], "paused")

    def test_teacher_cannot_be_physically_deleted_by_api(self) -> None:
        created = self.create_teacher()
        teacher_id = created.json()["id"]
        response = self.client.delete(f"/teachers/{teacher_id}")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.client.get(f"/teachers/{teacher_id}").status_code, 200)

    def test_department_can_be_deactivated_without_deleting_it(self) -> None:
        response = self.client.patch(
            f"/departments/{self.department_id}",
            json={"is_active": False},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["is_active"], False)
        self.assertEqual(self.client.get("/departments").json(), [])
        self.assertEqual(
            len(self.client.get("/departments", params={"include_inactive": True}).json()),
            1,
        )


if __name__ == "__main__":
    unittest.main()
