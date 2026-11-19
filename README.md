# FitTrack – Your Personal Fitness Companion

**FitTrack** is a full-stack Django personal fitness management platform evolved from *Fitness & Sports Ideas*. It supports multi-user registration and authentication, personalized profile onboarding, a SaaS sidebar dashboard with Chart.js analytics, guided exercise and sports libraries, private workout CRUD tracking, daily/weekly fitness goals, and full Django Admin management.

## Key Features

1. **Public Landing Page (`/`)**
   - Hero section (`"Your Fitness Journey Starts Here."`), FitTrack overview, Why Choose FitTrack cards, Fitness Activities & Sports previews, benefits of physical activity, demo testimonials, and footer with contact information.
2. **Authentication & Security (`/signup/`, `/login/`, `/logout/`, `/password-reset/`)**
   - Registration with duplicate username/email checks, Django password strength validation, password visibility toggles, auto-login, and onboarding redirect.
   - Login with Username or Email, Remember Me session expiry, Forgot Password / Reset Password (Django built-in flow), and Change Password in Settings.
   - Strict `request.user` ownership isolation across all personal workouts, goals, profiles, dashboards, and analytics.
3. **Profile Setup & Management (`/profile/setup/`, `/profile/`, `/settings/`)**
   - `UserProfile` (`OneToOneField` to `User`) storing age, optional gender, fitness level (`Beginner` / `Intermediate` / `Advanced`), primary goal, and preferred workout environment (`Home` / `Gym` / `Outdoor` / `Sports`).
4. **Personalized SaaS Dashboard (`/dashboard/`)**
   - Responsive left sidebar navigation + top navigation bar + user profile dropdown.
   - Welcome banner, 5 user-specific statistics cards, interactive **Chart.js** weekly activity bar chart, live goal progress bars, preference-matched activity recommendations, latest 5 workouts, and featured sports.
5. **Fitness Activities & Sports Libraries (`/activities/`, `/sports/`)**
   - Guided activity cards and individual detail pages (`/activities/<id>/`, `/sports/<id>/`) with descriptions, health benefits, instructions, equipment lists, search, category/difficulty/venue filters, and one-click workout logging.
6. **Workout Tracker (`/workouts/`)**
   - Create, view, edit (`/workouts/<id>/edit/`), delete (`/workouts/<id>/delete/`), search, and filter by activity or date range.
7. **Fitness Goals (`/goals/`)**
   - Daily Duration (minutes), Weekly Duration (minutes), and Weekly Frequency (sessions) goals with start/end dates, pause/resume toggle, edit, delete, and automatic progress calculation.
8. **Progress & Analytics (`/analytics/`)**
   - Chart.js visualizations for Weekly Workout Duration, Monthly Workout Duration, Activity Distribution, and Workout Frequency, plus most frequent activity and goal completion rate.
9. **Django Admin Panel (`/admin/`)**
   - Administrator management for Users, UserProfiles, FitnessActivities, Sports, Workouts, and FitnessGoals.

## Commands to Run the Project

```bash
# 1. Apply migrations
python3 manage.py makemigrations
python3 manage.py migrate

# 2. Seed exercise/sports libraries and ensure admin profile exists
python3 manage.py seed_data

# 3. Run the automated test suite
python3 manage.py test -v 2

# 4. Start the Django server
python3 manage.py runserver
```

- **Public Landing Page**: `http://127.0.0.1:8000/`
- **Admin Panel**: `http://127.0.0.1:8000/admin/` (Demo admin: `admin` / `admin123`)
