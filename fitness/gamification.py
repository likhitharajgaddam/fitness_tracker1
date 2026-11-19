from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from .models import (
    Achievement,
    DailyChallenge,
    FitnessGoal,
    Sport,
    UserAchievement,
    UserChallengeCompletion,
    Workout,
)

ACHIEVEMENT_DEFINITIONS = [
    {
        "slug": "first-workout",
        "title": "First Workout",
        "description": "Complete and log your very first workout session.",
        "category": "Milestone",
        "icon_name": "bi-rocket-takeoff",
        "badge_color": "purple",
        "metric_key": "workouts_count",
        "target_value": 1,
        "reward_xp": 50,
        "display_order": 1,
    },
    {
        "slug": "early-bird",
        "title": "Early Bird",
        "description": "Complete a morning workout session before noon or log a morning routine.",
        "category": "Habit",
        "icon_name": "bi-sunrise",
        "badge_color": "peach",
        "metric_key": "morning_workout",
        "target_value": 1,
        "reward_xp": 60,
        "display_order": 2,
    },
    {
        "slug": "consistency-star",
        "title": "Consistency Star",
        "description": "Stay active for 3 consecutive days in a row.",
        "category": "Consistency",
        "icon_name": "bi-fire",
        "badge_color": "peach",
        "metric_key": "streak_days",
        "target_value": 3,
        "reward_xp": 100,
        "display_order": 3,
    },
    {
        "slug": "fitness-explorer",
        "title": "Fitness Explorer",
        "description": "Try at least 5 different exercises or sports.",
        "category": "Explorer",
        "icon_name": "bi-compass",
        "badge_color": "sky",
        "metric_key": "unique_activities",
        "target_value": 5,
        "reward_xp": 100,
        "display_order": 4,
    },
    {
        "slug": "sports-enthusiast",
        "title": "Sports Enthusiast",
        "description": "Complete 5 sessions of any curated sport.",
        "category": "Sports",
        "icon_name": "bi-trophy",
        "badge_color": "mint",
        "metric_key": "sports_sessions",
        "target_value": 5,
        "reward_xp": 120,
        "display_order": 5,
    },
    {
        "slug": "goal-crusher",
        "title": "Goal Crusher",
        "description": "Fill your first Reward Jar by reaching 100% of any fitness goal.",
        "category": "Goals",
        "icon_name": "bi-gem",
        "badge_color": "purple",
        "metric_key": "goals_completed",
        "target_value": 1,
        "reward_xp": 120,
        "display_order": 6,
    },
    {
        "slug": "weekly-warrior",
        "title": "Weekly Warrior",
        "description": "Reach 100% on a Weekly Duration or Weekly Frequency goal.",
        "category": "Goals",
        "icon_name": "bi-shield-check",
        "badge_color": "mint",
        "metric_key": "weekly_goal_completed",
        "target_value": 1,
        "reward_xp": 150,
        "display_order": 7,
    },
    {
        "slug": "marathon-mindset",
        "title": "Marathon Mindset",
        "description": "Accumulate 500 total workout minutes across all sessions.",
        "category": "Endurance",
        "icon_name": "bi-lightning-charge",
        "badge_color": "sky",
        "metric_key": "total_minutes",
        "target_value": 500,
        "reward_xp": 200,
        "display_order": 8,
    },
]

DAILY_CHALLENGE_DEFINITIONS = [
    {
        "title": "Brisk Park Walk",
        "description": "Step outside or pace indoors for a refreshing 20-minute walk.",
        "activity_name": "Walking",
        "target_duration": 20,
        "challenge_type": "activity",
        "icon_name": "bi-person-walking",
        "xp_reward": 40,
    },
    {
        "title": "Power Squat Circuit",
        "description": "Build lower-body strength with 15 minutes of controlled squats.",
        "activity_name": "Squats",
        "target_duration": 15,
        "challenge_type": "activity",
        "icon_name": "bi-graph-up-arrow",
        "xp_reward": 45,
    },
    {
        "title": "Mobility & Stretch Reset",
        "description": "Release tight muscles with 15 minutes of calm full-body stretching.",
        "activity_name": "Stretching",
        "target_duration": 15,
        "challenge_type": "activity",
        "icon_name": "bi-wind",
        "xp_reward": 35,
    },
    {
        "title": "Court Rally Session",
        "description": "Grab a racket or hit the court for 30 minutes of badminton energy.",
        "activity_name": "Badminton",
        "target_duration": 30,
        "challenge_type": "sport",
        "icon_name": "bi-lightning-charge",
        "xp_reward": 55,
    },
    {
        "title": "Sunrise Yoga Flow",
        "description": "Restore balance and core posture with 25 minutes of guided yoga.",
        "activity_name": "Yoga",
        "target_duration": 25,
        "challenge_type": "activity",
        "icon_name": "bi-sun",
        "xp_reward": 45,
    },
    {
        "title": "Core Plank Challenge",
        "description": "Strengthen your deep core stability with a 20-minute plank circuit.",
        "activity_name": "Core Plank Circuit",
        "target_duration": 20,
        "challenge_type": "activity",
        "icon_name": "bi-layers",
        "xp_reward": 50,
    },
]


def ensure_gamification_catalog() -> None:
    if Achievement.objects.count() < len(ACHIEVEMENT_DEFINITIONS):
        for item in ACHIEVEMENT_DEFINITIONS:
            Achievement.objects.update_or_create(slug=item["slug"], defaults=item)
    if DailyChallenge.objects.count() == 0:
        for item in DAILY_CHALLENGE_DEFINITIONS:
            DailyChallenge.objects.get_or_create(
                title=item["title"], defaults=item
            )


def compute_user_streaks(user, reference_date=None) -> dict:
    today = reference_date or timezone.localdate()
    dates = sorted(
        set(Workout.objects.filter(user=user).values_list("date", flat=True))
    )
    if not dates:
        return {
            "current_streak": 0,
            "best_streak": 0,
            "total_active_days": 0,
            "last_workout_date": None,
            "days_since_last": None,
            "recent_7_days": [
                {
                    "date": today - timedelta(days=offset),
                    "label": (today - timedelta(days=offset)).strftime("%a")[0],
                    "full_label": (today - timedelta(days=offset)).strftime("%b %d"),
                    "active": False,
                }
                for offset in range(6, -1, -1)
            ],
        }

    date_set = set(dates)

    # Best streak across all logged dates
    best_streak = 1
    running = 1
    for i in range(1, len(dates)):
        if dates[i] == dates[i - 1] + timedelta(days=1):
            running += 1
            best_streak = max(best_streak, running)
        else:
            running = 1

    # Current streak ending today or yesterday
    current_streak = 0
    cursor = today if today in date_set else today - timedelta(days=1)
    if cursor in date_set:
        while cursor in date_set:
            current_streak += 1
            cursor -= timedelta(days=1)

    last_date = dates[-1]
    days_since_last = (today - last_date).days

    recent_7_days = [
        {
            "date": today - timedelta(days=offset),
            "label": (today - timedelta(days=offset)).strftime("%a")[0],
            "full_label": (today - timedelta(days=offset)).strftime("%b %d"),
            "active": (today - timedelta(days=offset)) in date_set,
        }
        for offset in range(6, -1, -1)
    ]

    return {
        "current_streak": current_streak,
        "best_streak": best_streak,
        "total_active_days": len(date_set),
        "last_workout_date": last_date,
        "days_since_last": days_since_last,
        "recent_7_days": recent_7_days,
    }


def compute_user_achievement_metrics(user, reference_date=None) -> dict:
    today = reference_date or timezone.localdate()
    user_workouts = list(Workout.objects.filter(user=user))
    workouts_count = len(user_workouts)
    total_minutes = sum(w.duration for w in user_workouts)
    unique_activities = len(
        {w.activity_name.strip().lower() for w in user_workouts if w.activity_name}
    )

    sport_names = {
        name.strip().lower()
        for name in Sport.objects.values_list("name", flat=True)
    }
    sports_sessions = sum(
        1
        for w in user_workouts
        if w.activity_name.strip().lower() in sport_names
    )

    morning_workout = 0
    for w in user_workouts:
        text_blob = f"{w.activity_name} {w.notes}".lower()
        local_created = timezone.localtime(w.created_at)
        if "morning" in text_blob or "sunrise" in text_blob or "early" in text_blob:
            morning_workout = 1
            break
        if local_created.date() == w.date and local_created.hour < 12:
            morning_workout = 1
            break

    streak_info = compute_user_streaks(user, reference_date=today)

    user_goals = list(FitnessGoal.objects.filter(user=user))
    goals_completed = 0
    weekly_goal_completed = 0
    for goal in user_goals:
        progress = goal.get_progress_data(reference_date=today)
        if progress["is_completed"]:
            goals_completed += 1
            if goal.goal_type in (
                FitnessGoal.GOAL_WEEKLY,
                FitnessGoal.GOAL_WEEKLY_FREQ,
            ):
                weekly_goal_completed = 1

    return {
        "workouts_count": workouts_count,
        "total_minutes": total_minutes,
        "unique_activities": unique_activities,
        "sports_sessions": sports_sessions,
        "morning_workout": morning_workout,
        "streak_days": streak_info["best_streak"],
        "goals_completed": goals_completed,
        "weekly_goal_completed": weekly_goal_completed,
    }


def evaluate_user_gamification(
    user, just_logged_workout=None, reference_date=None
) -> dict:
    """
    Sync achievements and one-time goal completion celebrations based on real DB records.
    Returns a celebration dict if any goal just hit 100% (celebrated_at is None)
    or any achievement was newly unlocked, otherwise empty lists.
    """
    ensure_gamification_catalog()
    today = reference_date or timezone.localdate()
    metrics = compute_user_achievement_metrics(user, reference_date=today)

    # 1. Check & unlock achievements (idempotent via UniqueConstraint / get_or_create)
    newly_unlocked = []
    for achievement in Achievement.objects.all():
        current_val = metrics.get(achievement.metric_key, 0)
        if current_val >= achievement.target_value:
            ua, created = UserAchievement.objects.get_or_create(
                user=user, achievement=achievement
            )
            if created or not ua.notified:
                ua.notified = True
                ua.save(update_fields=["notified"])
                newly_unlocked.append(
                    {
                        "slug": achievement.slug,
                        "title": achievement.title,
                        "description": achievement.description,
                        "icon_name": achievement.icon_name,
                        "badge_color": achievement.badge_color,
                        "reward_xp": achievement.reward_xp,
                    }
                )

    # 2. Check goals that reached 100% and have NOT been celebrated yet
    newly_completed_goals = []
    uncelebrated_goals = FitnessGoal.objects.filter(
        user=user, is_active=True, celebrated_at__isnull=True
    )
    now = timezone.now()
    for goal in uncelebrated_goals:
        progress = goal.get_progress_data(reference_date=today)
        if progress["is_completed"]:
            goal.celebrated_at = now
            goal.save(update_fields=["celebrated_at"])
            newly_completed_goals.append(
                {
                    "id": goal.pk,
                    "title": goal.title,
                    "goal_type": goal.goal_type,
                    "target_value": progress["target_value"],
                    "unit_label": progress["unit_label"],
                    "reward_container": goal.reward_container,
                    "reward_container_label": goal.get_reward_container_display(),
                    "badge_title": goal.reward_badge_title,
                }
            )

    workout_info = None
    if just_logged_workout is not None:
        workout_info = {
            "activity_name": just_logged_workout.activity_name,
            "duration": just_logged_workout.duration,
        }

    return {
        "has_celebration": bool(newly_unlocked or newly_completed_goals),
        "newly_unlocked": newly_unlocked,
        "newly_completed_goals": newly_completed_goals,
        "workout": workout_info,
    }


def get_achievements_with_progress(user, reference_date=None) -> dict:
    ensure_gamification_catalog()
    today = reference_date or timezone.localdate()
    metrics = compute_user_achievement_metrics(user, reference_date=today)
    unlocked_map = {
        ua.achievement_id: ua
        for ua in UserAchievement.objects.filter(user=user).select_related("achievement")
    }

    items = []
    total_xp = 0
    unlocked_count = 0
    for ach in Achievement.objects.all():
        ua = unlocked_map.get(ach.pk)
        current_val = metrics.get(ach.metric_key, 0)
        is_unlocked = ua is not None
        if is_unlocked:
            unlocked_count += 1
            total_xp += ach.reward_xp
            pct = 100
        else:
            pct = (
                min(99, round((current_val / ach.target_value) * 100))
                if ach.target_value > 0
                else 0
            )
        items.append(
            {
                "achievement": ach,
                "is_unlocked": is_unlocked,
                "unlocked_at": ua.unlocked_at if ua else None,
                "current_value": min(current_val, ach.target_value),
                "raw_value": current_val,
                "target_value": ach.target_value,
                "progress_percent": pct,
            }
        )

    # Also add challenge XP
    challenge_xp = (
        UserChallengeCompletion.objects.filter(user=user)
        .select_related("challenge")
        .aggregate(total=Sum("challenge__xp_reward"))["total"]
        or 0
    )
    total_xp += challenge_xp
    adventurer_level = 1 + (total_xp // 150)
    xp_into_level = total_xp % 150

    return {
        "items": items,
        "unlocked_count": unlocked_count,
        "total_count": len(items),
        "total_xp": total_xp,
        "adventurer_level": adventurer_level,
        "xp_into_level": xp_into_level,
        "xp_for_next": 150 - xp_into_level,
        "xp_percent": round((xp_into_level / 150) * 100),
        "metrics": metrics,
    }


def get_daily_challenge_for_user(user, reference_date=None) -> dict:
    ensure_gamification_catalog()
    today = reference_date or timezone.localdate()
    challenges = list(DailyChallenge.objects.filter(is_active=True))
    if not challenges:
        return {"challenge": None, "is_completed": False}

    idx = today.toordinal() % len(challenges)
    challenge = challenges[idx]
    completion = UserChallengeCompletion.objects.filter(
        user=user, challenge=challenge, date=today
    ).first()
    return {
        "challenge": challenge,
        "is_completed": completion is not None,
        "completion": completion,
    }


def get_fitbuddy_state(
    user,
    profile,
    goal_cards=None,
    streak_info=None,
    today_minutes=0,
    page_key="dashboard",
) -> dict:
    goal_cards = goal_cards or []
    companion_key = profile.companion_choice if profile else "female"
    companion_name = "Atlas" if companion_key == "male" else "Nova"
    first_name = (
        profile.display_name().split()[0]
        if profile and profile.display_name()
        else user.username
    )

    state = "greeting"
    message = f"Hey {first_name}! Ready to move today?"
    sub_hint = "Every move counts. Log a session or spin a new sport adventure!"

    # Check if user has a near-complete goal jar
    near_goal = None
    completed_goal = None
    for item in goal_cards:
        if item["is_completed"] and not completed_goal:
            completed_goal = item
        elif not item["is_completed"] and item["progress_percent"] >= 50:
            if near_goal is None or item["progress_percent"] > near_goal["progress_percent"]:
                near_goal = item

    days_since = streak_info.get("days_since_last") if streak_info else None
    current_streak = streak_info.get("current_streak", 0) if streak_info else 0

    if page_key == "dashboard":
        if completed_goal and today_minutes > 0:
            state = "celebration"
            message = f"Woohoo, {first_name}! You filled your {completed_goal['goal'].title} jar!"
            sub_hint = f"{today_minutes} active minutes logged today."
        elif near_goal:
            state = "encouragement"
            message = (
                f"Only {near_goal['remaining_value']} more {near_goal['unit_label']} "
                f"to fill your {near_goal['goal'].title} jar!"
            )
            sub_hint = f"You're already at {near_goal['progress_percent']}%!"
        elif days_since is not None and days_since >= 2:
            state = "reminder"
            message = "Don't worry about missing a day. Let's start again with 10 gentle minutes!"
            sub_hint = "Your FitBuddy is cheering for your comeback."
        elif days_since is None:
            state = "greeting"
            message = f"Hey {first_name}! Ready to move today? Let's log your first workout!"
            sub_hint = "Pick an activity or try today's Daily Challenge."
        elif current_streak >= 3:
            state = "encouragement"
            message = f"Awesome {current_streak}-day streak, {first_name}! Keep the momentum rolling!"
            sub_hint = "Every session fills your reward jars."
        else:
            state = "greeting"
            message = f"Hey {first_name}! Let's try something fun today — how about badminton or yoga?"
            sub_hint = f"Profile focus: {profile.primary_goal}"
    elif page_key == "activities":
        state = "encouragement"
        message = "Pick any exercise below and hit Start Activity for a live guided timer!"
        sub_hint = "Each workout updates your Reward Jar automatically."
    elif page_key == "sports":
        state = "greeting"
        message = "Not sure what to play? Spin 'What Should I Play Today?' for a fresh match!"
        sub_hint = "Sports sessions unlock the Sports Enthusiast badge."
    elif page_key == "workouts":
        state = "workout"
        message = "Every minute you log powers up your Reward Jars and unlocks new badges!"
        sub_hint = "Use quick-fill chips for 1-click entry."
    elif page_key == "goals":
        if near_goal:
            state = "encouragement"
            message = f"So close! Just {near_goal['remaining_value']} {near_goal['unit_label']} left on {near_goal['goal'].title}!"
        else:
            state = "idle"
            message = "Choose a fun Reward Jar for each goal — Popcorn, Juice, Flower Pot, or Treasure Chest!"
        sub_hint = "Jars fill automatically from your saved workouts."
    elif page_key == "rewards":
        state = "celebration"
        message = "Look at all the badges and XP waiting for you! Keep filling those jars!"
        sub_hint = "Badges unlock automatically from real workout milestones."
    elif page_key == "analytics":
        state = "encouragement"
        message = "Check out your My Fitness Journey timeline and weekly consistency charts!"
        sub_hint = "Data updates live from your workout history."
    else:
        state = "idle"
        message = f"Looking good, {first_name}! Ready for your next move?"
        sub_hint = "Every move counts."

    return {
        "companion_key": companion_key,
        "companion_name": companion_name,
        "state": state,
        "message": message,
        "sub_hint": sub_hint,
    }


def build_fitness_journey_milestones(user, profile) -> list[dict]:
    milestones = [
        {
            "date": user.date_joined.date(),
            "title": "Joined FitTrack Adventure",
            "detail": f"Set primary focus to {profile.primary_goal} ({profile.fitness_level}).",
            "icon": "bi-flag-fill",
            "tone": "purple",
        }
    ]

    first_workout = Workout.objects.filter(user=user).order_by("date", "created_at").first()
    if first_workout:
        milestones.append(
            {
                "date": first_workout.date,
                "title": f"First Logged Workout: {first_workout.activity_name}",
                "detail": f"Started tracking with a {first_workout.duration}-minute session.",
                "icon": "bi-lightning-charge-fill",
                "tone": "mint",
            }
        )

    for ua in (
        UserAchievement.objects.filter(user=user)
        .select_related("achievement")
        .order_by("unlocked_at")
    ):
        milestones.append(
            {
                "date": timezone.localtime(ua.unlocked_at).date(),
                "title": f"Unlocked Badge: {ua.achievement.title}",
                "detail": f"{ua.achievement.description} (+{ua.achievement.reward_xp} XP)",
                "icon": ua.achievement.icon_name,
                "tone": ua.achievement.badge_color,
            }
        )

    for goal in FitnessGoal.objects.filter(user=user, celebrated_at__isnull=False).order_by(
        "celebrated_at"
    ):
        milestones.append(
            {
                "date": timezone.localtime(goal.celebrated_at).date(),
                "title": f"Filled {goal.get_reward_container_display()}: {goal.title}",
                "detail": f"Earned {goal.reward_badge_title} by reaching {goal.target_minutes} {goal.unit_label}.",
                "icon": "bi-trophy-fill",
                "tone": goal.theme_color,
            }
        )

    milestones.sort(key=lambda m: m["date"], reverse=True)
    return milestones
