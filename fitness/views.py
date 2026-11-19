import json
from collections import defaultdict
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q, Sum
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .forms import (
    FitnessGoalForm,
    FitTrackPasswordChangeForm,
    LoginForm,
    ProfileSetupForm,
    ProfileUpdateForm,
    SignUpForm,
    WorkoutForm,
)
from .gamification import (
    build_fitness_journey_milestones,
    compute_user_streaks,
    evaluate_user_gamification,
    get_achievements_with_progress,
    get_daily_challenge_for_user,
    get_fitbuddy_state,
)
from .models import (
    FitnessActivity,
    FitnessGoal,
    Sport,
    UserChallengeCompletion,
    UserProfile,
    Workout,
)

MOTIVATIONAL_QUOTES = [
    {
        "quote": "Every move counts. Even ten mindful minutes moves your jar closer to full.",
        "author": "FitTrack Principle",
        "theme": "Daily Momentum",
    },
    {
        "quote": "Take care of your body. It is the only place you have to live.",
        "author": "Jim Rohn",
        "theme": "Consistency",
    },
    {
        "quote": "Success isn't always about greatness. It's about consistency. Consistent hard work leads to success.",
        "author": "Dwayne Johnson",
        "theme": "Discipline",
    },
    {
        "quote": "Movement is a medicine for creating change in a person's physical, emotional, and mental states.",
        "author": "Carol Welch",
        "theme": "Wellbeing",
    },
    {
        "quote": "Energy and persistence conquer all things.",
        "author": "Benjamin Franklin",
        "theme": "Endurance",
    },
]

DEMO_TESTIMONIALS = [
    {
        "name": "Maya Nair",
        "role": "Computer Science Undergraduate · Demo Profile",
        "quote": "Watching my Juice Glass reward jar fill up after evening runs turned sporadic workouts into a steady 4-day habit.",
        "metric": "420 min logged / month",
    },
    {
        "name": "Daniel Brooks",
        "role": "Campus Badminton Player · Demo Profile",
        "quote": "The What Should I Play Today picker and Sports Enthusiast badge keep every week feeling like a fresh game.",
        "metric": "14-day active streak",
    },
    {
        "name": "Priya Kulkarni",
        "role": "Morning Yoga & Walking Member · Demo Profile",
        "quote": "Having FitBuddy cheer me on with the live activity timer makes 15-minute mobility breaks genuinely fun.",
        "metric": "5 badges unlocked",
    },
]


def get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def queue_celebration(request, celebration: dict) -> None:
    if celebration and celebration.get("has_celebration"):
        request.session["pending_celebration"] = celebration


def pop_celebration(request, user=None, reference_date=None):
    pending = request.session.pop("pending_celebration", None)
    if pending:
        return pending
    if user is not None and user.is_authenticated:
        fresh = evaluate_user_gamification(user, reference_date=reference_date)
        if fresh.get("has_celebration"):
            return fresh
    return None


def build_activity_visual_map() -> dict:
    visual_map = {}
    for act in FitnessActivity.objects.values("name", "image_path", "icon_name"):
        visual_map[act["name"].strip().lower()] = {
            "image_path": act["image_path"],
            "icon_name": act["icon_name"],
        }
    for sp in Sport.objects.values("name", "image_path", "icon_name"):
        visual_map[sp["name"].strip().lower()] = {
            "image_path": sp["image_path"],
            "icon_name": sp["icon_name"],
        }
    return visual_map


def recommend_activities_for_profile(profile, limit=4):
    activities = list(FitnessActivity.objects.all())
    goal_category_map = {
        "Weight Management": {
            FitnessActivity.CATEGORY_CARDIO,
            FitnessActivity.CATEGORY_FULL_BODY,
        },
        "Improve Stamina": {
            FitnessActivity.CATEGORY_CARDIO,
            FitnessActivity.CATEGORY_FULL_BODY,
        },
        "Muscle Building": {
            FitnessActivity.CATEGORY_STRENGTH,
            FitnessActivity.CATEGORY_FULL_BODY,
        },
        "Flexibility": {FitnessActivity.CATEGORY_FLEXIBILITY},
        "General Fitness": {
            FitnessActivity.CATEGORY_CARDIO,
            FitnessActivity.CATEGORY_STRENGTH,
            FitnessActivity.CATEGORY_FLEXIBILITY,
        },
    }
    preferred_cats = goal_category_map.get(profile.primary_goal, set())

    def score(activity):
        pts = 0
        if activity.difficulty_level == profile.fitness_level:
            pts += 4
        if activity.category in preferred_cats:
            pts += 3
        if profile.preferred_environment.lower() in activity.environment.lower():
            pts += 2
        if activity.is_recommended:
            pts += 1
        return (-pts, activity.name)

    activities.sort(key=score)
    return activities[:limit]


def recommend_sports_for_profile(profile, limit=4):
    sports = list(Sport.objects.all())

    def score(sport):
        pts = 0
        if sport.difficulty_level == profile.fitness_level:
            pts += 3
        if profile.preferred_environment == "Outdoor" and "Outdoor" in sport.environment:
            pts += 3
        elif profile.preferred_environment == "Home" and "Indoor" in sport.environment:
            pts += 2
        elif profile.preferred_environment == "Sports":
            pts += 2
        return (-pts, sport.name)

    sports.sort(key=score)
    return sports[:limit]


def landing(request):
    if request.user.is_authenticated:
        return redirect("fitness:dashboard")

    preview_activities = FitnessActivity.objects.filter(is_recommended=True)[:4]
    if not preview_activities:
        preview_activities = FitnessActivity.objects.all()[:4]
    preview_sports = Sport.objects.all()[:4]

    context = {
        "preview_activities": preview_activities,
        "preview_sports": preview_sports,
        "activity_count": FitnessActivity.objects.count(),
        "sport_count": Sport.objects.count(),
        "demo_testimonials": DEMO_TESTIMONIALS,
    }
    return render(request, "fitness/landing.html", context)


def csrf_failure_view(request, reason=""):
    return render(
        request,
        "fitness/csrf_error.html",
        {"reason": reason},
        status=403,
    )


@never_cache
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("fitness:dashboard")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(
                request,
                user,
                backend="fitness.backends.EmailOrUsernameModelBackend",
            )
            request.session.set_expiry(1209600)
            messages.success(
                request,
                f"Welcome to FitTrack, {user.first_name or user.username}! Pick your FitBuddy and personalize your adventure.",
            )
            return redirect("fitness:profile_setup")
        messages.error(
            request, "Please correct the highlighted fields to complete registration."
        )
    else:
        form = SignUpForm()
        get_token(request)
        request.META["CSRF_COOKIE_NEEDS_UPDATE"] = True

    return render(request, "fitness/signup.html", {"form": form})


@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect("fitness:dashboard")

    next_url = (request.GET.get("next") or request.POST.get("next") or "").strip()

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(
                request,
                user,
                backend=getattr(
                    user,
                    "backend",
                    "fitness.backends.EmailOrUsernameModelBackend",
                ),
            )
            if form.cleaned_data.get("remember_me"):
                request.session.set_expiry(1209600)  # 14 days
            else:
                request.session.set_expiry(86400)  # 24 hours (reliable across iframe reloads)

            profile = get_or_create_profile(user)
            messages.success(
                request,
                f"Welcome back, {profile.display_name()}! Every move counts today.",
            )
            disallowed_next = {reverse("fitness:login"), reverse("fitness:logout")}
            if (
                next_url
                and next_url not in disallowed_next
                and url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                )
            ):
                return redirect(next_url)
            return redirect("fitness:dashboard")
    else:
        form = LoginForm(request)
        get_token(request)
        request.META["CSRF_COOKIE_NEEDS_UPDATE"] = True

    return render(
        request,
        "fitness/login.html",
        {"form": form, "next": next_url},
    )


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "You have been signed out safely. See you next session!")
    return redirect("fitness:landing")


@login_required
def profile_setup(request):
    profile = get_or_create_profile(request.user)

    if request.method == "POST":
        form = ProfileSetupForm(request.POST, instance=profile)
        if form.is_valid():
            saved_profile = form.save(commit=False)
            saved_profile.profile_completed = True
            saved_profile.save()
            messages.success(
                request,
                "Your fitness profile & FitBuddy are ready! Welcome to your Fitness World.",
            )
            return redirect("fitness:dashboard")
        messages.error(request, "Please review the highlighted profile fields.")
    else:
        form = ProfileSetupForm(instance=profile)

    return render(
        request,
        "fitness/profile_setup.html",
        {"form": form, "profile": profile},
    )


@never_cache
@login_required
def dashboard(request):
    profile = get_or_create_profile(request.user)
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    user_workouts = Workout.objects.filter(user=request.user)
    total_workouts = user_workouts.count()
    total_minutes = user_workouts.aggregate(total=Sum("duration"))["total"] or 0
    activities_completed = (
        user_workouts.values("activity_name").distinct().count()
    )
    today_minutes = (
        user_workouts.filter(date=today).aggregate(total=Sum("duration"))["total"]
        or 0
    )

    # Weekly Activity Chart (Mon -> Sun for current week)
    weekly_rows = (
        user_workouts.filter(date__gte=week_start, date__lte=week_end)
        .values("date")
        .annotate(total=Sum("duration"))
    )
    minutes_by_day = {row["date"]: row["total"] for row in weekly_rows}
    weekly_labels = []
    weekly_values = []
    for offset in range(7):
        day_date = week_start + timedelta(days=offset)
        weekly_labels.append(day_date.strftime("%a"))
        weekly_values.append(minutes_by_day.get(day_date, 0))

    all_user_goals = list(FitnessGoal.objects.filter(user=request.user))
    all_goal_cards = [
        {"goal": goal, **goal.get_progress_data(reference_date=today)}
        for goal in all_user_goals
    ]
    active_goal_cards = [item for item in all_goal_cards if item["goal"].is_active]
    active_goals_count = len(active_goal_cards)
    goals_completed_count = sum(
        1 for item in all_goal_cards if item["is_completed"]
    )
    goal_cards = active_goal_cards[:6]
    featured_goal = goal_cards[0] if goal_cards else None

    streak_info = compute_user_streaks(request.user, reference_date=today)
    daily_challenge_data = get_daily_challenge_for_user(
        request.user, reference_date=today
    )
    achievements_summary = get_achievements_with_progress(
        request.user, reference_date=today
    )

    pending_celebration = pop_celebration(
        request, user=request.user, reference_date=today
    )

    recommended_activities = recommend_activities_for_profile(profile, limit=4)
    featured_sports = recommend_sports_for_profile(profile, limit=4)
    recent_workouts = user_workouts[:5]
    visual_map = build_activity_visual_map()

    quote_index = today.toordinal() % len(MOTIVATIONAL_QUOTES)
    featured_quote = MOTIVATIONAL_QUOTES[quote_index]

    fitbuddy = get_fitbuddy_state(
        request.user,
        profile,
        goal_cards=goal_cards,
        streak_info=streak_info,
        today_minutes=today_minutes,
        page_key="dashboard",
    )

    show_tutorial = (
        not profile.tutorial_completed or request.GET.get("tour") == "1"
    )

    context = {
        "profile": profile,
        "total_workouts": total_workouts,
        "total_minutes": total_minutes,
        "today_minutes": today_minutes,
        "activities_completed": activities_completed,
        "active_goals_count": active_goals_count,
        "goals_completed_count": goals_completed_count,
        "weekly_minutes": sum(weekly_values),
        "weekly_chart_labels_json": json.dumps(weekly_labels),
        "weekly_chart_values_json": json.dumps(weekly_values),
        "week_range_label": f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d')}",
        "goal_cards": goal_cards,
        "featured_goal": featured_goal,
        "streak_info": streak_info,
        "daily_challenge_data": daily_challenge_data,
        "achievements_summary": achievements_summary,
        "recommended_activities": recommended_activities,
        "featured_sports": featured_sports,
        "recent_workouts": recent_workouts,
        "visual_map": visual_map,
        "featured_quote": featured_quote,
        "quotes_json": json.dumps(MOTIVATIONAL_QUOTES),
        "today": today,
        "fitbuddy": fitbuddy,
        "pending_celebration": pending_celebration,
        "pending_celebration_json": json.dumps(pending_celebration)
        if pending_celebration
        else "null",
        "show_tutorial": show_tutorial,
    }
    return render(request, "fitness/dashboard.html", context)


@login_required
@require_POST
def complete_daily_challenge(request):
    today = timezone.localdate()
    challenge_data = get_daily_challenge_for_user(request.user, reference_date=today)
    challenge = challenge_data.get("challenge")
    if challenge is None:
        messages.error(request, "No active daily challenge is available today.")
        return redirect("fitness:dashboard")

    if challenge_data.get("is_completed"):
        messages.info(
            request,
            f"You already completed today's challenge: {challenge.title}!",
        )
        return redirect("fitness:dashboard")

    workout = Workout.objects.create(
        user=request.user,
        activity_name=challenge.activity_name,
        duration=challenge.target_duration,
        date=today,
        notes=f"Daily Challenge: {challenge.title}",
        source=Workout.SOURCE_CHALLENGE,
    )
    UserChallengeCompletion.objects.create(
        user=request.user,
        challenge=challenge,
        date=today,
        workout=workout,
    )

    celebration = evaluate_user_gamification(
        request.user, just_logged_workout=workout, reference_date=today
    )
    if not celebration.get("has_celebration"):
        celebration = {
            "has_celebration": True,
            "newly_unlocked": [],
            "newly_completed_goals": [],
            "workout": {
                "activity_name": workout.activity_name,
                "duration": workout.duration,
            },
            "challenge_completed": {
                "title": challenge.title,
                "xp_reward": challenge.xp_reward,
            },
        }
    else:
        celebration["challenge_completed"] = {
            "title": challenge.title,
            "xp_reward": challenge.xp_reward,
        }
    queue_celebration(request, celebration)

    messages.success(
        request,
        f"Daily Challenge completed! Logged {challenge.target_duration} min of {challenge.activity_name} (+{challenge.xp_reward} XP).",
    )
    return redirect("fitness:dashboard")


@login_required
@require_POST
def complete_tutorial(request):
    profile = get_or_create_profile(request.user)
    if not profile.tutorial_completed:
        profile.tutorial_completed = True
        profile.save(update_fields=["tutorial_completed"])
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    return redirect("fitness:dashboard")


@login_required
@require_POST
def replay_tutorial(request):
    profile = get_or_create_profile(request.user)
    profile.tutorial_completed = False
    profile.save(update_fields=["tutorial_completed"])
    messages.info(request, "FitBuddy's interactive guide is ready!")
    return redirect(f"{reverse('fitness:dashboard')}?tour=1")


def activities_list(request):
    selected_category = request.GET.get("category", "").strip()
    selected_difficulty = request.GET.get("difficulty", "").strip()
    search_query = request.GET.get("q", "").strip()

    activities = FitnessActivity.objects.all()

    valid_categories = [choice[0] for choice in FitnessActivity.CATEGORY_CHOICES]
    valid_difficulties = [choice[0] for choice in FitnessActivity.DIFFICULTY_CHOICES]

    if selected_category in valid_categories:
        activities = activities.filter(category=selected_category)
    else:
        selected_category = ""

    if selected_difficulty in valid_difficulties:
        activities = activities.filter(difficulty_level=selected_difficulty)
    else:
        selected_difficulty = ""

    if search_query:
        activities = activities.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(benefits__icontains=search_query)
        )

    base_template = (
        "base_app.html" if request.user.is_authenticated else "base_public.html"
    )
    profile = get_or_create_profile(request.user) if request.user.is_authenticated else None
    fitbuddy = (
        get_fitbuddy_state(request.user, profile, page_key="activities")
        if request.user.is_authenticated
        else None
    )

    context = {
        "base_template": base_template,
        "profile": profile,
        "fitbuddy": fitbuddy,
        "activities": activities,
        "categories": valid_categories,
        "difficulties": valid_difficulties,
        "selected_category": selected_category,
        "selected_difficulty": selected_difficulty,
        "search_query": search_query,
        "total_available": FitnessActivity.objects.count(),
    }
    return render(request, "fitness/activities.html", context)


def activity_detail(request, pk):
    activity = get_object_or_404(FitnessActivity, pk=pk)
    related_activities = (
        FitnessActivity.objects.filter(category=activity.category)
        .exclude(pk=activity.pk)[:3]
    )
    base_template = (
        "base_app.html" if request.user.is_authenticated else "base_public.html"
    )
    profile = get_or_create_profile(request.user) if request.user.is_authenticated else None
    fitbuddy = (
        get_fitbuddy_state(request.user, profile, page_key="activities")
        if request.user.is_authenticated
        else None
    )
    pending_celebration = (
        pop_celebration(request, user=request.user)
        if request.user.is_authenticated
        else None
    )

    return render(
        request,
        "fitness/activity_detail.html",
        {
            "base_template": base_template,
            "profile": profile,
            "fitbuddy": fitbuddy,
            "activity": activity,
            "related_activities": related_activities,
            "pending_celebration": pending_celebration,
            "pending_celebration_json": json.dumps(pending_celebration)
            if pending_celebration
            else "null",
        },
    )


@login_required
@require_POST
def log_activity_session(request, pk):
    activity = get_object_or_404(FitnessActivity, pk=pk)
    raw_duration = (request.POST.get("duration") or "").strip()
    notes = (request.POST.get("notes") or "").strip()

    try:
        duration = int(raw_duration)
    except ValueError:
        duration = activity.estimated_duration

    if duration < 1 or duration > 720:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"ok": False, "error": "Duration must be between 1 and 720 minutes."},
                status=400,
            )
        messages.error(request, "Duration must be between 1 and 720 minutes.")
        return redirect("fitness:activity_detail", pk=activity.pk)

    today = timezone.localdate()
    workout = Workout.objects.create(
        user=request.user,
        activity_name=activity.name,
        duration=duration,
        date=today,
        notes=notes or f"Completed guided {activity.name} session.",
        source=Workout.SOURCE_TIMER,
    )
    celebration = evaluate_user_gamification(
        request.user, just_logged_workout=workout, reference_date=today
    )
    if not celebration.get("has_celebration"):
        celebration = {
            "has_celebration": True,
            "newly_unlocked": [],
            "newly_completed_goals": [],
            "workout": {
                "activity_name": workout.activity_name,
                "duration": workout.duration,
            },
        }
    queue_celebration(request, celebration)

    messages.success(
        request,
        f"Awesome work! Saved {workout.duration} min of {workout.activity_name} to your workout log.",
    )
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {
                "ok": True,
                "redirect_url": reverse("fitness:workouts"),
                "celebration": celebration,
            }
        )
    return redirect("fitness:workouts")


def sports_list(request):
    selected_environment = request.GET.get("environment", "").strip()
    selected_intensity = request.GET.get("intensity", "").strip()
    selected_difficulty = request.GET.get("difficulty", "").strip()
    search_query = request.GET.get("q", "").strip()

    sports = Sport.objects.all()

    valid_environments = [choice[0] for choice in Sport.ENVIRONMENT_CHOICES]
    valid_intensities = [choice[0] for choice in Sport.INTENSITY_CHOICES]
    valid_difficulties = [choice[0] for choice in FitnessActivity.DIFFICULTY_CHOICES]

    if selected_environment in valid_environments:
        sports = sports.filter(environment=selected_environment)
    else:
        selected_environment = ""

    if selected_intensity in valid_intensities:
        sports = sports.filter(intensity=selected_intensity)
    else:
        selected_intensity = ""

    if selected_difficulty in valid_difficulties:
        sports = sports.filter(difficulty_level=selected_difficulty)
    else:
        selected_difficulty = ""

    if search_query:
        sports = sports.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(benefits__icontains=search_query)
            | Q(equipment_required__icontains=search_query)
        )

    base_template = (
        "base_app.html" if request.user.is_authenticated else "base_public.html"
    )
    profile = get_or_create_profile(request.user) if request.user.is_authenticated else None
    fitbuddy = (
        get_fitbuddy_state(request.user, profile, page_key="sports")
        if request.user.is_authenticated
        else None
    )

    all_sports_list = list(Sport.objects.all())
    if profile:
        recommended_sports = recommend_sports_for_profile(profile, limit=len(all_sports_list))
    else:
        recommended_sports = all_sports_list
    initial_pick = recommended_sports[0] if recommended_sports else None

    sports_picker_payload = [
        {
            "id": s.pk,
            "name": s.name,
            "description": s.description,
            "benefits": s.benefits,
            "environment": s.environment,
            "intensity": s.intensity,
            "difficulty_level": s.difficulty_level,
            "recommended_duration": s.recommended_duration,
            "equipment_required": s.equipment_required,
            "detail_url": reverse("fitness:sport_detail", args=[s.pk]),
            "log_url": f"{reverse('fitness:workouts')}?log_activity={s.name}&duration={s.recommended_duration}#log-workout-form",
        }
        for s in all_sports_list
    ]

    context = {
        "base_template": base_template,
        "profile": profile,
        "fitbuddy": fitbuddy,
        "sports": sports,
        "environments": valid_environments,
        "intensities": valid_intensities,
        "difficulties": valid_difficulties,
        "selected_environment": selected_environment,
        "selected_intensity": selected_intensity,
        "selected_difficulty": selected_difficulty,
        "search_query": search_query,
        "total_available": len(all_sports_list),
        "initial_pick": initial_pick,
        "sports_picker_json": json.dumps(sports_picker_payload),
    }
    return render(request, "fitness/sports.html", context)


def sport_detail(request, pk):
    sport = get_object_or_404(Sport, pk=pk)
    related_sports = Sport.objects.exclude(pk=sport.pk)[:3]
    base_template = (
        "base_app.html" if request.user.is_authenticated else "base_public.html"
    )
    profile = get_or_create_profile(request.user) if request.user.is_authenticated else None
    fitbuddy = (
        get_fitbuddy_state(request.user, profile, page_key="sports")
        if request.user.is_authenticated
        else None
    )

    return render(
        request,
        "fitness/sport_detail.html",
        {
            "base_template": base_template,
            "profile": profile,
            "fitbuddy": fitbuddy,
            "sport": sport,
            "related_sports": related_sports,
        },
    )


@never_cache
@login_required
def workout_tracker(request):
    profile = get_or_create_profile(request.user)
    today = timezone.localdate()

    if request.method == "POST":
        form = WorkoutForm(request.POST)
        if form.is_valid():
            workout = form.save(commit=False)
            workout.user = request.user
            workout.save()

            celebration = evaluate_user_gamification(
                request.user, just_logged_workout=workout, reference_date=today
            )
            if not celebration.get("has_celebration"):
                celebration = {
                    "has_celebration": True,
                    "newly_unlocked": [],
                    "newly_completed_goals": [],
                    "workout": {
                        "activity_name": workout.activity_name,
                        "duration": workout.duration,
                    },
                }
            queue_celebration(request, celebration)

            messages.success(
                request,
                f"Workout logged: {workout.activity_name} ({workout.duration} min on {workout.date.strftime('%b %d, %Y')}).",
            )
            return redirect("fitness:workouts")
        messages.error(
            request,
            "Could not save workout. Please review the highlighted fields below.",
        )
    else:
        initial = {}
        prefill_activity = (
            request.GET.get("log_activity", "").strip()
            or request.GET.get("activity", "").strip()
        )
        prefill_duration = request.GET.get("duration", "").strip()
        if prefill_activity:
            initial["activity_name"] = prefill_activity[:150]
        if prefill_duration.isdigit() and 1 <= int(prefill_duration) <= 720:
            initial["duration"] = int(prefill_duration)
        form = WorkoutForm(initial=initial)

    search_query = request.GET.get("q", "").strip()
    filter_activity = request.GET.get("filter_activity", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    user_workouts = Workout.objects.filter(user=request.user)
    workouts = user_workouts

    if search_query:
        workouts = workouts.filter(
            Q(activity_name__icontains=search_query)
            | Q(notes__icontains=search_query)
        )
    if filter_activity:
        workouts = workouts.filter(activity_name__iexact=filter_activity)
    if date_from:
        try:
            workouts = workouts.filter(date__gte=date.fromisoformat(date_from))
        except ValueError:
            date_from = ""
    if date_to:
        try:
            workouts = workouts.filter(date__lte=date.fromisoformat(date_to))
        except ValueError:
            date_to = ""

    stats = user_workouts.aggregate(
        total_minutes=Sum("duration"),
        avg_duration=Avg("duration"),
    )
    total_workouts = user_workouts.count()
    today_minutes = (
        user_workouts.filter(date=today).aggregate(total=Sum("duration"))["total"]
        or 0
    )

    logged_activity_names = sorted(
        set(user_workouts.values_list("activity_name", flat=True))
    )
    quick_activities = list(
        FitnessActivity.objects.values("name", "estimated_duration")[:6]
    )
    quick_sports = list(
        Sport.objects.values("name", "recommended_duration")[:4]
    )
    all_suggestions = sorted(
        set(
            list(FitnessActivity.objects.values_list("name", flat=True))
            + list(Sport.objects.values_list("name", flat=True))
        )
    )

    visual_map = build_activity_visual_map()
    workout_rows = []
    for w in workouts:
        vis = visual_map.get(w.activity_name.strip().lower())
        workout_rows.append(
            {
                "workout": w,
                "image_path": vis["image_path"] if vis else None,
                "icon_name": vis["icon_name"] if vis else "bi-activity",
            }
        )

    pending_celebration = pop_celebration(
        request, user=request.user, reference_date=today
    )
    fitbuddy = get_fitbuddy_state(
        request.user, profile, today_minutes=today_minutes, page_key="workouts"
    )

    context = {
        "profile": profile,
        "fitbuddy": fitbuddy,
        "form": form,
        "workouts": workouts,
        "workout_rows": workout_rows,
        "search_query": search_query,
        "filter_activity": filter_activity,
        "date_from": date_from,
        "date_to": date_to,
        "logged_activity_names": logged_activity_names,
        "total_workouts": total_workouts,
        "total_minutes": stats["total_minutes"] or 0,
        "avg_duration": round(stats["avg_duration"] or 0),
        "today_minutes": today_minutes,
        "quick_activities": quick_activities,
        "quick_sports": quick_sports,
        "all_suggestions": all_suggestions,
        "pending_celebration": pending_celebration,
        "pending_celebration_json": json.dumps(pending_celebration)
        if pending_celebration
        else "null",
    }
    return render(request, "fitness/workouts.html", context)


@login_required
def edit_workout(request, pk):
    profile = get_or_create_profile(request.user)
    workout = get_object_or_404(Workout, pk=pk, user=request.user)

    if request.method == "POST":
        form = WorkoutForm(request.POST, instance=workout)
        if form.is_valid():
            updated = form.save()
            celebration = evaluate_user_gamification(
                request.user, just_logged_workout=updated
            )
            queue_celebration(request, celebration)
            messages.success(
                request,
                f"Updated workout '{updated.activity_name}' ({updated.duration} min).",
            )
            return redirect("fitness:workouts")
        messages.error(request, "Please correct the highlighted fields.")
    else:
        form = WorkoutForm(instance=workout)

    all_suggestions = sorted(
        set(
            list(FitnessActivity.objects.values_list("name", flat=True))
            + list(Sport.objects.values_list("name", flat=True))
        )
    )

    fitbuddy = get_fitbuddy_state(request.user, profile, page_key="workouts")

    return render(
        request,
        "fitness/workout_edit.html",
        {
            "profile": profile,
            "fitbuddy": fitbuddy,
            "form": form,
            "workout": workout,
            "all_suggestions": all_suggestions,
        },
    )


@login_required
@require_POST
def delete_workout(request, pk):
    workout = get_object_or_404(Workout, pk=pk, user=request.user)
    activity_name = workout.activity_name
    workout.delete()
    messages.success(request, f"Removed '{activity_name}' from your workout log.")
    return redirect("fitness:workouts")


@never_cache
@login_required
def goals_view(request):
    profile = get_or_create_profile(request.user)
    today = timezone.localdate()

    if request.method == "POST":
        form = FitnessGoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            celebration = evaluate_user_gamification(
                request.user, reference_date=today
            )
            queue_celebration(request, celebration)
            messages.success(
                request,
                f"Goal '{goal.title}' ({goal.get_reward_container_display()}) has been added to your Fitness World!",
            )
            return redirect("fitness:goals")
        messages.error(
            request,
            "Could not create goal. Please check the form fields below.",
        )
    else:
        form = FitnessGoalForm()

    goals = FitnessGoal.objects.filter(user=request.user)
    goal_items = [
        {"goal": goal, **goal.get_progress_data(reference_date=today)}
        for goal in goals
    ]

    active_items = [item for item in goal_items if item["goal"].is_active]
    paused_items = [item for item in goal_items if not item["goal"].is_active]
    completed_items = [item for item in goal_items if item["is_completed"]]

    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    user_workouts = Workout.objects.filter(user=request.user)
    today_minutes = (
        user_workouts.filter(date=today).aggregate(total=Sum("duration"))["total"]
        or 0
    )
    weekly_qs = user_workouts.filter(date__gte=week_start, date__lte=week_end)
    weekly_minutes = weekly_qs.aggregate(total=Sum("duration"))["total"] or 0
    weekly_sessions = weekly_qs.count()

    pending_celebration = pop_celebration(
        request, user=request.user, reference_date=today
    )
    fitbuddy = get_fitbuddy_state(
        request.user,
        profile,
        goal_cards=active_items,
        today_minutes=today_minutes,
        page_key="goals",
    )

    context = {
        "profile": profile,
        "fitbuddy": fitbuddy,
        "form": form,
        "goal_items": goal_items,
        "active_items": active_items,
        "paused_items": paused_items,
        "completed_items": completed_items,
        "active_count": len(active_items),
        "completed_count": len(completed_items),
        "today_minutes": today_minutes,
        "weekly_minutes": weekly_minutes,
        "weekly_sessions": weekly_sessions,
        "today": today,
        "container_choices": FitnessGoal.CONTAINER_CHOICES,
        "theme_choices": FitnessGoal.THEME_CHOICES,
        "pending_celebration": pending_celebration,
        "pending_celebration_json": json.dumps(pending_celebration)
        if pending_celebration
        else "null",
    }
    return render(request, "fitness/goals.html", context)


@login_required
def edit_goal(request, pk):
    profile = get_or_create_profile(request.user)
    goal = get_object_or_404(FitnessGoal, pk=pk, user=request.user)

    if request.method == "POST":
        form = FitnessGoalForm(request.POST, instance=goal)
        if form.is_valid():
            updated = form.save()
            celebration = evaluate_user_gamification(request.user)
            queue_celebration(request, celebration)
            messages.success(request, f"Updated goal '{updated.title}'.")
            return redirect("fitness:goals")
        messages.error(request, "Please correct the highlighted goal fields.")
    else:
        form = FitnessGoalForm(instance=goal)

    fitbuddy = get_fitbuddy_state(request.user, profile, page_key="goals")

    return render(
        request,
        "fitness/goal_edit.html",
        {
            "profile": profile,
            "fitbuddy": fitbuddy,
            "form": form,
            "goal": goal,
            "container_choices": FitnessGoal.CONTAINER_CHOICES,
            "theme_choices": FitnessGoal.THEME_CHOICES,
        },
    )


@login_required
@require_POST
def toggle_goal(request, pk):
    goal = get_object_or_404(FitnessGoal, pk=pk, user=request.user)
    goal.is_active = not goal.is_active
    goal.save(update_fields=["is_active"])
    status_word = "resumed" if goal.is_active else "paused"
    messages.info(request, f"Goal '{goal.title}' has been {status_word}.")
    return redirect("fitness:goals")


@login_required
@require_POST
def delete_goal(request, pk):
    goal = get_object_or_404(FitnessGoal, pk=pk, user=request.user)
    title = goal.title
    goal.delete()
    messages.success(request, f"Deleted goal '{title}'.")
    return redirect("fitness:goals")


@never_cache
@login_required
def rewards_view(request):
    profile = get_or_create_profile(request.user)
    today = timezone.localdate()

    pending_celebration = pop_celebration(
        request, user=request.user, reference_date=today
    )
    achievements_summary = get_achievements_with_progress(
        request.user, reference_date=today
    )
    streak_info = compute_user_streaks(request.user, reference_date=today)

    user_goals = FitnessGoal.objects.filter(user=request.user)
    earned_goal_rewards = []
    for goal in user_goals:
        progress = goal.get_progress_data(reference_date=today)
        if progress["is_completed"] or goal.celebrated_at is not None:
            earned_goal_rewards.append({"goal": goal, **progress})

    fitbuddy = get_fitbuddy_state(
        request.user, profile, streak_info=streak_info, page_key="rewards"
    )

    return render(
        request,
        "fitness/rewards.html",
        {
            "profile": profile,
            "fitbuddy": fitbuddy,
            "achievements_summary": achievements_summary,
            "earned_goal_rewards": earned_goal_rewards,
            "streak_info": streak_info,
            "pending_celebration": pending_celebration,
            "pending_celebration_json": json.dumps(pending_celebration)
            if pending_celebration
            else "null",
        },
    )


@never_cache
@login_required
def goals_progress_api(request):
    """
    Authenticated JSON endpoint returning live database-calculated Reward Jar
    progress and activity/time breakdowns strictly scoped to request.user.
    """
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    user_workouts = Workout.objects.filter(user=request.user)
    today_minutes = (
        user_workouts.filter(date=today).aggregate(total=Sum("duration"))["total"]
        or 0
    )
    weekly_qs = user_workouts.filter(date__gte=week_start, date__lte=week_end)
    weekly_minutes = weekly_qs.aggregate(total=Sum("duration"))["total"] or 0
    weekly_sessions = weekly_qs.count()

    goals_payload = []
    for goal in FitnessGoal.objects.filter(user=request.user):
        pdata = goal.get_progress_data(reference_date=today)
        goals_payload.append(
            {
                "id": goal.pk,
                "title": goal.title,
                "goal_type": goal.goal_type,
                "goal_type_label": goal.get_goal_type_display(),
                "reward_container": goal.reward_container,
                "reward_container_label": goal.get_reward_container_display(),
                "is_active": goal.is_active,
                "status": pdata["status"],
                "completed_value": pdata["completed_value"],
                "target_value": pdata["target_value"],
                "remaining_value": pdata["remaining_value"],
                "unit_label": pdata["unit_label"],
                "progress_percent": pdata["progress_percent"],
                "raw_percent": pdata["raw_percent"],
                "is_completed": pdata["is_completed"],
                "period_label": pdata["period_label"],
                "workout_count": pdata["workout_count"],
                "total_minutes_in_period": pdata["total_minutes_in_period"],
                "activity_breakdown": pdata["activity_breakdown"],
            }
        )

    return JsonResponse(
        {
            "ok": True,
            "date": today.isoformat(),
            "today_minutes": today_minutes,
            "weekly_minutes": weekly_minutes,
            "weekly_sessions": weekly_sessions,
            "goals": goals_payload,
        }
    )


@never_cache
@login_required
def analytics_view(request):
    profile = get_or_create_profile(request.user)
    today = timezone.localdate()

    period = request.GET.get("period", "30d").strip()
    valid_periods = {"7d", "30d", "90d", "all"}
    if period not in valid_periods:
        period = "30d"

    all_user_workouts = Workout.objects.filter(user=request.user)
    if period == "7d":
        filtered_workouts = all_user_workouts.filter(date__gte=today - timedelta(days=6))
        period_label = "Last 7 Days"
    elif period == "30d":
        filtered_workouts = all_user_workouts.filter(date__gte=today - timedelta(days=29))
        period_label = "Last 30 Days"
    elif period == "90d":
        filtered_workouts = all_user_workouts.filter(date__gte=today - timedelta(days=89))
        period_label = "Last 90 Days"
    else:
        filtered_workouts = all_user_workouts
        period_label = "All Time"

    total_workouts = filtered_workouts.count()
    total_minutes = filtered_workouts.aggregate(total=Sum("duration"))["total"] or 0
    avg_duration = round(
        filtered_workouts.aggregate(avg=Avg("duration"))["avg"] or 0
    )

    top_activity_row = (
        filtered_workouts.values("activity_name")
        .annotate(session_count=Count("id"), total_min=Sum("duration"))
        .order_by("-session_count", "-total_min")
        .first()
    )
    most_frequent_activity = (
        top_activity_row["activity_name"] if top_activity_row else "No sessions yet"
    )
    most_frequent_count = (
        top_activity_row["session_count"] if top_activity_row else 0
    )

    # 1. Weekly Workout Duration & Frequency (last 8 weeks, Mon-Sun buckets)
    current_week_start = today - timedelta(days=today.weekday())
    num_weeks = 2 if period == "7d" else 8
    weekly_labels = []
    weekly_duration_values = []
    weekly_frequency_values = []

    earliest_week = current_week_start - timedelta(weeks=num_weeks - 1)
    recent_8w_workouts = all_user_workouts.filter(date__gte=earliest_week)
    week_buckets_min = defaultdict(int)
    week_buckets_cnt = defaultdict(int)
    for w in recent_8w_workouts:
        w_start = w.date - timedelta(days=w.date.weekday())
        week_buckets_min[w_start] += w.duration
        week_buckets_cnt[w_start] += 1

    for i in range(num_weeks):
        wk = earliest_week + timedelta(weeks=i)
        weekly_labels.append(wk.strftime("%b %d"))
        weekly_duration_values.append(week_buckets_min.get(wk, 0))
        weekly_frequency_values.append(week_buckets_cnt.get(wk, 0))

    # 2. Monthly Workout Duration (last 6 months)
    month_labels = []
    month_values = []
    month_buckets = defaultdict(int)
    for w in all_user_workouts:
        month_buckets[(w.date.year, w.date.month)] += w.duration

    y, m = today.year, today.month
    month_pairs = []
    for _ in range(6):
        month_pairs.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    month_pairs.reverse()
    for yr, mo in month_pairs:
        dt = date(yr, mo, 1)
        month_labels.append(dt.strftime("%b %Y"))
        month_values.append(month_buckets.get((yr, mo), 0))

    # 3. Activity Distribution (top 6 activities + Other)
    dist_rows = list(
        filtered_workouts.values("activity_name")
        .annotate(total_min=Sum("duration"), count=Count("id"))
        .order_by("-total_min")
    )
    dist_labels = []
    dist_values = []
    if len(dist_rows) > 6:
        for row in dist_rows[:5]:
            dist_labels.append(row["activity_name"])
            dist_values.append(row["total_min"])
        other_sum = sum(row["total_min"] for row in dist_rows[5:])
        dist_labels.append("Other")
        dist_values.append(other_sum)
    else:
        for row in dist_rows:
            dist_labels.append(row["activity_name"])
            dist_values.append(row["total_min"])

    # 4. Goal Completion Statistics
    user_goals = FitnessGoal.objects.filter(user=request.user)
    total_goals = user_goals.count()
    completed_goals = 0
    completed_goal_items = []
    for goal in user_goals:
        pdata = goal.get_progress_data(reference_date=today)
        if pdata["is_completed"]:
            completed_goals += 1
            completed_goal_items.append({"goal": goal, **pdata})
    goal_completion_rate = (
        round((completed_goals / total_goals) * 100) if total_goals > 0 else 0
    )

    streak_info = compute_user_streaks(request.user, reference_date=today)
    achievements_summary = get_achievements_with_progress(
        request.user, reference_date=today
    )
    journey_milestones = build_fitness_journey_milestones(request.user, profile)
    fitbuddy = get_fitbuddy_state(
        request.user, profile, streak_info=streak_info, page_key="analytics"
    )

    context = {
        "profile": profile,
        "fitbuddy": fitbuddy,
        "period": period,
        "period_label": period_label,
        "total_workouts": total_workouts,
        "total_minutes": total_minutes,
        "avg_duration": avg_duration,
        "most_frequent_activity": most_frequent_activity,
        "most_frequent_count": most_frequent_count,
        "total_goals": total_goals,
        "completed_goals": completed_goals,
        "completed_goal_items": completed_goal_items,
        "goal_completion_rate": goal_completion_rate,
        "streak_info": streak_info,
        "achievements_summary": achievements_summary,
        "journey_milestones": journey_milestones,
        "weekly_labels_json": json.dumps(weekly_labels),
        "weekly_duration_json": json.dumps(weekly_duration_values),
        "weekly_frequency_json": json.dumps(weekly_frequency_values),
        "month_labels_json": json.dumps(month_labels),
        "month_values_json": json.dumps(month_values),
        "dist_labels_json": json.dumps(dist_labels),
        "dist_values_json": json.dumps(dist_values),
        "has_workouts": total_workouts > 0,
    }
    return render(request, "fitness/analytics.html", context)


@login_required
def profile_view(request):
    profile = get_or_create_profile(request.user)

    if request.method == "POST":
        form = ProfileUpdateForm(
            request.POST, instance=profile, user=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(
                request, "Your profile and FitBuddy preferences have been updated."
            )
            return redirect("fitness:profile")
        messages.error(request, "Please correct the highlighted profile fields.")
    else:
        form = ProfileUpdateForm(instance=profile, user=request.user)

    total_workouts = Workout.objects.filter(user=request.user).count()
    total_minutes = (
        Workout.objects.filter(user=request.user).aggregate(
            total=Sum("duration")
        )["total"]
        or 0
    )
    total_goals = FitnessGoal.objects.filter(user=request.user).count()
    achievements_summary = get_achievements_with_progress(request.user)
    account_role = (
        "Administrator"
        if (request.user.is_staff or request.user.is_superuser)
        else "Regular User"
    )
    fitbuddy = get_fitbuddy_state(request.user, profile, page_key="profile")

    return render(
        request,
        "fitness/profile.html",
        {
            "profile": profile,
            "fitbuddy": fitbuddy,
            "form": form,
            "total_workouts": total_workouts,
            "total_minutes": total_minutes,
            "total_goals": total_goals,
            "achievements_summary": achievements_summary,
            "account_role": account_role,
        },
    )


@login_required
def settings_view(request):
    profile = get_or_create_profile(request.user)
    pref_form = ProfileSetupForm(instance=profile)
    pw_form = FitTrackPasswordChangeForm(request.user)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "update_preferences":
            pref_form = ProfileSetupForm(request.POST, instance=profile)
            if pref_form.is_valid():
                saved = pref_form.save(commit=False)
                saved.profile_completed = True
                saved.save()
                messages.success(
                    request, "Fitness & FitBuddy preferences updated successfully."
                )
                return redirect("fitness:settings")
            messages.error(
                request, "Could not update preferences. Please review the form."
            )
        elif action == "change_password":
            pw_form = FitTrackPasswordChangeForm(request.user, request.POST)
            if pw_form.is_valid():
                user = pw_form.save()
                update_session_auth_hash(request, user)
                messages.success(
                    request, "Your password has been changed securely."
                )
                return redirect("fitness:settings")
            messages.error(
                request, "Could not change password. Please fix the errors below."
            )

    account_role = (
        "Administrator"
        if (request.user.is_staff or request.user.is_superuser)
        else "Regular User"
    )
    fitbuddy = get_fitbuddy_state(request.user, profile, page_key="settings")

    return render(
        request,
        "fitness/settings.html",
        {
            "profile": profile,
            "fitbuddy": fitbuddy,
            "pref_form": pref_form,
            "pw_form": pw_form,
            "account_role": account_role,
        },
    )
