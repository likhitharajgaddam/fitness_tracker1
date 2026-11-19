from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from fitness.gamification import (
    ACHIEVEMENT_DEFINITIONS,
    DAILY_CHALLENGE_DEFINITIONS,
    evaluate_user_gamification,
)
from fitness.models import (
    Achievement,
    DailyChallenge,
    FitnessActivity,
    FitnessGoal,
    Sport,
    UserProfile,
    Workout,
)

SAMPLE_ACTIVITIES = [
    {
        "name": "Walking",
        "description": "Low-impact aerobic movement that improves cardiovascular circulation, clears mental fatigue, and supports daily recovery without joint strain.",
        "benefits": "Boosts heart health, regulates blood sugar, relieves daily stress, and builds foundational aerobic stamina.",
        "instructions": "1. Wear supportive walking shoes and maintain upright posture with relaxed shoulders.\n2. Begin with 5 minutes at a comfortable warm-up pace.\n3. Increase to a brisk stride where you can speak in short sentences.\n4. Swing arms naturally at 90 degrees and finish with 3 minutes of slower cooldown walking.",
        "category": FitnessActivity.CATEGORY_CARDIO,
        "difficulty_level": FitnessActivity.DIFFICULTY_BEGINNER,
        "environment": "Outdoor / Home",
        "estimated_duration": 30,
        "calories_burn": 140,
        "target_muscles": "Calves, Quadriceps, Glutes, Core Stabilizers",
        "icon_name": "bi-person-walking",
        "image_path": "illustrations/activity_walking.svg",
        "is_recommended": True,
    },
    {
        "name": "Running",
        "description": "High-efficiency endurance training that builds aerobic capacity, strengthens lower-body muscles, and boosts metabolic conditioning.",
        "benefits": "Improves VO2 max, strengthens leg bones and tendons, elevates mood via endorphins, and burns high calories per minute.",
        "instructions": "1. Warm up with 5 minutes of brisk walking and dynamic leg swings.\n2. Run with a tall torso, soft midfoot landings, and steady breathing rhythm.\n3. Keep effort conversational for base runs or alternate 1-minute faster intervals.\n4. Cool down with 5 minutes of walking and light calf/hamstring stretches.",
        "category": FitnessActivity.CATEGORY_CARDIO,
        "difficulty_level": FitnessActivity.DIFFICULTY_INTERMEDIATE,
        "environment": "Outdoor / Gym",
        "estimated_duration": 35,
        "calories_burn": 360,
        "target_muscles": "Quadriceps, Hamstrings, Calves, Glutes, Heart & Lungs",
        "icon_name": "bi-lightning-charge",
        "image_path": "illustrations/activity_running.svg",
        "is_recommended": True,
    },
    {
        "name": "Yoga",
        "description": "Mindful sequence of postures and controlled breathing designed to increase joint mobility, core stability, and nervous system calm.",
        "benefits": "Increases spinal and hip flexibility, reduces lower-back tension, improves balance, and lowers resting stress levels.",
        "instructions": "1. Roll out a mat in a quiet space and begin with 3 minutes of deep nasal breathing.\n2. Flow through cat-cow, downward dog, and gentle sun salutations.\n3. Hold standing balance poses and seated hip openers for 5–8 breaths per side.\n4. Conclude with 3–5 minutes of supine relaxation.",
        "category": FitnessActivity.CATEGORY_FLEXIBILITY,
        "difficulty_level": FitnessActivity.DIFFICULTY_BEGINNER,
        "environment": "Home / Studio",
        "estimated_duration": 30,
        "calories_burn": 120,
        "target_muscles": "Spine, Hips, Shoulders, Deep Core, Ankles",
        "icon_name": "bi-sun",
        "image_path": "illustrations/activity_yoga.svg",
        "is_recommended": True,
    },
    {
        "name": "Cycling",
        "description": "Smooth, joint-friendly cardiovascular ride—indoors or outdoors—that develops leg power and sustained aerobic stamina.",
        "benefits": "Builds quadriceps and glute endurance, protects knees from impact, and strengthens cardiovascular efficiency.",
        "instructions": "1. Adjust saddle height so your knee retains a slight 15-degree bend at the bottom of the pedal stroke.\n2. Spin at an easy cadence (70–80 RPM) for the first 5 minutes.\n3. Alternate 5 minutes of steady resistance with 2 minutes of faster cadence.\n4. Taper effort during the final 5 minutes and hydrate well.",
        "category": FitnessActivity.CATEGORY_CARDIO,
        "difficulty_level": FitnessActivity.DIFFICULTY_INTERMEDIATE,
        "environment": "Outdoor / Gym",
        "estimated_duration": 45,
        "calories_burn": 390,
        "target_muscles": "Quadriceps, Glutes, Calves, Hip Flexors",
        "icon_name": "bi-bicycle",
        "image_path": "illustrations/activity_cycling.svg",
        "is_recommended": True,
    },
    {
        "name": "Push-ups",
        "description": "Classic upper-body bodyweight exercise targeting the chest, shoulders, triceps, and core bracing through scalable progressions.",
        "benefits": "Strengthens upper-body pushing muscles, stabilizes shoulder blades, and reinforces plank-like core tension.",
        "instructions": "1. Place hands slightly wider than shoulder-width apart and brace your core and glutes.\n2. Lower your chest in a controlled 2-second tempo with elbows angled roughly 45 degrees.\n3. Press back up smoothly without letting your hips sag.\n4. Perform 3–4 sets of 8–15 repetitions (use incline or knee variations if building up).",
        "category": FitnessActivity.CATEGORY_STRENGTH,
        "difficulty_level": FitnessActivity.DIFFICULTY_BEGINNER,
        "environment": "Home / Gym",
        "estimated_duration": 15,
        "calories_burn": 110,
        "target_muscles": "Pectorals (Chest), Triceps, Anterior Deltoids, Core",
        "icon_name": "bi-activity",
        "image_path": "illustrations/activity_pushups.svg",
        "is_recommended": False,
    },
    {
        "name": "Squats",
        "description": "Foundational lower-body strength movement engaging quadriceps, hamstrings, glutes, and hip stability for everyday athletic power.",
        "benefits": "Builds functional leg strength, enhances hip mobility, supports knee stability, and boosts athletic sprinting and jumping.",
        "instructions": "1. Stand with feet shoulder-width apart and toes turned slightly outward.\n2. Sit hips back and bend knees while keeping your chest lifted and heels planted.\n3. Lower until thighs are parallel to the floor (or comfortable depth).\n4. Drive through mid-foot to stand tall; complete 3–4 sets of 12–15 reps.",
        "category": FitnessActivity.CATEGORY_STRENGTH,
        "difficulty_level": FitnessActivity.DIFFICULTY_BEGINNER,
        "environment": "Home / Gym",
        "estimated_duration": 20,
        "calories_burn": 160,
        "target_muscles": "Quadriceps, Glutes, Hamstrings, Lower Back, Core",
        "icon_name": "bi-graph-up-arrow",
        "image_path": "illustrations/activity_squats.svg",
        "is_recommended": False,
    },
    {
        "name": "Stretching",
        "description": "Guided static and dynamic mobility routine to release tight hamstrings, hips, and shoulders after study or desk work.",
        "benefits": "Improves posture, reduces post-workout muscle stiffness, widens joint range of motion, and helps prevent strains.",
        "instructions": "1. Warm muscles briefly with 2 minutes of arm circles and marching in place.\n2. Stretch major muscle groups (calves, hamstrings, hip flexors, chest, upper back).\n3. Hold each static stretch for 25–30 seconds without bouncing.\n4. Breathe slowly to allow tension to release naturally.",
        "category": FitnessActivity.CATEGORY_FLEXIBILITY,
        "difficulty_level": FitnessActivity.DIFFICULTY_BEGINNER,
        "environment": "Home",
        "estimated_duration": 15,
        "calories_burn": 60,
        "target_muscles": "Hamstrings, Shoulders, Upper Back, Hip Flexors",
        "icon_name": "bi-wind",
        "image_path": "illustrations/activity_stretching.svg",
        "is_recommended": False,
    },
    {
        "name": "Strength Training",
        "description": "Structured resistance sets using dumbbells, bands, or bodyweight to build lean muscle mass, bone density, and posture.",
        "benefits": "Increases lean muscle mass, raises resting metabolic rate, strengthens connective tissue, and protects long-term joint health.",
        "instructions": "1. Start with 5 minutes of light cardio and shoulder/hip mobility.\n2. Choose 5 compound movements (e.g., goblet squats, rows, overhead press, lunges, planks).\n3. Complete 3 sets of 8–12 controlled reps with 60 seconds rest between sets.\n4. Focus on clean form before increasing resistance.",
        "category": FitnessActivity.CATEGORY_STRENGTH,
        "difficulty_level": FitnessActivity.DIFFICULTY_INTERMEDIATE,
        "environment": "Gym / Home",
        "estimated_duration": 45,
        "calories_burn": 290,
        "target_muscles": "Full Body (Upper Push/Pull, Legs, Core)",
        "icon_name": "bi-shield-check",
        "image_path": "illustrations/activity_strength.svg",
        "is_recommended": False,
    },
    {
        "name": "Jump Rope Intervals",
        "description": "Fast-paced coordination and footwork intervals alternating 45 seconds of brisk skipping with 15 seconds of active rest.",
        "benefits": "Rapidly elevates heart rate, sharpens ankle spring and footwork agility, and builds high aerobic conditioning in minimal space.",
        "instructions": "1. Size the rope so handles reach your armpits when standing on the center.\n2. Jump 1–2 inches off the ground using compact wrist rotations rather than wide arm swings.\n3. Perform 10–15 rounds of 40 seconds skipping / 20 seconds rest.\n4. Finish with calf stretches and slow nasal breathing.",
        "category": FitnessActivity.CATEGORY_CARDIO,
        "difficulty_level": FitnessActivity.DIFFICULTY_ADVANCED,
        "environment": "Home / Outdoor",
        "estimated_duration": 20,
        "calories_burn": 280,
        "target_muscles": "Calves, Ankles, Forearms, Shoulders, Cardiovascular System",
        "icon_name": "bi-fire",
        "image_path": "illustrations/activity_jumprope.svg",
        "is_recommended": False,
    },
    {
        "name": "Core Plank Circuit",
        "description": "Full-body isometric stability circuit combining forearm planks, side planks, and mountain climbers for resilient posture.",
        "benefits": "Builds deep abdominal and lower-back stability, improves athletic transfer of force, and prevents slouching fatigue.",
        "instructions": "1. Set up in a forearm plank with elbows directly under shoulders and body in a straight line.\n2. Rotate through 30s forearm plank, 25s left side plank, 25s right side plank, and 30s slow mountain climbers.\n3. Rest 45 seconds between rounds and repeat 3–4 times.",
        "category": FitnessActivity.CATEGORY_FULL_BODY,
        "difficulty_level": FitnessActivity.DIFFICULTY_INTERMEDIATE,
        "environment": "Home / Gym",
        "estimated_duration": 20,
        "calories_burn": 170,
        "target_muscles": "Transverse Abdominis, Obliques, Lower Back, Shoulders",
        "icon_name": "bi-layers",
        "image_path": "illustrations/activity_plank.svg",
        "is_recommended": False,
    },
]

SAMPLE_SPORTS = [
    {
        "name": "Badminton",
        "description": "High-tempo racket sport featuring rapid court lunges, overhead clears, and sharp net exchanges in singles or doubles.",
        "benefits": "Sharpens reflexes, improves lateral agility, strengthens calves and shoulders, and elevates heart rate quickly.",
        "recommended_duration": 45,
        "environment": Sport.ENV_INDOOR,
        "intensity": Sport.INTENSITY_MOD_HIGH,
        "difficulty_level": FitnessActivity.DIFFICULTY_BEGINNER,
        "equipment_required": "Badminton racket, feather or nylon shuttlecocks, non-marking court shoes.",
        "instructions": "1. Warm up shoulders, wrists, and ankles for 5 minutes.\n2. Practice basic high serves and forehand/backhand clears for 10 minutes.\n3. Play 2–3 games to 21 points focusing on returning to center court after every shot.",
        "icon_name": "bi-lightning-charge",
        "image_path": "illustrations/sport_badminton.svg",
    },
    {
        "name": "Football",
        "description": "Dynamic field team sport blending sustained aerobic running, sprint bursts, dribbling control, and tactical teamwork.",
        "benefits": "Builds cardiovascular endurance, lower-body power, spatial awareness, and cooperative team communication.",
        "recommended_duration": 60,
        "environment": Sport.ENV_OUTDOOR,
        "intensity": Sport.INTENSITY_HIGH,
        "difficulty_level": FitnessActivity.DIFFICULTY_INTERMEDIATE,
        "equipment_required": "Football (size 5), turf or grass cleats, shin guards, hydration bottle.",
        "instructions": "1. Warm up with light jogging, hip openers, and short passing drills.\n2. Run 15 minutes of small-sided possession or 5v5 scrimmages.\n3. Cool down with walking and quadriceps/groin stretches.",
        "icon_name": "bi-trophy",
        "image_path": "illustrations/sport_football.svg",
    },
    {
        "name": "Basketball",
        "description": "Fast-paced court sport built around continuous transitions, defensive slides, rebounding, and jump-shot mechanics.",
        "benefits": "Boosts vertical explosiveness, hand-eye coordination, anaerobic conditioning, and upper-lower body synchronization.",
        "recommended_duration": 50,
        "environment": Sport.ENV_BOTH,
        "intensity": Sport.INTENSITY_HIGH,
        "difficulty_level": FitnessActivity.DIFFICULTY_INTERMEDIATE,
        "equipment_required": "Basketball, supportive court shoes with ankle traction.",
        "instructions": "1. Start with form shooting around the key and ball-handling crossovers.\n2. Play 3v3 half-court or 5v5 full-court games in 10-minute blocks.\n3. Track sprints and finish with free-throw cooldown reps.",
        "icon_name": "bi-dribbble",
        "image_path": "illustrations/sport_basketball.svg",
    },
    {
        "name": "Cricket",
        "description": "Strategic bat-and-ball sport combining sprint intervals between wickets, bowling biomechanics, and sharp fielding focus.",
        "benefits": "Develops shoulder mobility, sprint acceleration, sustained mental concentration, and athletic teamwork.",
        "recommended_duration": 90,
        "environment": Sport.ENV_OUTDOOR,
        "intensity": Sport.INTENSITY_MODERATE,
        "difficulty_level": FitnessActivity.DIFFICULTY_BEGINNER,
        "equipment_required": "Cricket bat, ball, stumps, protective pads/gloves for hard-ball play.",
        "instructions": "1. Warm up rotator cuffs and run fielding catch drills for 15 minutes.\n2. Rotate through net batting, bowling overs, and quick-single running drills.\n3. Hydrate between overs during longer matches.",
        "icon_name": "bi-compass",
        "image_path": "illustrations/sport_cricket.svg",
    },
    {
        "name": "Swimming",
        "description": "Zero-impact full-body aquatic sport moving through freestyle, breaststroke, or backstroke lap intervals.",
        "benefits": "Strengthens back, core, and lungs simultaneously while protecting knees and ankles from impact stress.",
        "recommended_duration": 40,
        "environment": Sport.ENV_BOTH,
        "intensity": Sport.INTENSITY_MOD_HIGH,
        "difficulty_level": FitnessActivity.DIFFICULTY_BEGINNER,
        "equipment_required": "Swimwear, anti-fog goggles, swim cap, optional kickboard.",
        "instructions": "1. Swim 4 easy warm-up laps focusing on rhythmic exhale underwater.\n2. Complete 6–10 moderate interval laps with 20–30 seconds rest at the wall.\n3. Finish with 2 slow backstroke cooldown laps.",
        "icon_name": "bi-droplet",
        "image_path": "illustrations/sport_swimming.svg",
    },
    {
        "name": "Volleyball",
        "description": "Explosive net sport centered on quick footwork, overhead setting, timed vertical jumps, and seamless team rotation.",
        "benefits": "Enhances reaction speed, core stability, shoulder endurance, and explosive vertical jump power.",
        "recommended_duration": 50,
        "environment": Sport.ENV_BOTH,
        "intensity": Sport.INTENSITY_MODERATE,
        "difficulty_level": FitnessActivity.DIFFICULTY_BEGINNER,
        "equipment_required": "Volleyball, court shoes (or barefoot on sand), optional knee pads.",
        "instructions": "1. Warm up wrists, shoulders, and passing forearms with partner pepper drills.\n2. Practice serving accuracy and 3-touch bump-set-spike sequences.\n3. Play sets to 25 points with active court rotation.",
        "icon_name": "bi-award",
        "image_path": "illustrations/sport_volleyball.svg",
    },
    {
        "name": "Tennis",
        "description": "All-court racket duel pairing baseline rallies, directional sprints, and rotational core power on every stroke.",
        "benefits": "Improves rotational core strength, footwork precision, bone density, and sustained anaerobic recovery.",
        "recommended_duration": 60,
        "environment": Sport.ENV_OUTDOOR,
        "intensity": Sport.INTENSITY_HIGH,
        "difficulty_level": FitnessActivity.DIFFICULTY_INTERMEDIATE,
        "equipment_required": "Tennis racket, pressurized tennis balls, lateral-support court shoes.",
        "instructions": "1. Begin with 10 minutes of mini-tennis short rallies to dial in footwork.\n2. Move to full-court baseline forehands, backhands, and serve practice.\n3. Play tiebreaks or full sets while staying light on your toes between points.",
        "icon_name": "bi-bullseye",
        "image_path": "illustrations/sport_tennis.svg",
    },
    {
        "name": "Table Tennis",
        "description": "Precision indoor paddle sport requiring split-second anticipation, wrist control, and compact footwork shifts.",
        "benefits": "Accelerates visual reaction time, fine motor coordination, and active light-to-moderate calorie burn.",
        "recommended_duration": 40,
        "environment": Sport.ENV_INDOOR,
        "intensity": Sport.INTENSITY_MODERATE,
        "difficulty_level": FitnessActivity.DIFFICULTY_BEGINNER,
        "equipment_required": "Table tennis paddles, 40+ mm balls, standard table and net.",
        "instructions": "1. Warm up with steady forehand-to-forehand and backhand-to-backhand rallies.\n2. Practice short spin serves and third-ball attacks.\n3. Play best-of-5 games to 11 points.",
        "icon_name": "bi-arrow-repeat",
        "image_path": "illustrations/sport_table_tennis.svg",
    },
]


class Command(BaseCommand):
    help = "Populate fitness activities, sports ideas, achievements, daily challenges, and demo admin profile."

    def handle(self, *args, **options):
        created_activities = 0
        for item in SAMPLE_ACTIVITIES:
            _, created = FitnessActivity.objects.update_or_create(
                name=item["name"], defaults=item
            )
            if created:
                created_activities += 1

        created_sports = 0
        for item in SAMPLE_SPORTS:
            _, created = Sport.objects.update_or_create(
                name=item["name"], defaults=item
            )
            if created:
                created_sports += 1

        created_achievements = 0
        for item in ACHIEVEMENT_DEFINITIONS:
            _, created = Achievement.objects.update_or_create(
                slug=item["slug"], defaults=item
            )
            if created:
                created_achievements += 1

        created_challenges = 0
        for item in DAILY_CHALLENGE_DEFINITIONS:
            _, created = DailyChallenge.objects.update_or_create(
                title=item["title"], defaults=item
            )
            if created:
                created_challenges += 1

        User = get_user_model()
        admin_user = User.objects.filter(username="admin").first()
        if admin_user is None:
            admin_user = User.objects.create_superuser(
                "admin", "admin@example.com", "admin123"
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "Created default admin user (admin / admin123)."
                )
            )

        UserProfile.objects.get_or_create(
            user=admin_user,
            defaults={
                "fitness_level": "Intermediate",
                "primary_goal": "General Fitness",
                "preferred_environment": "Outdoor",
                "companion_choice": UserProfile.COMPANION_FEMALE,
                "tutorial_completed": True,
                "profile_completed": True,
            },
        )

        today = timezone.localdate()
        created_workouts = 0
        if Workout.objects.count() == 0:
            starter_workouts = [
                {
                    "user": admin_user,
                    "activity_name": "Morning Run",
                    "duration": 30,
                    "date": today,
                    "notes": "Steady 5K pace along the park loop.",
                },
                {
                    "user": admin_user,
                    "activity_name": "Stretching",
                    "duration": 15,
                    "date": today,
                    "notes": "Post-run hip flexor and hamstring cooldown.",
                },
                {
                    "user": admin_user,
                    "activity_name": "Badminton",
                    "duration": 45,
                    "date": today - timedelta(days=1),
                    "notes": "Three competitive singles sets at the campus court.",
                },
                {
                    "user": admin_user,
                    "activity_name": "Strength Training",
                    "duration": 40,
                    "date": today - timedelta(days=2),
                    "notes": "Upper-body push/pull circuit and core planks.",
                },
                {
                    "user": admin_user,
                    "activity_name": "Cycling",
                    "duration": 50,
                    "date": today - timedelta(days=3),
                    "notes": "Evening endurance ride with moderate hill climbs.",
                },
            ]
            for entry in starter_workouts:
                Workout.objects.create(**entry)
                created_workouts += 1

        created_goals = 0
        if FitnessGoal.objects.count() == 0:
            starter_goals = [
                {
                    "user": admin_user,
                    "title": "Daily Active Target",
                    "goal_type": FitnessGoal.GOAL_DAILY,
                    "target_minutes": 60,
                    "reward_container": FitnessGoal.CONTAINER_JUICE,
                    "theme_color": FitnessGoal.THEME_PEACH,
                    "start_date": today,
                    "is_active": True,
                },
                {
                    "user": admin_user,
                    "title": "Weekly Consistency Target",
                    "goal_type": FitnessGoal.GOAL_WEEKLY,
                    "target_minutes": 210,
                    "reward_container": FitnessGoal.CONTAINER_FLOWER,
                    "theme_color": FitnessGoal.THEME_MINT,
                    "start_date": today - timedelta(days=today.weekday()),
                    "is_active": True,
                },
                {
                    "user": admin_user,
                    "title": "Weekly Sessions Target",
                    "goal_type": FitnessGoal.GOAL_WEEKLY_FREQ,
                    "target_minutes": 5,
                    "reward_container": FitnessGoal.CONTAINER_TREASURE,
                    "theme_color": FitnessGoal.THEME_PURPLE,
                    "start_date": today - timedelta(days=today.weekday()),
                    "is_active": True,
                },
            ]
            for goal in starter_goals:
                FitnessGoal.objects.create(**goal)
                created_goals += 1

        # Ensure existing goals get distinct fun containers if still default
        existing_goals = list(FitnessGoal.objects.filter(user=admin_user).order_by("id"))
        containers = [
            FitnessGoal.CONTAINER_JUICE,
            FitnessGoal.CONTAINER_FLOWER,
            FitnessGoal.CONTAINER_TREASURE,
        ]
        themes = [
            FitnessGoal.THEME_PEACH,
            FitnessGoal.THEME_MINT,
            FitnessGoal.THEME_PURPLE,
        ]
        for idx, g in enumerate(existing_goals[:3]):
            if g.reward_container == FitnessGoal.CONTAINER_JUICE and idx > 0:
                g.reward_container = containers[idx]
                g.theme_color = themes[idx]
                g.save(update_fields=["reward_container", "theme_color"])

        # Sync admin's achievements quietly (mark notified so no popup flood on first load)
        evaluate_user_gamification(admin_user, reference_date=today)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {created_activities} new activities, "
                f"{created_sports} new sports, {created_achievements} achievements, "
                f"{created_challenges} daily challenges, {created_workouts} starter workouts, "
                f"{created_goals} starter goals."
            )
        )
