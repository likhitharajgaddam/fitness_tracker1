from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .gamification import evaluate_user_gamification
from .models import (
    Achievement,
    DailyChallenge,
    FitnessActivity,
    FitnessGoal,
    Sport,
    UserAchievement,
    UserChallengeCompletion,
    UserProfile,
    Workout,
)

User = get_user_model()


class FitTrackPlatformTests(TestCase):
    def setUp(self):
        call_command("seed_data")
        self.user_a = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="StrongPass123!",
            first_name="Alice",
            last_name="Morgan",
        )
        UserProfile.objects.create(
            user=self.user_a,
            age=23,
            fitness_level="Beginner",
            primary_goal="Flexibility",
            preferred_environment="Home",
            companion_choice=UserProfile.COMPANION_FEMALE,
            profile_completed=True,
            tutorial_completed=True,
        )
        self.user_b = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="StrongPass456!",
            first_name="Bob",
            last_name="Chen",
        )
        UserProfile.objects.create(user=self.user_b)

    def test_public_landing_and_library_access(self):
        landing_resp = self.client.get(reverse("fitness:landing"))
        self.assertEqual(landing_resp.status_code, 200)
        self.assertContains(landing_resp, "Every Move Counts.")

        act_resp = self.client.get(reverse("fitness:activities"))
        self.assertEqual(act_resp.status_code, 200)
        self.assertContains(act_resp, "Walking")
        self.assertContains(act_resp, "Jump Rope")
        self.assertContains(act_resp, "Core Plank")

        sport_resp = self.client.get(reverse("fitness:sports"))
        self.assertEqual(sport_resp.status_code, 200)
        self.assertContains(sport_resp, "Badminton")
        self.assertContains(sport_resp, "Table Tennis")
        self.assertContains(sport_resp, "What Should I Play Today?")

        activity = FitnessActivity.objects.first()
        sport = Sport.objects.first()
        self.assertEqual(
            self.client.get(
                reverse("fitness:activity_detail", args=[activity.pk])
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("fitness:sport_detail", args=[sport.pk])
            ).status_code,
            200,
        )

    def test_private_routes_require_authentication(self):
        private_urls = [
            reverse("fitness:dashboard"),
            reverse("fitness:workouts"),
            reverse("fitness:goals"),
            reverse("fitness:rewards"),
            reverse("fitness:analytics"),
            reverse("fitness:profile"),
            reverse("fitness:profile_setup"),
            reverse("fitness:settings"),
        ]
        for url in private_urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, f"Expected redirect on {url}")
            self.assertIn(reverse("fitness:login"), resp.url)

    def test_signup_auto_login_and_duplicate_prevention(self):
        dup_resp = self.client.post(
            reverse("fitness:signup"),
            {
                "full_name": "Another Alice",
                "username": "alice",
                "email": "newalice@example.com",
                "password": "ValidPassword99!",
                "confirm_password": "ValidPassword99!",
            },
        )
        self.assertEqual(dup_resp.status_code, 200)
        self.assertContains(dup_resp, "already taken")

        dup_email_resp = self.client.post(
            reverse("fitness:signup"),
            {
                "full_name": "Another Alice",
                "username": "alice_two",
                "email": "ALICE@example.com",
                "password": "ValidPassword99!",
                "confirm_password": "ValidPassword99!",
            },
        )
        self.assertEqual(dup_email_resp.status_code, 200)
        self.assertContains(dup_email_resp, "already exists")

        ok_resp = self.client.post(
            reverse("fitness:signup"),
            {
                "full_name": "Maya Patel",
                "username": "maya_fit",
                "email": "maya@example.com",
                "password": "ValidPassword99!",
                "confirm_password": "ValidPassword99!",
            },
        )
        self.assertRedirects(ok_resp, reverse("fitness:profile_setup"))
        new_user = User.objects.get(username="maya_fit")
        self.assertTrue(UserProfile.objects.filter(user=new_user).exists())

        setup_resp = self.client.post(
            reverse("fitness:profile_setup"),
            {
                "age": 22,
                "gender": "Female",
                "fitness_level": "Intermediate",
                "primary_goal": "Improve Stamina",
                "preferred_environment": "Outdoor",
                "companion_choice": UserProfile.COMPANION_MALE,
            },
        )
        self.assertRedirects(setup_resp, reverse("fitness:dashboard"))
        new_user.profile.refresh_from_db()
        self.assertTrue(new_user.profile.profile_completed)
        self.assertEqual(new_user.profile.primary_goal, "Improve Stamina")
        self.assertEqual(
            new_user.profile.companion_choice, UserProfile.COMPANION_MALE
        )

    def test_login_with_username_or_email_and_logout(self):
        bad_resp = self.client.post(
            reverse("fitness:login"),
            {"identifier": "alice", "password": "wrongpassword"},
        )
        self.assertEqual(bad_resp.status_code, 200)
        self.assertContains(bad_resp, "Invalid username/email or password")

        email_login = self.client.post(
            reverse("fitness:login"),
            {
                "identifier": "alice@example.com",
                "password": "StrongPass123!",
                "remember_me": "on",
            },
        )
        self.assertRedirects(email_login, reverse("fitness:dashboard"))

        logout_resp = self.client.post(reverse("fitness:logout"))
        self.assertRedirects(logout_resp, reverse("fitness:landing"))

    def test_user_specific_dashboard_and_workout_crud(self):
        today = timezone.localdate()
        self.client.force_login(self.user_a)

        create_resp = self.client.post(
            reverse("fitness:workouts"),
            {
                "activity_name": "Alice Morning Yoga",
                "duration": 40,
                "date": today.isoformat(),
                "notes": "Mobility flow",
            },
            follow=True,
        )
        self.assertEqual(create_resp.status_code, 200)
        self.assertContains(create_resp, "Alice Morning Yoga")

        workout = Workout.objects.get(
            user=self.user_a, activity_name="Alice Morning Yoga"
        )

        dash_resp = self.client.get(reverse("fitness:dashboard"))
        self.assertEqual(dash_resp.status_code, 200)
        self.assertEqual(dash_resp.context["total_workouts"], 1)
        self.assertEqual(dash_resp.context["total_minutes"], 40)
        self.assertEqual(dash_resp.context["today_minutes"], 40)

        edit_resp = self.client.post(
            reverse("fitness:edit_workout", args=[workout.pk]),
            {
                "activity_name": "Alice Evening Yoga",
                "duration": 55,
                "date": today.isoformat(),
                "notes": "Extended stretch",
            },
            follow=True,
        )
        self.assertEqual(edit_resp.status_code, 200)
        workout.refresh_from_db()
        self.assertEqual(workout.duration, 55)
        self.assertEqual(workout.activity_name, "Alice Evening Yoga")

        filter_resp = self.client.get(
            reverse("fitness:workouts"), {"filter_activity": "Alice Evening Yoga"}
        )
        self.assertContains(filter_resp, "Alice Evening Yoga")

        del_resp = self.client.post(
            reverse("fitness:delete_workout", args=[workout.pk]), follow=True
        )
        self.assertEqual(del_resp.status_code, 200)
        self.assertFalse(Workout.objects.filter(pk=workout.pk).exists())

    def test_authorization_prevents_cross_user_access(self):
        today = timezone.localdate()
        alice_workout = Workout.objects.create(
            user=self.user_a,
            activity_name="Private Run",
            duration=30,
            date=today,
        )
        alice_goal = FitnessGoal.objects.create(
            user=self.user_a,
            title="Alice Private Goal",
            goal_type=FitnessGoal.GOAL_DAILY,
            target_minutes=45,
        )

        self.client.force_login(self.user_b)

        bob_dash = self.client.get(reverse("fitness:dashboard"))
        self.assertEqual(bob_dash.context["total_workouts"], 0)
        self.assertEqual(bob_dash.context["active_goals_count"], 0)
        self.assertNotContains(bob_dash, "Private Run")

        self.assertEqual(
            self.client.get(
                reverse("fitness:edit_workout", args=[alice_workout.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse("fitness:delete_workout", args=[alice_workout.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("fitness:edit_goal", args=[alice_goal.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse("fitness:toggle_goal", args=[alice_goal.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse("fitness:delete_goal", args=[alice_goal.pk])
            ).status_code,
            404,
        )

    def test_goals_reward_jars_one_time_celebration_and_analytics(self):
        today = timezone.localdate()
        self.client.force_login(self.user_a)

        goal_resp = self.client.post(
            reverse("fitness:goals"),
            {
                "title": "Popcorn Daily Target",
                "goal_type": FitnessGoal.GOAL_DAILY,
                "target_minutes": 30,
                "reward_container": FitnessGoal.CONTAINER_POPCORN,
                "theme_color": FitnessGoal.THEME_PEACH,
                "start_date": today.isoformat(),
                "end_date": "",
            },
            follow=True,
        )
        self.assertEqual(goal_resp.status_code, 200)
        goal = FitnessGoal.objects.get(
            user=self.user_a, title="Popcorn Daily Target"
        )
        self.assertEqual(goal.reward_container, FitnessGoal.CONTAINER_POPCORN)
        self.assertIsNone(goal.celebrated_at)

        # Log workout that completes the goal
        workout = Workout.objects.create(
            user=self.user_a,
            activity_name="Running",
            duration=35,
            date=today,
        )
        first_eval = evaluate_user_gamification(
            self.user_a, just_logged_workout=workout, reference_date=today
        )
        self.assertTrue(first_eval["has_celebration"])
        self.assertEqual(len(first_eval["newly_completed_goals"]), 1)

        goal.refresh_from_db()
        self.assertIsNotNone(goal.celebrated_at)

        # Re-evaluating on refresh must NOT re-trigger celebration for the same goal
        second_eval = evaluate_user_gamification(
            self.user_a, reference_date=today
        )
        self.assertEqual(len(second_eval["newly_completed_goals"]), 0)

        analytics_resp = self.client.get(
            reverse("fitness:analytics"), {"period": "30d"}
        )
        self.assertEqual(analytics_resp.status_code, 200)
        self.assertEqual(analytics_resp.context["total_workouts"], 1)
        self.assertEqual(
            analytics_resp.context["most_frequent_activity"], "Running"
        )
        self.assertContains(analytics_resp, "Popcorn Daily Target")

    def test_achievements_unlock_idempotently_and_rewards_page(self):
        today = timezone.localdate()
        self.client.force_login(self.user_a)

        Workout.objects.create(
            user=self.user_a, activity_name="Badminton", duration=40, date=today
        )
        Workout.objects.create(
            user=self.user_a,
            activity_name="Swimming",
            duration=25,
            date=today - timedelta(days=1),
        )
        Workout.objects.create(
            user=self.user_a,
            activity_name="Tennis",
            duration=25,
            date=today - timedelta(days=2),
        )
        Workout.objects.create(
            user=self.user_a,
            activity_name="Football",
            duration=30,
            date=today - timedelta(days=3),
        )
        Workout.objects.create(
            user=self.user_a,
            activity_name="Basketball",
            duration=30,
            date=today - timedelta(days=4),
        )

        evaluate_user_gamification(self.user_a, reference_date=today)
        # Re-run to ensure zero duplicate UserAchievement rows
        evaluate_user_gamification(self.user_a, reference_date=today)

        unlocked_slugs = set(
            UserAchievement.objects.filter(user=self.user_a).values_list(
                "achievement__slug", flat=True
            )
        )
        self.assertIn("first-workout", unlocked_slugs)
        self.assertIn("consistency-star", unlocked_slugs)
        self.assertIn("fitness-explorer", unlocked_slugs)
        self.assertIn("sports-enthusiast", unlocked_slugs)
        self.assertEqual(
            UserAchievement.objects.filter(user=self.user_a).count(),
            len(unlocked_slugs),
        )

        rewards_resp = self.client.get(reverse("fitness:rewards"))
        self.assertEqual(rewards_resp.status_code, 200)
        self.assertContains(rewards_resp, "Consistency Star")
        self.assertEqual(Achievement.objects.count(), 8)

    def test_daily_challenge_activity_timer_and_onboarding_tour(self):
        self.client.force_login(self.user_a)
        self.assertGreaterEqual(DailyChallenge.objects.count(), 1)

        # Complete daily challenge
        chal_resp = self.client.post(
            reverse("fitness:complete_challenge"), follow=True
        )
        self.assertEqual(chal_resp.status_code, 200)
        self.assertEqual(
            UserChallengeCompletion.objects.filter(user=self.user_a).count(), 1
        )
        self.assertEqual(
            Workout.objects.filter(
                user=self.user_a, source=Workout.SOURCE_CHALLENGE
            ).count(),
            1,
        )

        # Second click on same day does not duplicate workout
        self.client.post(reverse("fitness:complete_challenge"))
        self.assertEqual(
            UserChallengeCompletion.objects.filter(user=self.user_a).count(), 1
        )

        # Activity timer session save via AJAX
        activity = FitnessActivity.objects.first()
        timer_resp = self.client.post(
            reverse("fitness:log_activity_session", args=[activity.pk]),
            {"duration": 18, "notes": "Timed test"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(timer_resp.status_code, 200)
        self.assertTrue(timer_resp.json()["ok"])
        self.assertTrue(
            Workout.objects.filter(
                user=self.user_a,
                activity_name=activity.name,
                source=Workout.SOURCE_TIMER,
            ).exists()
        )

        # Replay & complete onboarding tour
        replay_resp = self.client.post(reverse("fitness:replay_tutorial"))
        self.assertEqual(replay_resp.status_code, 302)
        self.user_a.profile.refresh_from_db()
        self.assertFalse(self.user_a.profile.tutorial_completed)

        done_resp = self.client.post(
            reverse("fitness:complete_tutorial"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(done_resp.status_code, 200)
        self.user_a.profile.refresh_from_db()
        self.assertTrue(self.user_a.profile.tutorial_completed)

    def test_profile_edit_password_change_and_admin_access(self):
        self.client.force_login(self.user_a)

        admin_resp = self.client.get("/admin/")
        self.assertEqual(admin_resp.status_code, 302)

        prof_resp = self.client.post(
            reverse("fitness:profile"),
            {
                "full_name": "Alice Updated",
                "email": "alice@example.com",
                "age": 24,
                "gender": "Female",
                "fitness_level": "Intermediate",
                "primary_goal": "Muscle Building",
                "preferred_environment": "Gym",
                "companion_choice": UserProfile.COMPANION_MALE,
            },
            follow=True,
        )
        self.assertEqual(prof_resp.status_code, 200)
        self.user_a.refresh_from_db()
        self.assertEqual(self.user_a.first_name, "Alice")
        self.assertEqual(self.user_a.last_name, "Updated")
        self.assertEqual(self.user_a.profile.primary_goal, "Muscle Building")
        self.assertEqual(
            self.user_a.profile.companion_choice, UserProfile.COMPANION_MALE
        )

        pw_resp = self.client.post(
            reverse("fitness:settings"),
            {
                "action": "change_password",
                "old_password": "StrongPass123!",
                "new_password1": "EvenStronger789!",
                "new_password2": "EvenStronger789!",
            },
            follow=True,
        )
        self.assertEqual(pw_resp.status_code, 200)
        self.user_a.refresh_from_db()
        self.assertTrue(self.user_a.check_password("EvenStronger789!"))

        admin_user = User.objects.get(username="admin")
        self.client.force_login(admin_user)
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_auth_case_insensitive_email_inactive_next_redirect_and_persistence(self):
        # Empty fields validation
        empty_resp = self.client.post(
            reverse("fitness:login"), {"identifier": "", "password": ""}
        )
        self.assertEqual(empty_resp.status_code, 200)
        self.assertContains(empty_resp, "Please enter your username or email address.")
        self.assertContains(empty_resp, "Please enter your password.")

        # Case-insensitive username login + next redirect
        next_goals = reverse("fitness:goals")
        login_resp = self.client.post(
            f"{reverse('fitness:login')}?next={next_goals}",
            {"identifier": "  ALICE  ", "password": "StrongPass123!"},
        )
        self.assertRedirects(login_resp, next_goals)

        # Session persists across refresh and all protected routes
        for route in [
            "fitness:dashboard",
            "fitness:goals",
            "fitness:workouts",
            "fitness:rewards",
            "fitness:analytics",
            "fitness:profile",
            "fitness:settings",
            "fitness:dashboard",
        ]:
            resp = self.client.get(reverse(route))
            self.assertEqual(resp.status_code, 200, f"Session failed on {route}")

        # Logout terminates session and blocks protected routes
        logout_resp = self.client.post(reverse("fitness:logout"))
        self.assertRedirects(logout_resp, reverse("fitness:landing"))
        blocked = self.client.get(reverse("fitness:dashboard"))
        self.assertEqual(blocked.status_code, 302)
        self.assertIn(reverse("fitness:login"), blocked.url)

        # Mixed-case email login + external open-redirect protection
        email_resp = self.client.post(
            reverse("fitness:login"),
            {
                "identifier": "ALICE@Example.COM",
                "password": "StrongPass123!",
                "next": "https://evil.example.com/phish",
            },
        )
        self.assertRedirects(email_resp, reverse("fitness:dashboard"))
        self.client.post(reverse("fitness:logout"))

        # Inactive account with right password shows specific inactive message
        inactive = User.objects.create_user(
            username="paused_user",
            email="paused@example.com",
            password="PausedPass123!",
            is_active=False,
        )
        inactive_resp = self.client.post(
            reverse("fitness:login"),
            {"identifier": "paused@example.com", "password": "PausedPass123!"},
        )
        self.assertEqual(inactive_resp.status_code, 200)
        self.assertContains(inactive_resp, "currently inactive")

        # Inactive account with wrong password does NOT leak account status
        inactive_wrong = self.client.post(
            reverse("fitness:login"),
            {"identifier": inactive.username, "password": "WrongPassword999"},
        )
        self.assertEqual(inactive_wrong.status_code, 200)
        self.assertContains(inactive_wrong, "Invalid username/email or password")

    def test_iframe_safe_cookie_policy_https_vs_http(self):
        # Local HTTP request: SameSite=Lax, no Secure/Partitioned
        http_resp = self.client.get(reverse("fitness:login"))
        self.assertEqual(http_resp.status_code, 200)
        csrf_http = http_resp.cookies["csrftoken"].OutputString()
        self.assertIn("SameSite=Lax", csrf_http)
        self.assertNotIn("Secure", csrf_http)
        self.assertNotIn("Partitioned", csrf_http)

        # HTTPS proxied request (AI Studio preview iframe): SameSite=None; Secure; Partitioned
        https_get = self.client.get(
            reverse("fitness:login"),
            HTTP_X_FORWARDED_PROTO="https",
        )
        self.assertEqual(https_get.status_code, 200)
        csrf_https = https_get.cookies["csrftoken"].OutputString()
        self.assertIn("SameSite=None", csrf_https)
        self.assertIn("Secure", csrf_https)
        self.assertIn("Partitioned", csrf_https)

        https_login = self.client.post(
            reverse("fitness:login"),
            {"identifier": "alice", "password": "StrongPass123!"},
            HTTP_X_FORWARDED_PROTO="https",
        )
        self.assertEqual(https_login.status_code, 302)
        session_https = https_login.cookies["sessionid"].OutputString()
        self.assertIn("SameSite=None", session_https)
        self.assertIn("Secure", session_https)
        self.assertIn("Partitioned", session_https)
        self.assertIn("HttpOnly", session_https)

    def test_single_fittrack_logo_in_navigation_across_pages(self):
        # Public pages: strictly 1 logo inside <header>
        for route in ["fitness:landing", "fitness:login", "fitness:signup", "fitness:activities", "fitness:sports"]:
            resp = self.client.get(reverse(route))
            self.assertEqual(resp.status_code, 200)
            html = resp.content.decode("utf-8")
            header_html = html.split("<header", 1)[1].split("</header>", 1)[0]
            self.assertEqual(
                header_html.count('class="app-brand"'),
                1,
                f"Expected strictly 1 FitTrack logo in header on {route}",
            )

        # Authenticated pages: strictly 1 logo in desktop sidebar and 1 in mobile offcanvas (never duplicated!)
        self.client.force_login(self.user_a)
        for route in [
            "fitness:dashboard",
            "fitness:goals",
            "fitness:workouts",
            "fitness:rewards",
            "fitness:analytics",
            "fitness:profile",
            "fitness:settings",
        ]:
            resp = self.client.get(reverse(route))
            self.assertEqual(resp.status_code, 200)
            html = resp.content.decode("utf-8")
            desktop_sidebar = html.split('class="app-sidebar', 1)[1].split("</aside>", 1)[0]
            mobile_sidebar = html.split('id="mobileSidebar"', 1)[1].split('class="app-main-column"', 1)[0]
            self.assertEqual(
                desktop_sidebar.count('class="app-brand"'),
                1,
                f"Expected strictly 1 logo in desktop sidebar on {route}",
            )
            self.assertEqual(
                mobile_sidebar.count('class="app-brand"'),
                1,
                f"Expected strictly 1 logo in mobile offcanvas on {route} (no duplicate!)",
            )
            self.assertNotIn(
                "sidebar-brand-area",
                mobile_sidebar,
                f"Mobile offcanvas must not duplicate sidebar-brand-area on {route}",
            )

    def test_nginx_cloud_run_proxy_headers_with_csrf_enforced(self):
        """
        Simulate exact Cloud Run + container nginx proxy headers where nginx
        forwards Host=localhost:3000, X-Forwarded-Proto=http, and
        X-Forwarded-Host=<external>.run.app, with real CSRF enforcement enabled.
        """
        import re
        from django.test import Client

        csrf_client = Client(enforce_csrf_checks=True)
        external_host = "ais-dev-example.asia-east1.run.app"
        nginx_headers = {
            "HTTP_HOST": "localhost:3000",
            "HTTP_X_FORWARDED_HOST": external_host,
            "HTTP_X_FORWARDED_PROTO": "http",
            "HTTP_ORIGIN": f"https://{external_host}",
            "HTTP_REFERER": f"https://{external_host}/login/",
        }

        get_resp = csrf_client.get(reverse("fitness:login"), **nginx_headers)
        self.assertEqual(get_resp.status_code, 200)
        csrf_hdr = get_resp.cookies["csrftoken"].OutputString()
        self.assertIn("SameSite=None", csrf_hdr)
        self.assertIn("Secure", csrf_hdr)
        self.assertIn("Partitioned", csrf_hdr)

        token_match = re.search(
            r'name="csrfmiddlewaretoken"\s+value="([^"]+)"',
            get_resp.content.decode("utf-8"),
        )
        self.assertIsNotNone(token_match)
        csrf_token = token_match.group(1)

        post_resp = csrf_client.post(
            reverse("fitness:login"),
            {
                "csrfmiddlewaretoken": csrf_token,
                "identifier": "alice@example.com",
                "password": "StrongPass123!",
            },
            **nginx_headers,
        )
        self.assertEqual(post_resp.status_code, 302)
        self.assertEqual(post_resp["Location"], reverse("fitness:dashboard"))
        sess_hdr = post_resp.cookies["sessionid"].OutputString()
        self.assertIn("SameSite=None", sess_hdr)
        self.assertIn("Secure", sess_hdr)
        self.assertIn("Partitioned", sess_hdr)
        self.assertIn("HttpOnly", sess_hdr)

        dash_resp = csrf_client.get(reverse("fitness:dashboard"), **nginx_headers)
        self.assertEqual(dash_resp.status_code, 200)
        self.assertContains(dash_resp, "Alice")

        logout_token = re.search(
            r'name="csrfmiddlewaretoken"\s+value="([^"]+)"',
            dash_resp.content.decode("utf-8"),
        ).group(1)
        logout_resp = csrf_client.post(
            reverse("fitness:logout"),
            {"csrfmiddlewaretoken": logout_token},
            **{**nginx_headers, "HTTP_REFERER": f"https://{external_host}/dashboard/"},
        )
        self.assertEqual(logout_resp.status_code, 302)
        del_sess_hdr = logout_resp.cookies["sessionid"].OutputString()
        self.assertIn("SameSite=None", del_sess_hdr)
        self.assertIn("Secure", del_sess_hdr)
        self.assertIn("Partitioned", del_sess_hdr)

    def test_reward_jar_persistence_across_logout_relogin_refresh_and_user_isolation(self):
        today = timezone.localdate()

        # 1. Sign in as User A (alice)
        login_resp = self.client.post(
            reverse("fitness:login"),
            {"identifier": "alice", "password": "StrongPass123!"},
        )
        self.assertRedirects(login_resp, reverse("fitness:dashboard"))

        # 2. Create a Daily Yoga goal with target 45 minutes and Water Bottle container
        create_goal = self.client.post(
            reverse("fitness:goals"),
            {
                "title": "Daily Yoga Flow",
                "goal_type": FitnessGoal.GOAL_DAILY,
                "target_minutes": 45,
                "reward_container": FitnessGoal.CONTAINER_BOTTLE,
                "theme_color": FitnessGoal.THEME_SKY,
                "start_date": today.isoformat(),
                "end_date": "",
            },
            follow=True,
        )
        self.assertEqual(create_goal.status_code, 200)
        yoga_goal = FitnessGoal.objects.get(user=self.user_a, title="Daily Yoga Flow")
        self.assertEqual(yoga_goal.reward_container, FitnessGoal.CONTAINER_BOTTLE)

        # 3. Log 20 minutes of Yoga for today
        log_resp = self.client.post(
            reverse("fitness:workouts"),
            {
                "activity_name": "Yoga",
                "duration": 20,
                "date": today.isoformat(),
                "notes": "Morning sun salutations",
            },
            follow=True,
        )
        self.assertEqual(log_resp.status_code, 200)

        # 4. Verify 20/45 min, 44%, 25 min remaining, Water Bottle SVG fill 44%, and Yoga 20 min breakdown
        def assert_alice_jar_state(label):
            goals_resp = self.client.get(reverse("fitness:goals"))
            self.assertEqual(goals_resp.status_code, 200, label)
            self.assertIn("no-store", goals_resp.headers.get("Cache-Control", "").lower(), label)
            self.assertContains(goals_resp, "20 / 45 min completed")
            self.assertContains(goals_resp, "44%")
            self.assertContains(goals_resp, "25 min")
            self.assertContains(goals_resp, 'data-jar-type="bottle"')
            self.assertContains(goals_resp, 'data-progress="44"')
            self.assertContains(goals_resp, 'aria-label="Water Bottle at 44 percent"')
            # Exact calibrated Water Bottle liquid Y for 44%: 44 + 86 - round(0.44 * 86) = 92
            self.assertContains(goals_resp, 'y="92"')
            self.assertContains(goals_resp, "Yoga")
            self.assertContains(goals_resp, "20 min")

            dash_resp = self.client.get(reverse("fitness:dashboard"))
            self.assertEqual(dash_resp.status_code, 200, label)
            self.assertIn("no-store", dash_resp.headers.get("Cache-Control", "").lower(), label)
            self.assertContains(dash_resp, "Daily Yoga Flow")
            self.assertContains(dash_resp, "20 / 45 min completed")
            self.assertContains(dash_resp, "44%")
            self.assertContains(dash_resp, "25 min")
            self.assertContains(dash_resp, "Yoga")
            self.assertContains(dash_resp, 'data-jar-type="bottle"')
            self.assertContains(dash_resp, 'data-progress="44"')

            api_resp = self.client.get(reverse("fitness:goals_progress_api"))
            self.assertEqual(api_resp.status_code, 200, label)
            self.assertIn("no-store", api_resp.headers.get("Cache-Control", "").lower(), label)
            payload = api_resp.json()
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["today_minutes"], 20)
            self.assertEqual(len(payload["goals"]), 1)
            g0 = payload["goals"][0]
            self.assertEqual(g0["completed_value"], 20)
            self.assertEqual(g0["target_value"], 45)
            self.assertEqual(g0["remaining_value"], 25)
            self.assertEqual(g0["progress_percent"], 44)
            self.assertEqual(g0["reward_container"], FitnessGoal.CONTAINER_BOTTLE)
            self.assertEqual(
                g0["activity_breakdown"],
                [
                    {
                        "activity_name": "Yoga",
                        "total_minutes": 20,
                        "session_count": 1,
                        "percent_of_goal": 44,
                    }
                ],
            )

        assert_alice_jar_state("before logout")

        # 5. Log out — MUST NOT delete workouts, goals, or progress in DB
        logout_resp = self.client.post(reverse("fitness:logout"))
        self.assertRedirects(logout_resp, reverse("fitness:landing"))
        self.assertEqual(Workout.objects.filter(user=self.user_a).count(), 1)
        self.assertEqual(FitnessGoal.objects.filter(user=self.user_a).count(), 1)

        # 6–8. Sign in again as User A and verify exact persisted jar progress
        relogin_resp = self.client.post(
            reverse("fitness:login"),
            {"identifier": "alice@example.com", "password": "StrongPass123!"},
        )
        self.assertRedirects(relogin_resp, reverse("fitness:dashboard"))
        assert_alice_jar_state("after re-login")

        # 9. Refresh page again and verify persistence
        assert_alice_jar_state("after refresh")

        # 10. Sign out and sign in as User B (bob) — complete user isolation
        self.client.post(reverse("fitness:logout"))
        bob_login = self.client.post(
            reverse("fitness:login"),
            {"identifier": "bob", "password": "StrongPass456!"},
        )
        self.assertRedirects(bob_login, reverse("fitness:dashboard"))

        bob_goals = self.client.get(reverse("fitness:goals"))
        self.assertEqual(bob_goals.status_code, 200)
        self.assertNotContains(bob_goals, "Daily Yoga Flow")
        self.assertNotContains(bob_goals, "20 / 45 min")

        bob_dash = self.client.get(reverse("fitness:dashboard"))
        self.assertEqual(bob_dash.status_code, 200)
        self.assertNotContains(bob_dash, "Daily Yoga Flow")
        self.assertEqual(bob_dash.context["active_goals_count"], 0)
        self.assertEqual(bob_dash.context["total_workouts"], 0)

        bob_api = self.client.get(reverse("fitness:goals_progress_api"))
        self.assertEqual(bob_api.status_code, 200)
        self.assertEqual(bob_api.json()["goals"], [])
        self.assertEqual(bob_api.json()["today_minutes"], 0)

    def test_goal_progress_calculations_all_types_periods_and_activity_breakdown(self):
        # Fixed Wednesday reference date so Mon..Sun boundaries are completely explicit
        from datetime import date

        ref_wed = date(2026, 11, 18)  # Wednesday (week: Mon Nov 16 .. Sun Nov 22)
        prev_week_day = date(2026, 11, 10)  # Tuesday of prior week
        mon_this_week = date(2026, 11, 16)
        tue_this_week = date(2026, 11, 17)

        # Historical workout outside current week (must NEVER be counted in active daily/weekly goals)
        Workout.objects.create(
            user=self.user_a, activity_name="Old Run", duration=60, date=prev_week_day
        )
        # Earlier-this-week workouts
        Workout.objects.create(
            user=self.user_a, activity_name="Badminton", duration=40, date=mon_this_week
        )
        Workout.objects.create(
            user=self.user_a, activity_name="Stretching", duration=15, date=tue_this_week
        )
        # Today's workouts (2 Yoga sessions + 1 Walking session)
        Workout.objects.create(
            user=self.user_a, activity_name="Yoga", duration=20, date=ref_wed
        )
        Workout.objects.create(
            user=self.user_a, activity_name="yoga", duration=10, date=ref_wed
        )
        Workout.objects.create(
            user=self.user_a, activity_name="Walking", duration=15, date=ref_wed
        )
        # Another user's workout today (must NEVER leak into User A's goals)
        Workout.objects.create(
            user=self.user_b, activity_name="Swimming", duration=90, date=ref_wed
        )

        # 1. Daily Duration goal
        daily_goal = FitnessGoal.objects.create(
            user=self.user_a,
            title="Daily Movement",
            goal_type=FitnessGoal.GOAL_DAILY,
            target_minutes=60,
            reward_container=FitnessGoal.CONTAINER_BOTTLE,
            start_date=ref_wed,
        )
        daily_data = daily_goal.get_progress_data(reference_date=ref_wed)
        self.assertEqual(daily_data["completed_value"], 45)
        self.assertEqual(daily_data["remaining_value"], 15)
        self.assertEqual(daily_data["progress_percent"], 75)
        self.assertEqual(daily_data["workout_count"], 3)
        self.assertEqual(
            [(a["activity_name"].lower(), a["total_minutes"], a["session_count"]) for a in daily_data["activity_breakdown"]],
            [("yoga", 30, 2), ("walking", 15, 1)],
        )

        # 2. Weekly Duration goal (whole week Mon..Sun, excludes prev_week_day)
        weekly_goal = FitnessGoal.objects.create(
            user=self.user_a,
            title="Weekly Endurance",
            goal_type=FitnessGoal.GOAL_WEEKLY,
            target_minutes=200,
            reward_container=FitnessGoal.CONTAINER_JUICE,
            start_date=mon_this_week,
        )
        weekly_data = weekly_goal.get_progress_data(reference_date=ref_wed)
        # 40 (Mon) + 15 (Tue) + 45 (Wed) = 100 min (Old Run 60 min excluded!)
        self.assertEqual(weekly_data["completed_value"], 100)
        self.assertEqual(weekly_data["remaining_value"], 100)
        self.assertEqual(weekly_data["progress_percent"], 50)
        self.assertEqual(weekly_data["workout_count"], 5)

        # 3. Weekly Duration goal respecting mid-week start_date (Tue Nov 17 -> excludes Mon Badminton)
        midweek_goal = FitnessGoal.objects.create(
            user=self.user_a,
            title="Midweek Push",
            goal_type=FitnessGoal.GOAL_WEEKLY,
            target_minutes=120,
            start_date=tue_this_week,
        )
        midweek_data = midweek_goal.get_progress_data(reference_date=ref_wed)
        # 15 (Tue) + 45 (Wed) = 60 min (Mon 40 min excluded)
        self.assertEqual(midweek_data["completed_value"], 60)
        self.assertEqual(midweek_data["progress_percent"], 50)

        # 4. Weekly Frequency goal (counts sessions in week, excludes Old Run)
        freq_goal = FitnessGoal.objects.create(
            user=self.user_a,
            title="Weekly Sessions",
            goal_type=FitnessGoal.GOAL_WEEKLY_FREQ,
            target_minutes=6,
            reward_container=FitnessGoal.CONTAINER_POPCORN,
            start_date=mon_this_week,
        )
        freq_data = freq_goal.get_progress_data(reference_date=ref_wed)
        self.assertEqual(freq_data["completed_value"], 5)
        self.assertEqual(freq_data["remaining_value"], 1)
        self.assertEqual(freq_data["progress_percent"], 83)
        self.assertEqual(freq_data["total_minutes_in_period"], 100)

        # 5. Ended Weekly goal with earlier start_date clamps strictly to its final week
        ended_weekly = FitnessGoal.objects.create(
            user=self.user_a,
            title="Past Week Goal",
            goal_type=FitnessGoal.GOAL_WEEKLY,
            target_minutes=100,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 11, 13),  # Friday of prior week (week starts Nov 9)
        )
        Workout.objects.create(
            user=self.user_a, activity_name="October Ride", duration=90, date=date(2026, 10, 20)
        )
        ended_data = ended_weekly.get_progress_data(reference_date=ref_wed)
        # Only prev_week_day (Nov 10, 60 min) counts — October Ride (Oct 20) excluded!
        self.assertEqual(ended_data["completed_value"], 60)
        self.assertEqual(ended_data["status"], "ended")

        # 6. Upcoming Weekly goal shows clean "Starts ..." period_label and 0 progress
        future_weekly = FitnessGoal.objects.create(
            user=self.user_a,
            title="Next Month Plan",
            goal_type=FitnessGoal.GOAL_WEEKLY,
            target_minutes=150,
            start_date=date(2026, 12, 1),
        )
        future_data = future_weekly.get_progress_data(reference_date=ref_wed)
        self.assertEqual(future_data["completed_value"], 0)
        self.assertEqual(future_data["status"], "upcoming")
        self.assertIn("Starts Dec 01", future_data["period_label"])

        # 7. Timezone cookie activation safely handles valid & invalid IANA names without crashing
        self.client.force_login(self.user_a)
        self.client.cookies["fittrack_tz"] = "Asia/Kolkata"
        tz_ok = self.client.get(reverse("fitness:goals_progress_api"))
        self.assertEqual(tz_ok.status_code, 200)
        self.client.cookies["fittrack_tz"] = "Not/A_Real_Zone"
        tz_bad = self.client.get(reverse("fitness:goals_progress_api"))
        self.assertEqual(tz_bad.status_code, 200)



