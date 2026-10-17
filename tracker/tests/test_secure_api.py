import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from tracker.models import Habit


class HabitApiTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.owner = users.objects.create_user(username="owner", password="strong-test-password")
        self.other = users.objects.create_user(username="other", password="strong-test-password")
        self.client = Client(enforce_csrf_checks=True)
        self.client.login(username="owner", password="strong-test-password")
        self.csrf = self.client.get(reverse("home")).cookies["csrftoken"].value

    def post_json(self, url, payload):
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )

    def test_login_is_required(self):
        self.client.logout()
        response = self.client.get(reverse("habits"))
        self.assertEqual(response.status_code, 302)

    def test_health_check_is_public(self):
        self.client.logout()
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_create_and_list_habit(self):
        response = self.post_json(reverse("habits"), {"name": "Read", "target_per_week": 5})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Habit.objects.get().owner, self.owner)
        listed = self.client.get(reverse("habits")).json()["habits"]
        self.assertEqual([row["name"] for row in listed], ["Read"])

    def test_cannot_read_another_users_habits(self):
        Habit.objects.create(owner=self.other, name="Private habit")
        self.assertEqual(self.client.get(reverse("habits")).json()["habits"], [])

    def test_csrf_is_enforced(self):
        response = self.client.post(
            reverse("habits"),
            data=json.dumps({"name": "Read"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_validates_target(self):
        response = self.post_json(reverse("habits"), {"name": "Read", "target_per_week": 9})
        self.assertEqual(response.status_code, 422)
