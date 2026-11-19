import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def assign_existing_records_and_profiles(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Workout = apps.get_model("fitness", "Workout")
    FitnessGoal = apps.get_model("fitness", "FitnessGoal")
    UserProfile = apps.get_model("fitness", "UserProfile")

    first_user = User.objects.order_by("id").first()
    if first_user is None and (
        Workout.objects.exists() or FitnessGoal.objects.exists()
    ):
        first_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="!",
            is_staff=True,
            is_superuser=True,
        )

    if first_user is not None:
        Workout.objects.filter(user__isnull=True).update(user=first_user)
        FitnessGoal.objects.filter(user__isnull=True).update(user=first_user)

    for user in User.objects.all():
        UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "fitness_level": "Intermediate",
                "primary_goal": "General Fitness",
                "preferred_environment": "Outdoor",
                "profile_completed": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("fitness", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "age",
                    models.PositiveIntegerField(
                        blank=True,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(10),
                            django.core.validators.MaxValueValidator(110),
                        ],
                    ),
                ),
                (
                    "gender",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("", "Prefer not to say"),
                            ("Female", "Female"),
                            ("Male", "Male"),
                            ("Non-binary", "Non-binary"),
                            ("Other", "Other"),
                        ],
                        max_length=25,
                    ),
                ),
                (
                    "fitness_level",
                    models.CharField(
                        choices=[
                            ("Beginner", "Beginner"),
                            ("Intermediate", "Intermediate"),
                            ("Advanced", "Advanced"),
                        ],
                        default="Beginner",
                        max_length=20,
                    ),
                ),
                (
                    "primary_goal",
                    models.CharField(
                        choices=[
                            ("Weight Management", "Weight Management"),
                            ("Muscle Building", "Muscle Building"),
                            ("Improve Stamina", "Improve Stamina"),
                            ("General Fitness", "General Fitness"),
                            ("Flexibility", "Flexibility"),
                        ],
                        default="General Fitness",
                        max_length=40,
                    ),
                ),
                (
                    "preferred_environment",
                    models.CharField(
                        choices=[
                            ("Home", "Home"),
                            ("Gym", "Gym"),
                            ("Outdoor", "Outdoor"),
                            ("Sports", "Sports"),
                        ],
                        default="Outdoor",
                        max_length=20,
                    ),
                ),
                ("profile_completed", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "User Profile",
                "verbose_name_plural": "User Profiles",
            },
        ),
        migrations.AddField(
            model_name="fitnessactivity",
            name="benefits",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Key health and performance benefits",
            ),
        ),
        migrations.AddField(
            model_name="fitnessactivity",
            name="environment",
            field=models.CharField(
                default="Home / Outdoor",
                help_text="Typical workout setting (Home, Gym, Outdoor)",
                max_length=40,
            ),
        ),
        migrations.AddField(
            model_name="fitnessactivity",
            name="image_path",
            field=models.CharField(
                blank=True,
                default="images/activity_cardio_running.jpg",
                help_text="Static image path relative to static/",
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name="fitnessactivity",
            name="instructions",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Step-by-step instructions for performing the exercise safely",
            ),
        ),
        migrations.AddField(
            model_name="sport",
            name="difficulty_level",
            field=models.CharField(
                choices=[
                    ("Beginner", "Beginner"),
                    ("Intermediate", "Intermediate"),
                    ("Advanced", "Advanced"),
                ],
                default="Beginner",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="sport",
            name="equipment_required",
            field=models.TextField(
                blank=True, default="", help_text="Recommended gear and equipment"
            ),
        ),
        migrations.AddField(
            model_name="sport",
            name="image_path",
            field=models.CharField(
                blank=True,
                default="images/sport_court_action.jpg",
                help_text="Static image path relative to static/",
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name="sport",
            name="instructions",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Getting-started guide and session structure",
            ),
        ),
        migrations.AddField(
            model_name="fitnessgoal",
            name="end_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="fitnessgoal",
            name="start_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="fitnessgoal",
            name="goal_type",
            field=models.CharField(
                choices=[
                    ("Daily", "Daily Duration (Minutes)"),
                    ("Weekly", "Weekly Duration (Minutes)"),
                    ("Weekly Frequency", "Weekly Frequency (Workouts)"),
                ],
                default="Daily",
                max_length=25,
            ),
        ),
        migrations.AlterField(
            model_name="fitnessgoal",
            name="target_minutes",
            field=models.PositiveIntegerField(
                help_text="Target minutes (for duration goals) or sessions (for frequency goals)",
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(3000),
                ],
            ),
        ),
        migrations.AddField(
            model_name="fitnessgoal",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="fitness_goals",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="workout",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="workouts",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(
            assign_existing_records_and_profiles, migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name="fitnessgoal",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="fitness_goals",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="workout",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="workouts",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
