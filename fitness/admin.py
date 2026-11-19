from django.contrib import admin

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


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "age",
        "fitness_level",
        "primary_goal",
        "preferred_environment",
        "companion_choice",
        "tutorial_completed",
        "profile_completed",
        "updated_at",
    )
    list_filter = (
        "fitness_level",
        "primary_goal",
        "preferred_environment",
        "companion_choice",
        "tutorial_completed",
        "profile_completed",
    )
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    ordering = ("user__username",)


@admin.register(FitnessActivity)
class FitnessActivityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "difficulty_level",
        "environment",
        "estimated_duration",
        "calories_burn",
        "is_recommended",
    )
    list_filter = ("category", "difficulty_level", "is_recommended")
    search_fields = ("name", "description", "benefits", "target_muscles")
    list_editable = ("is_recommended",)
    ordering = ("name",)


@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "environment",
        "intensity",
        "difficulty_level",
        "recommended_duration",
    )
    list_filter = ("environment", "intensity", "difficulty_level")
    search_fields = ("name", "description", "benefits", "equipment_required")
    ordering = ("name",)


@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):
    list_display = (
        "activity_name",
        "user",
        "duration",
        "source",
        "date",
        "created_at",
    )
    list_filter = ("date", "source", "user")
    search_fields = ("activity_name", "notes", "user__username")
    date_hierarchy = "date"
    ordering = ("-date", "-created_at")


@admin.register(FitnessGoal)
class FitnessGoalAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "goal_type",
        "target_minutes",
        "reward_container",
        "theme_color",
        "is_active",
        "celebrated_at",
    )
    list_filter = ("goal_type", "reward_container", "is_active", "user")
    search_fields = ("title", "user__username")
    list_editable = ("is_active",)
    ordering = ("-is_active", "-created_at")


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "metric_key",
        "target_value",
        "reward_xp",
        "display_order",
    )
    list_filter = ("category", "badge_color")
    search_fields = ("title", "description", "slug")
    ordering = ("display_order", "id")


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ("user", "achievement", "unlocked_at", "notified")
    list_filter = ("achievement", "notified")
    search_fields = ("user__username", "achievement__title")
    ordering = ("-unlocked_at",)


@admin.register(DailyChallenge)
class DailyChallengeAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "activity_name",
        "target_duration",
        "challenge_type",
        "xp_reward",
        "is_active",
    )
    list_filter = ("challenge_type", "is_active")
    search_fields = ("title", "activity_name", "description")
    list_editable = ("is_active",)


@admin.register(UserChallengeCompletion)
class UserChallengeCompletionAdmin(admin.ModelAdmin):
    list_display = ("user", "challenge", "date", "completed_at")
    list_filter = ("date", "challenge")
    search_fields = ("user__username", "challenge__title")
    ordering = ("-date", "-completed_at")
