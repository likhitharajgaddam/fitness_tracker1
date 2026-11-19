from datetime import timedelta

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import (
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
)
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import FitnessGoal, UserProfile, Workout

User = get_user_model()


class SignUpForm(forms.Form):
    full_name = forms.CharField(
        max_length=150,
        label="Full Name",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g., Jordan Taylor",
                "autocomplete": "name",
            }
        ),
    )
    username = forms.CharField(
        max_length=150,
        label="Username",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Choose a unique username",
                "autocomplete": "username",
            }
        ),
    )
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "you@example.com",
                "autocomplete": "email",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Create a strong password",
                "autocomplete": "new-password",
                "data-password-input": "true",
            }
        ),
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Re-enter your password",
                "autocomplete": "new-password",
                "data-password-input": "true",
            }
        ),
    )

    def clean_full_name(self):
        name = (self.cleaned_data.get("full_name") or "").strip()
        if len(name) < 2:
            raise forms.ValidationError("Please enter your full name.")
        return name

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if len(username) < 3:
            raise forms.ValidationError(
                "Username must be at least 3 characters long."
            )
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                "This username is already taken. Please choose another."
            )
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email address already exists."
            )
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error(
                "confirm_password", "Passwords do not match. Please try again."
            )

        if password:
            temp_user = User(
                username=cleaned_data.get("username", ""),
                email=cleaned_data.get("email", ""),
                first_name=cleaned_data.get("full_name", ""),
            )
            try:
                validate_password(password, user=temp_user)
            except ValidationError as exc:
                self.add_error("password", exc.messages)

        return cleaned_data

    def save(self):
        full_name = self.cleaned_data["full_name"]
        parts = full_name.split(None, 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
            first_name=first_name,
            last_name=last_name,
        )
        UserProfile.objects.get_or_create(user=user)
        return user


class LoginForm(forms.Form):
    identifier = forms.CharField(
        max_length=254,
        label="Username or Email",
        error_messages={"required": "Please enter your username or email address."},
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your username or email",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        error_messages={"required": "Please enter your password."},
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your password",
                "autocomplete": "current-password",
                "data-password-input": "true",
            }
        ),
    )
    remember_me = forms.BooleanField(
        required=False,
        label="Remember me for 14 days",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean_identifier(self):
        identifier = (self.cleaned_data.get("identifier") or "").strip()
        if not identifier:
            raise forms.ValidationError("Please enter your username or email address.")
        return identifier

    def clean(self):
        cleaned_data = super().clean()
        identifier = (cleaned_data.get("identifier") or "").strip()
        password = cleaned_data.get("password")

        if identifier and password:
            user = authenticate(
                self.request, username=identifier, password=password
            )
            if user is None:
                # Check if credentials belong to an inactive account so we can
                # give an accurate status message without leaking non-matching accounts.
                inactive_candidates = list(
                    User.objects.filter(username__iexact=identifier, is_active=False)
                )
                if "@" in identifier:
                    inactive_candidates.extend(
                        User.objects.filter(email__iexact=identifier, is_active=False)
                    )
                for candidate in inactive_candidates:
                    if candidate.check_password(password):
                        raise forms.ValidationError(
                            "This account is currently inactive. Please contact an administrator."
                        )
                raise forms.ValidationError(
                    "Invalid username/email or password. Please check your credentials."
                )

            self.user_cache = user

        return cleaned_data

    def get_user(self):
        return self.user_cache


class ProfileSetupForm(forms.ModelForm):
    companion_choice = forms.ChoiceField(
        choices=UserProfile.COMPANION_CHOICES,
        required=False,
        initial=UserProfile.COMPANION_FEMALE,
        label="Choose Your FITBUDDY Companion",
        widget=forms.RadioSelect(attrs={"class": "companion-radio-input"}),
    )

    class Meta:
        model = UserProfile
        fields = [
            "age",
            "gender",
            "fitness_level",
            "primary_goal",
            "preferred_environment",
            "companion_choice",
        ]
        widgets = {
            "age": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., 24",
                    "min": 10,
                    "max": 110,
                }
            ),
            "gender": forms.Select(attrs={"class": "form-select"}),
            "fitness_level": forms.Select(attrs={"class": "form-select"}),
            "primary_goal": forms.Select(attrs={"class": "form-select"}),
            "preferred_environment": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "age": "Age",
            "gender": "Gender (Optional)",
            "fitness_level": "Fitness Level",
            "primary_goal": "Primary Fitness Goal",
            "preferred_environment": "Preferred Workout Environment",
        }

    def clean_companion_choice(self):
        return self.cleaned_data.get("companion_choice") or UserProfile.COMPANION_FEMALE

    def clean_age(self):
        age = self.cleaned_data.get("age")
        if age is not None and (age < 10 or age > 110):
            raise forms.ValidationError("Please enter a valid age between 10 and 110.")
        return age


class ProfileUpdateForm(ProfileSetupForm):
    full_name = forms.CharField(
        max_length=150,
        label="Full Name",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )

    class Meta(ProfileSetupForm.Meta):
        fields = [
            "full_name",
            "email",
            "age",
            "gender",
            "fitness_level",
            "primary_goal",
            "preferred_environment",
            "companion_choice",
        ]

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields["full_name"].initial = (
                self.user.get_full_name() or ""
            ).strip()
            self.fields["email"].initial = self.user.email

    def clean_full_name(self):
        name = (self.cleaned_data.get("full_name") or "").strip()
        if len(name) < 2:
            raise forms.ValidationError("Full name must be at least 2 characters.")
        return name

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.user:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError(
                "Another account is already using this email address."
            )
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            full_name = self.cleaned_data["full_name"]
            parts = full_name.split(None, 1)
            self.user.first_name = parts[0]
            self.user.last_name = parts[1] if len(parts) > 1 else ""
            self.user.email = self.cleaned_data["email"]
            if commit:
                self.user.save(update_fields=["first_name", "last_name", "email"])
        profile.profile_completed = True
        if commit:
            profile.save()
        return profile


class FitTrackPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update(
                {"class": "form-control", "data-password-input": "true"}
            )


class FitTrackPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Enter the email linked to your account",
            }
        )


class FitTrackSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update(
                {"class": "form-control", "data-password-input": "true"}
            )


class WorkoutForm(forms.ModelForm):
    class Meta:
        model = Workout
        fields = ["activity_name", "duration", "date", "notes"]
        widgets = {
            "activity_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Morning Run, Badminton, Yoga",
                    "list": "activity-suggestions-list",
                    "autocomplete": "off",
                }
            ),
            "duration": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Minutes (e.g., 30)",
                    "min": 1,
                    "max": 720,
                }
            ),
            "date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Optional notes on intensity, distance, sets, or how you felt...",
                }
            ),
        }
        labels = {
            "activity_name": "Activity or Sport",
            "duration": "Duration (minutes)",
            "date": "Workout Date",
            "notes": "Session Notes (Optional)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not self.instance.pk and not self.initial.get("date"):
            self.initial["date"] = timezone.localdate()

    def clean_activity_name(self):
        name = (self.cleaned_data.get("activity_name") or "").strip()
        if len(name) < 2:
            raise forms.ValidationError(
                "Please enter an activity name with at least 2 characters."
            )
        return name

    def clean_duration(self):
        duration = self.cleaned_data.get("duration")
        if duration is None or duration < 1:
            raise forms.ValidationError("Workout duration must be at least 1 minute.")
        if duration > 720:
            raise forms.ValidationError(
                "Workout duration cannot exceed 720 minutes (12 hours) per entry."
            )
        return duration

    def clean_date(self):
        workout_date = self.cleaned_data.get("date")
        if workout_date and workout_date > timezone.localdate() + timedelta(days=1):
            raise forms.ValidationError(
                "Please select today or a past date for completed workouts."
            )
        return workout_date


class FitnessGoalForm(forms.ModelForm):
    reward_container = forms.ChoiceField(
        choices=FitnessGoal.CONTAINER_CHOICES,
        required=False,
        initial=FitnessGoal.CONTAINER_JUICE,
        label="Reward Jar Container",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    theme_color = forms.ChoiceField(
        choices=FitnessGoal.THEME_CHOICES,
        required=False,
        initial=FitnessGoal.THEME_PURPLE,
        label="Goal Accent Theme",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = FitnessGoal
        fields = [
            "title",
            "goal_type",
            "target_minutes",
            "reward_container",
            "theme_color",
            "start_date",
            "end_date",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Daily Cardio Target or 4 Sessions / Week",
                }
            ),
            "goal_type": forms.Select(attrs={"class": "form-select"}),
            "target_minutes": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Minutes or sessions (e.g., 45 or 4)",
                    "min": 1,
                    "max": 3000,
                }
            ),
            "start_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "end_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
        }
        labels = {
            "title": "Goal Title",
            "goal_type": "Goal Type",
            "target_minutes": "Target Value (Minutes or Sessions)",
            "start_date": "Start Date (Optional)",
            "end_date": "Target / End Date (Optional)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not self.instance.pk and not self.initial.get("start_date"):
            self.initial["start_date"] = timezone.localdate()

    def clean_reward_container(self):
        return self.cleaned_data.get("reward_container") or FitnessGoal.CONTAINER_JUICE

    def clean_theme_color(self):
        return self.cleaned_data.get("theme_color") or FitnessGoal.THEME_PURPLE

    def clean_title(self):
        title = (self.cleaned_data.get("title") or "").strip()
        if len(title) < 3:
            raise forms.ValidationError(
                "Goal title must be at least 3 characters long."
            )
        return title

    def clean(self):
        cleaned_data = super().clean()
        goal_type = cleaned_data.get("goal_type")
        target_value = cleaned_data.get("target_minutes")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:
            self.add_error(
                "end_date", "End date cannot be earlier than start date."
            )

        if target_value is not None:
            if goal_type == FitnessGoal.GOAL_WEEKLY_FREQ:
                if target_value < 1 or target_value > 21:
                    self.add_error(
                        "target_minutes",
                        "Weekly frequency targets must be between 1 and 21 workouts.",
                    )
            else:
                if target_value < 5:
                    self.add_error(
                        "target_minutes",
                        "Duration target must be at least 5 minutes.",
                    )
                elif goal_type == FitnessGoal.GOAL_DAILY and target_value > 720:
                    self.add_error(
                        "target_minutes",
                        "Daily targets cannot exceed 720 minutes (12 hours).",
                    )
        return cleaned_data
