from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone

User = get_user_model()


class UserProfile(models.Model):
    GENDER_CHOICES = [
        ("", "Prefer not to say"),
        ("Female", "Female"),
        ("Male", "Male"),
        ("Non-binary", "Non-binary"),
        ("Other", "Other"),
    ]

    FITNESS_LEVEL_CHOICES = [
        ("Beginner", "Beginner"),
        ("Intermediate", "Intermediate"),
        ("Advanced", "Advanced"),
    ]

    PRIMARY_GOAL_CHOICES = [
        ("Weight Management", "Weight Management"),
        ("Muscle Building", "Muscle Building"),
        ("Improve Stamina", "Improve Stamina"),
        ("General Fitness", "General Fitness"),
        ("Flexibility", "Flexibility"),
    ]

    ENVIRONMENT_CHOICES = [
        ("Home", "Home"),
        ("Gym", "Gym"),
        ("Outdoor", "Outdoor"),
        ("Sports", "Sports"),
    ]

    COMPANION_FEMALE = "female"
    COMPANION_MALE = "male"

    COMPANION_CHOICES = [
        (COMPANION_FEMALE, "Nova · Energetic Coach (Female Buddy)"),
        (COMPANION_MALE, "Atlas · Cheerful Trainer (Male Buddy)"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )
    age = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(10), MaxValueValidator(110)],
    )
    gender = models.CharField(max_length=25, blank=True, choices=GENDER_CHOICES)
    fitness_level = models.CharField(
        max_length=20, choices=FITNESS_LEVEL_CHOICES, default="Beginner"
    )
    primary_goal = models.CharField(
        max_length=40, choices=PRIMARY_GOAL_CHOICES, default="General Fitness"
    )
    preferred_environment = models.CharField(
        max_length=20, choices=ENVIRONMENT_CHOICES, default="Outdoor"
    )
    companion_choice = models.CharField(
        max_length=16, choices=COMPANION_CHOICES, default=COMPANION_FEMALE
    )
    tutorial_completed = models.BooleanField(default=False)
    profile_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def display_name(self) -> str:
        full_name = (self.user.get_full_name() or "").strip()
        return full_name if full_name else self.user.username

    def initials(self) -> str:
        name = self.display_name()
        parts = [p for p in name.split() if p]
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return name[:2].upper()

    def __str__(self) -> str:
        return f"{self.user.username} ({self.fitness_level} · {self.primary_goal})"


class FitnessActivity(models.Model):
    CATEGORY_CARDIO = "Cardio"
    CATEGORY_STRENGTH = "Strength"
    CATEGORY_FLEXIBILITY = "Flexibility"
    CATEGORY_FULL_BODY = "Full Body"

    CATEGORY_CHOICES = [
        (CATEGORY_CARDIO, "Cardio"),
        (CATEGORY_STRENGTH, "Strength"),
        (CATEGORY_FLEXIBILITY, "Flexibility"),
        (CATEGORY_FULL_BODY, "Full Body"),
    ]

    DIFFICULTY_BEGINNER = "Beginner"
    DIFFICULTY_INTERMEDIATE = "Intermediate"
    DIFFICULTY_ADVANCED = "Advanced"

    DIFFICULTY_CHOICES = [
        (DIFFICULTY_BEGINNER, "Beginner"),
        (DIFFICULTY_INTERMEDIATE, "Intermediate"),
        (DIFFICULTY_ADVANCED, "Advanced"),
    ]

    name = models.CharField(max_length=120, unique=True)
    description = models.TextField()
    benefits = models.TextField(
        blank=True,
        default="",
        help_text="Key health and performance benefits",
    )
    instructions = models.TextField(
        blank=True,
        default="",
        help_text="Step-by-step instructions for performing the exercise safely",
    )
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES)
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    environment = models.CharField(
        max_length=40,
        default="Home / Outdoor",
        help_text="Typical workout setting (Home, Gym, Outdoor)",
    )
    estimated_duration = models.PositiveIntegerField(
        validators=[MinValueValidator(5), MaxValueValidator(300)],
        help_text="Estimated duration in minutes",
    )
    calories_burn = models.PositiveIntegerField(
        default=150,
        validators=[MinValueValidator(10), MaxValueValidator(2500)],
        help_text="Approximate kcal burned per session",
    )
    icon_name = models.CharField(
        max_length=60,
        default="bi-activity",
        help_text="Bootstrap Icons class name (e.g., bi-person-walking)",
    )
    image_path = models.CharField(
        max_length=200,
        blank=True,
        default="images/activity_cardio_running.jpg",
        help_text="Static image path relative to static/",
    )
    target_muscles = models.CharField(
        max_length=180,
        blank=True,
        default="",
        help_text="Muscles or body areas engaged",
    )
    is_recommended = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Fitness Activity"
        verbose_name_plural = "Fitness Activities"

    def instruction_steps(self) -> list[str]:
        return [line.strip() for line in self.instructions.splitlines() if line.strip()]

    def __str__(self) -> str:
        return f"{self.name} ({self.category})"


class Sport(models.Model):
    ENV_INDOOR = "Indoor"
    ENV_OUTDOOR = "Outdoor"
    ENV_BOTH = "Indoor / Outdoor"

    ENVIRONMENT_CHOICES = [
        (ENV_INDOOR, "Indoor"),
        (ENV_OUTDOOR, "Outdoor"),
        (ENV_BOTH, "Indoor / Outdoor"),
    ]

    INTENSITY_MODERATE = "Moderate"
    INTENSITY_MOD_HIGH = "Moderate to High"
    INTENSITY_HIGH = "High"

    INTENSITY_CHOICES = [
        (INTENSITY_MODERATE, "Moderate"),
        (INTENSITY_MOD_HIGH, "Moderate to High"),
        (INTENSITY_HIGH, "High"),
    ]

    name = models.CharField(max_length=120, unique=True)
    description = models.TextField()
    benefits = models.TextField(help_text="Key health and athletic benefits")
    recommended_duration = models.PositiveIntegerField(
        validators=[MinValueValidator(10), MaxValueValidator(360)],
        help_text="Recommended session duration in minutes",
    )
    environment = models.CharField(
        max_length=25, choices=ENVIRONMENT_CHOICES, default=ENV_OUTDOOR
    )
    intensity = models.CharField(
        max_length=25, choices=INTENSITY_CHOICES, default=INTENSITY_MODERATE
    )
    difficulty_level = models.CharField(
        max_length=20,
        choices=FitnessActivity.DIFFICULTY_CHOICES,
        default=FitnessActivity.DIFFICULTY_BEGINNER,
    )
    equipment_required = models.TextField(
        blank=True,
        default="",
        help_text="Recommended gear and equipment",
    )
    instructions = models.TextField(
        blank=True,
        default="",
        help_text="Getting-started guide and session structure",
    )
    icon_name = models.CharField(
        max_length=60,
        default="bi-trophy",
        help_text="Bootstrap Icons class name",
    )
    image_path = models.CharField(
        max_length=200,
        blank=True,
        default="images/sport_court_action.jpg",
        help_text="Static image path relative to static/",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Sport"
        verbose_name_plural = "Sports"

    def instruction_steps(self) -> list[str]:
        return [line.strip() for line in self.instructions.splitlines() if line.strip()]

    def __str__(self) -> str:
        return self.name


class Workout(models.Model):
    SOURCE_MANUAL = "manual"
    SOURCE_TIMER = "timer"
    SOURCE_CHALLENGE = "challenge"

    SOURCE_CHOICES = [
        (SOURCE_MANUAL, "Manual Entry"),
        (SOURCE_TIMER, "Activity Timer"),
        (SOURCE_CHALLENGE, "Daily Challenge"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="workouts"
    )
    activity_name = models.CharField(max_length=150)
    duration = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(720)],
        help_text="Duration in minutes",
    )
    date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True)
    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default=SOURCE_MANUAL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "Workout"
        verbose_name_plural = "Workouts"

    def clean(self) -> None:
        super().clean()
        if self.activity_name:
            self.activity_name = self.activity_name.strip()
        if not self.activity_name or len(self.activity_name) < 2:
            raise ValidationError(
                {
                    "activity_name": "Please enter an activity name (at least 2 characters)."
                }
            )
        if self.duration is not None and (self.duration < 1 or self.duration > 720):
            raise ValidationError(
                {"duration": "Duration must be between 1 and 720 minutes."}
            )
        if self.date and self.date > timezone.localdate() + timedelta(days=1):
            raise ValidationError(
                {"date": "Workout date cannot be set in the future."}
            )

    def __str__(self) -> str:
        return f"{self.activity_name} - {self.duration} min ({self.date})"


class FitnessGoal(models.Model):
    GOAL_DAILY = "Daily"
    GOAL_WEEKLY = "Weekly"
    GOAL_WEEKLY_FREQ = "Weekly Frequency"

    GOAL_TYPE_CHOICES = [
        (GOAL_DAILY, "Daily Duration (Minutes)"),
        (GOAL_WEEKLY, "Weekly Duration (Minutes)"),
        (GOAL_WEEKLY_FREQ, "Weekly Frequency (Workouts)"),
    ]

    CONTAINER_POPCORN = "popcorn"
    CONTAINER_JUICE = "juice"
    CONTAINER_BOTTLE = "bottle"
    CONTAINER_FLOWER = "flower"
    CONTAINER_TREASURE = "treasure"
    CONTAINER_FISHTANK = "fishtank"

    CONTAINER_CHOICES = [
        (CONTAINER_POPCORN, "Popcorn Bucket"),
        (CONTAINER_JUICE, "Juice Glass"),
        (CONTAINER_BOTTLE, "Water Bottle"),
        (CONTAINER_FLOWER, "Flower Pot"),
        (CONTAINER_TREASURE, "Treasure Chest"),
        (CONTAINER_FISHTANK, "Fish Tank"),
    ]

    THEME_PURPLE = "purple"
    THEME_MINT = "mint"
    THEME_PEACH = "peach"
    THEME_SKY = "sky"

    THEME_CHOICES = [
        (THEME_PURPLE, "Vibrant Purple"),
        (THEME_MINT, "Mint Green"),
        (THEME_PEACH, "Warm Peach"),
        (THEME_SKY, "Sky Blue"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="fitness_goals"
    )
    title = models.CharField(max_length=150)
    goal_type = models.CharField(
        max_length=25, choices=GOAL_TYPE_CHOICES, default=GOAL_DAILY
    )
    target_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3000)],
        help_text="Target minutes (for duration goals) or sessions (for frequency goals)",
    )
    reward_container = models.CharField(
        max_length=20, choices=CONTAINER_CHOICES, default=CONTAINER_JUICE
    )
    theme_color = models.CharField(
        max_length=20, choices=THEME_CHOICES, default=THEME_PURPLE
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    celebrated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_active", "-created_at"]
        verbose_name = "Fitness Goal"
        verbose_name_plural = "Fitness Goals"

    @property
    def is_frequency_goal(self) -> bool:
        return self.goal_type == self.GOAL_WEEKLY_FREQ

    @property
    def unit_label(self) -> str:
        return "sessions" if self.is_frequency_goal else "min"

    @property
    def reward_badge_title(self) -> str:
        if self.goal_type == self.GOAL_DAILY:
            return "Daily Champion Badge"
        if self.goal_type == self.GOAL_WEEKLY_FREQ:
            return "Streak Builder Badge"
        return "Weekly Warrior Badge"

    def clean(self) -> None:
        super().clean()
        if self.title:
            self.title = self.title.strip()
        if not self.title or len(self.title) < 3:
            raise ValidationError(
                {
                    "title": "Please provide a descriptive goal title (at least 3 characters)."
                }
            )
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": "End date cannot be earlier than start date."}
            )
        if self.target_minutes is not None:
            if self.is_frequency_goal:
                if self.target_minutes < 1 or self.target_minutes > 21:
                    raise ValidationError(
                        {
                            "target_minutes": "Weekly workout frequency target must be between 1 and 21 sessions."
                        }
                    )
            else:
                if self.target_minutes < 5:
                    raise ValidationError(
                        {
                            "target_minutes": "Duration target must be at least 5 minutes."
                        }
                    )
                if self.goal_type == self.GOAL_DAILY and self.target_minutes > 720:
                    raise ValidationError(
                        {
                            "target_minutes": "A daily goal cannot exceed 720 minutes (12 hours)."
                        }
                    )

    def get_progress_data(self, reference_date=None) -> dict:
        today = reference_date or timezone.localdate()
        user_workouts = Workout.objects.filter(user=self.user)
        period_start = None
        period_end = None
        period_status = "active"

        if self.goal_type == self.GOAL_DAILY:
            target_date = today
            if self.end_date and today > self.end_date:
                target_date = self.end_date
                period_status = "ended"
            if self.start_date and target_date < self.start_date:
                queryset = user_workouts.none()
                period_label = f"Starts {self.start_date.strftime('%b %d')}"
                period_start = self.start_date
                period_end = self.end_date or self.start_date
                period_status = "upcoming"
            else:
                queryset = user_workouts.filter(date=target_date)
                period_start = target_date
                period_end = target_date
                if target_date == today:
                    period_label = f"Today ({target_date.strftime('%b %d')})"
                else:
                    period_label = f"Ended {target_date.strftime('%b %d')}"
        else:
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)

            if self.end_date and today > self.end_date:
                # For ended weekly goals, evaluate strictly within the goal's final week
                # clamped to start_date so prior historical weeks are excluded.
                end_week_start = self.end_date - timedelta(days=self.end_date.weekday())
                window_end = self.end_date
                window_start = (
                    max(end_week_start, self.start_date)
                    if self.start_date
                    else end_week_start
                )
                period_status = "ended"
            else:
                window_start = (
                    max(week_start, self.start_date) if self.start_date else week_start
                )
                window_end = (
                    min(week_end, self.end_date) if self.end_date else week_end
                )

            if self.start_date and window_end < window_start:
                queryset = user_workouts.none()
                period_start = self.start_date
                period_end = self.end_date or self.start_date
                period_label = f"Starts {self.start_date.strftime('%b %d')}"
                period_status = "upcoming"
            elif window_end < window_start:
                queryset = user_workouts.none()
                period_start = window_start
                period_end = window_end
                period_label = (
                    f"{window_start.strftime('%b %d')} – {window_end.strftime('%b %d')}"
                )
            else:
                queryset = user_workouts.filter(
                    date__gte=window_start, date__lte=window_end
                )
                period_start = window_start
                period_end = window_end
                period_label = (
                    f"{window_start.strftime('%b %d')} – {window_end.strftime('%b %d')}"
                )

        period_workouts = list(queryset.order_by("-date", "-created_at"))
        workout_count = len(period_workouts)
        total_minutes_in_period = sum(w.duration for w in period_workouts)

        # Build per-activity breakdown so each Reward Jar displays what was done & how much time
        breakdown_map = {}
        contributing_workouts = []
        for w in period_workouts:
            clean_name = (w.activity_name or "").strip() or "Workout"
            key = clean_name.lower()
            entry = breakdown_map.get(key)
            if entry is None:
                entry = {
                    "activity_name": clean_name,
                    "total_minutes": 0,
                    "session_count": 0,
                }
                breakdown_map[key] = entry
            entry["total_minutes"] += w.duration
            entry["session_count"] += 1
            contributing_workouts.append(
                {
                    "id": w.pk,
                    "activity_name": clean_name,
                    "duration": w.duration,
                    "date": w.date,
                }
            )

        activity_breakdown = list(breakdown_map.values())
        for row in activity_breakdown:
            if self.target_minutes > 0:
                basis = (
                    row["session_count"]
                    if self.is_frequency_goal
                    else row["total_minutes"]
                )
                row["percent_of_goal"] = round((basis / self.target_minutes) * 100)
            else:
                row["percent_of_goal"] = 0

        if self.is_frequency_goal:
            activity_breakdown.sort(
                key=lambda r: (
                    -r["session_count"],
                    -r["total_minutes"],
                    r["activity_name"].lower(),
                )
            )
            completed_value = workout_count
        else:
            activity_breakdown.sort(
                key=lambda r: (
                    -r["total_minutes"],
                    -r["session_count"],
                    r["activity_name"].lower(),
                )
            )
            completed_value = total_minutes_in_period

        raw_percent = (
            round((completed_value / self.target_minutes) * 100)
            if self.target_minutes > 0
            else 0
        )
        progress_percent = min(100, raw_percent)
        remaining_value = max(0, self.target_minutes - completed_value)
        is_completed = completed_value >= self.target_minutes

        if is_completed:
            status = "completed"
        elif not self.is_active:
            status = "paused"
        else:
            status = period_status

        return {
            "completed_value": completed_value,
            "target_value": self.target_minutes,
            "completed_minutes": completed_value,
            "target_minutes": self.target_minutes,
            "remaining_value": remaining_value,
            "remaining_minutes": remaining_value,
            "unit_label": self.unit_label,
            "progress_percent": progress_percent,
            "raw_percent": raw_percent,
            "is_completed": is_completed,
            "is_active": self.is_active,
            "status": status,
            "period_label": period_label,
            "period_start": period_start,
            "period_end": period_end,
            "workout_count": workout_count,
            "total_minutes_in_period": total_minutes_in_period,
            "activity_breakdown": activity_breakdown,
            "contributing_workouts": contributing_workouts,
        }

    def __str__(self) -> str:
        return f"{self.title} ({self.goal_type}: {self.target_minutes} {self.unit_label})"


class Achievement(models.Model):
    slug = models.SlugField(max_length=64, unique=True)
    title = models.CharField(max_length=120)
    description = models.TextField()
    category = models.CharField(max_length=40, default="Milestone")
    icon_name = models.CharField(max_length=60, default="bi-award")
    badge_color = models.CharField(max_length=20, default="purple")
    metric_key = models.CharField(max_length=50)
    target_value = models.PositiveIntegerField(default=1)
    reward_xp = models.PositiveIntegerField(default=50)
    display_order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "Achievement"
        verbose_name_plural = "Achievements"

    def __str__(self) -> str:
        return self.title


class UserAchievement(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_achievements"
    )
    achievement = models.ForeignKey(
        Achievement, on_delete=models.CASCADE, related_name="unlocks"
    )
    unlocked_at = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)

    class Meta:
        ordering = ["-unlocked_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "achievement"],
                name="unique_user_achievement",
            )
        ]
        verbose_name = "User Achievement"
        verbose_name_plural = "User Achievements"

    def __str__(self) -> str:
        return f"{self.user.username} - {self.achievement.title}"


class DailyChallenge(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField()
    activity_name = models.CharField(max_length=120)
    target_duration = models.PositiveIntegerField(
        validators=[MinValueValidator(5), MaxValueValidator(180)],
        default=20,
    )
    challenge_type = models.CharField(
        max_length=20,
        choices=[("activity", "Fitness Activity"), ("sport", "Sport")],
        default="activity",
    )
    icon_name = models.CharField(max_length=60, default="bi-stars")
    xp_reward = models.PositiveIntegerField(default=40)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Daily Challenge"
        verbose_name_plural = "Daily Challenges"

    def __str__(self) -> str:
        return f"{self.title} ({self.target_duration} min)"


class UserChallengeCompletion(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="challenge_completions"
    )
    challenge = models.ForeignKey(
        DailyChallenge, on_delete=models.CASCADE, related_name="completions"
    )
    date = models.DateField(default=timezone.localdate)
    workout = models.ForeignKey(
        Workout,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="challenge_entries",
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-completed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "challenge", "date"],
                name="unique_daily_challenge_per_user_day",
            )
        ]
        verbose_name = "Daily Challenge Completion"
        verbose_name_plural = "Daily Challenge Completions"

    def __str__(self) -> str:
        return f"{self.user.username} completed {self.challenge.title} on {self.date}"

