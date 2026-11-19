from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import FitTrackPasswordResetForm, FitTrackSetPasswordForm

app_name = "fitness"

urlpatterns = [
    # Public & Authentication
    path("", views.landing, name="landing"),
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # Password Reset (Django built-in views with FitTrack templates)
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="fitness/password_reset_form.html",
            email_template_name="fitness/password_reset_email.txt",
            subject_template_name="fitness/password_reset_subject.txt",
            form_class=FitTrackPasswordResetForm,
            success_url=reverse_lazy("fitness:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="fitness/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="fitness/password_reset_confirm.html",
            form_class=FitTrackSetPasswordForm,
            success_url=reverse_lazy("fitness:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="fitness/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
    # Core Application Workspace
    path("dashboard/", views.dashboard, name="dashboard"),
    path("challenge/complete/", views.complete_daily_challenge, name="complete_challenge"),
    path("tutorial/complete/", views.complete_tutorial, name="complete_tutorial"),
    path("tutorial/replay/", views.replay_tutorial, name="replay_tutorial"),
    path("profile/setup/", views.profile_setup, name="profile_setup"),
    path("profile/", views.profile_view, name="profile"),
    path("settings/", views.settings_view, name="settings"),
    # Activities & Sports (Public + Authenticated App Shell)
    path("activities/", views.activities_list, name="activities"),
    path("activities/<int:pk>/", views.activity_detail, name="activity_detail"),
    path(
        "activities/<int:pk>/log-session/",
        views.log_activity_session,
        name="log_activity_session",
    ),
    path("sports/", views.sports_list, name="sports"),
    path("sports/<int:pk>/", views.sport_detail, name="sport_detail"),
    # Workouts CRUD
    path("workouts/", views.workout_tracker, name="workouts"),
    path("workouts/<int:pk>/edit/", views.edit_workout, name="edit_workout"),
    path("workouts/<int:pk>/delete/", views.delete_workout, name="delete_workout"),
    # Fitness Goals & Reward Jars CRUD
    path("goals/", views.goals_view, name="goals"),
    path("goals/<int:pk>/edit/", views.edit_goal, name="edit_goal"),
    path("goals/<int:pk>/toggle/", views.toggle_goal, name="toggle_goal"),
    path("goals/<int:pk>/delete/", views.delete_goal, name="delete_goal"),
    path("api/goals/progress/", views.goals_progress_api, name="goals_progress_api"),
    # Rewards & Achievements
    path("rewards/", views.rewards_view, name="rewards"),
    # Progress & Analytics
    path("analytics/", views.analytics_view, name="analytics"),
]
