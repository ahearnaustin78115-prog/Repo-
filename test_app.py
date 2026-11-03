import re
import tempfile
import unittest
from pathlib import Path

from app import create_app


class SubscriberAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret-key",
                "ADMIN_PASSWORD": "test-admin-password",
                "DATABASE": str(Path(self.temp_dir.name) / "subscribers.sqlite3"),
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def csrf_token(self, response):
        match = re.search(
            rb'name="csrf_token" value="([^"]+)"', response.data
        )
        self.assertIsNotNone(match)
        return match.group(1).decode()

    def test_subscribe_and_prevent_duplicate_addresses(self):
        response = self.client.get("/")
        token = self.csrf_token(response)
        response = self.client.post(
            "/subscribe",
            data={"csrf_token": token, "email": " Reader@Example.com "},
            follow_redirects=True,
        )
        self.assertIn(b"You\xe2\x80\x99re subscribed", response.data)

        response = self.client.get("/")
        response = self.client.post(
            "/subscribe",
            data={
                "csrf_token": self.csrf_token(response),
                "email": "reader@example.com",
            },
            follow_redirects=True,
        )
        self.assertIn(b"already subscribed", response.data)

    def test_reject_invalid_email(self):
        response = self.client.get("/")
        response = self.client.post(
            "/subscribe",
            data={"csrf_token": self.csrf_token(response), "email": "not-an-email"},
            follow_redirects=True,
        )
        self.assertIn(b"Enter a valid email address", response.data)

    def test_admin_can_view_and_remove_subscriber(self):
        response = self.client.get("/")
        self.client.post(
            "/subscribe",
            data={
                "csrf_token": self.csrf_token(response),
                "email": "reader@example.com",
            },
        )

        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 302)
        response = self.client.get("/admin/login")
        response = self.client.post(
            "/admin/login",
            data={
                "csrf_token": self.csrf_token(response),
                "password": "test-admin-password",
            },
            follow_redirects=True,
        )
        self.assertIn(b"reader@example.com", response.data)

        response = self.client.post(
            "/admin/subscribers/1/delete",
            data={"csrf_token": self.csrf_token(response)},
            follow_redirects=True,
        )
        self.assertIn(b"No subscribers yet", response.data)

    def test_post_without_csrf_token_is_rejected(self):
        response = self.client.post("/subscribe", data={"email": "reader@example.com"})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
