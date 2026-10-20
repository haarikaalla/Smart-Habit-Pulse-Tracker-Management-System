import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from tracker.models import Habit, HabitCheckIn
from tracker.services import current_and_best_streak


class HabitApiTests(TestCase):
    password = "strong-test-password"

    def setUp(self):
        users = get_user_model()
        self.owner = users.objects.create_user(username="owner", password=self.password)
        self.other = users.objects.create_user(username="other", password=self.password)
        self.client = Client(enforce_csrf_checks=True)
        self.client.login(username="owner", password=self.password)
        self.csrf = self.client.get(reverse("home")).cookies["csrftoken"].value

    def json_request(self, method, url, payload=None, *, csrf=True):
        kwargs = {
            "data": json.dumps(payload or {}),
            "content_type": "application/json",
        }
        if csrf:
            kwargs["HTTP_X_CSRFTOKEN"] = self.csrf
        return getattr(self.client, method.lower())(url, **kwargs)

    def create_habit(self, **overrides):
        data = {
            "name": "Read deeply",
            "description": "Thirty focused minutes",
            "category": "learning",
            "target_per_week": 5,
            "color": "#7657E8",
        }
        data.update(overrides)
        return self.json_request("post", reverse("habits"), data)

    def test_dashboard_and_apis_require_login(self):
        self.client.logout()
        for url in (reverse("home"), reverse("habits"), reverse("analytics"), reverse("export_data")):
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_health_checks_are_public_and_ready(self):
        self.client.logout()
        live = self.client.get(reverse("health"))
        ready = self.client.get(reverse("readiness"))
        self.assertEqual(live.json()["status"], "ok")
        self.assertEqual(ready.json(), {"status": "ready", "database": "connected"})
        self.assertIn("X-Request-ID", live.headers)

    def test_create_returns_rich_habit_contract(self):
        response = self.create_habit(reminder_time="08:30")
        self.assertEqual(response.status_code, 201)
        payload = response.json()["habit"]
        self.assertEqual(payload["category_label"], "Learning")
        self.assertEqual(payload["week_progress"], 0)
        self.assertEqual(payload["version"], 1)
        self.assertEqual(Habit.objects.get().owner, self.owner)

    def test_create_rejects_invalid_json_and_fields(self):
        invalid_json = self.client.post(
            reverse("habits"),
            data="not-json",
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )
        invalid_target = self.create_habit(name="Invalid", target_per_week=8)
        invalid_color = self.create_habit(name="Color", color="purple")
        self.assertEqual(invalid_json.status_code, 400)
        self.assertEqual(invalid_json.json()["error"]["code"], "invalid_json")
        self.assertEqual(invalid_target.status_code, 422)
        self.assertEqual(invalid_color.status_code, 422)

    def test_duplicate_active_name_is_rejected_case_insensitively(self):
        self.assertEqual(self.create_habit().status_code, 201)
        duplicate = self.create_habit(name="READ DEEPLY")
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.json()["error"]["code"], "duplicate_habit")

    def test_list_search_and_category_filters_are_user_scoped(self):
        Habit.objects.create(owner=self.owner, name="Read", category="learning")
        Habit.objects.create(owner=self.owner, name="Run", category="health")
        Habit.objects.create(owner=self.other, name="Private read", category="learning")
        response = self.client.get(reverse("habits"), {"q": "read", "category": "learning"})
        self.assertEqual([item["name"] for item in response.json()["habits"]], ["Read"])

    def test_csrf_is_enforced_for_mutations(self):
        response = self.json_request("post", reverse("habits"), {"name": "Read"}, csrf=False)
        self.assertEqual(response.status_code, 403)

    def test_update_uses_optimistic_concurrency(self):
        habit = Habit.objects.create(owner=self.owner, name="Read")
        url = reverse("habit_detail", args=[habit.id])
        updated = self.json_request("patch", url, {"name": "Read daily", "expected_version": 1})
        stale = self.json_request("patch", url, {"name": "Overwrite", "expected_version": 1})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["habit"]["version"], 2)
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["error"]["code"], "version_conflict")

    def test_cannot_update_or_check_in_another_users_habit(self):
        habit = Habit.objects.create(owner=self.other, name="Private")
        update = self.json_request(
            "patch", reverse("habit_detail", args=[habit.id]), {"name": "Stolen", "expected_version": 1}
        )
        check_in = self.json_request("put", reverse("habit_check_in", args=[habit.id]), {"completed": True})
        self.assertEqual(update.status_code, 404)
        self.assertEqual(check_in.status_code, 404)

    def test_check_in_is_idempotent_and_can_be_reversed(self):
        habit = Habit.objects.create(owner=self.owner, name="Read")
        url = reverse("habit_check_in", args=[habit.id])
        first = self.json_request("put", url, {"completed": True, "effort": 4, "note": "Focused"})
        second = self.json_request("put", url, {"completed": True, "effort": 5})
        removed = self.json_request("put", url, {"completed": False})
        self.assertTrue(first.json()["changed"])
        self.assertFalse(second.json()["changed"])
        self.assertEqual(HabitCheckIn.objects.count(), 0)
        self.assertTrue(removed.json()["changed"])

    def test_future_check_in_is_rejected(self):
        habit = Habit.objects.create(owner=self.owner, name="Read")
        future = timezone.localdate() + timedelta(days=1)
        response = self.json_request(
            "put", reverse("habit_check_in", args=[habit.id]), {"date": future.isoformat()}
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "future_date")

    def test_archive_is_soft_and_history_is_preserved(self):
        habit = Habit.objects.create(owner=self.owner, name="Read")
        HabitCheckIn.objects.create(habit=habit, completed_on=timezone.localdate())
        response = self.json_request("delete", reverse("habit_detail", args=[habit.id]))
        habit.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(habit.is_archived)
        self.assertEqual(habit.check_ins.count(), 1)
        self.assertEqual(self.client.get(reverse("habits")).json()["habits"], [])

    def test_analytics_reports_streaks_goals_and_timeline(self):
        today = timezone.localdate()
        habit = Habit.objects.create(owner=self.owner, name="Read", target_per_week=4)
        for offset in range(3):
            HabitCheckIn.objects.create(habit=habit, completed_on=today - timedelta(days=offset))
        response = self.client.get(reverse("analytics"), {"days": 28})
        summary = response.json()["summary"]
        row = response.json()["habits"][0]
        self.assertEqual(summary["active_habits"], 1)
        self.assertEqual(summary["period_check_ins"], 3)
        self.assertEqual(row["current_streak"], 3)
        self.assertEqual(len(response.json()["timeline"]), 28)

    def test_export_contains_only_requesting_users_data(self):
        mine = Habit.objects.create(owner=self.owner, name="Mine")
        HabitCheckIn.objects.create(habit=mine, completed_on=timezone.localdate(), note="Kept private")
        Habit.objects.create(owner=self.other, name="Secret")
        response = self.client.get(reverse("export_data"))
        self.assertEqual(
            response.headers["Content-Disposition"],
            'attachment; filename="habitpulse-export.json"',
        )
        self.assertEqual([item["name"] for item in response.json()["habits"]], ["Mine"])
        self.assertEqual(response.json()["habits"][0]["check_ins"][0]["note"], "Kept private")


class StreakCalculationTests(TestCase):
    def test_current_streak_allows_today_to_be_pending(self):
        today = timezone.localdate()
        dates = {today - timedelta(days=1), today - timedelta(days=2), today - timedelta(days=5)}
        self.assertEqual(current_and_best_streak(dates, today=today), (2, 2))

    def test_best_streak_is_independent_of_current_streak(self):
        today = timezone.localdate()
        dates = {today - timedelta(days=value) for value in (0, 3, 4, 5, 6)}
        self.assertEqual(current_and_best_streak(dates, today=today), (1, 4))
