"""
Django settings for fitness_companion project.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-fitness-companion-dev-key-change-in-production",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = ["*"]

APP_URL = os.environ.get("APP_URL", "").strip()

CSRF_TRUSTED_ORIGINS = [
    "https://*.run.app",
    "https://*.aistudio.google.com",
    "https://*.googleusercontent.com",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
if APP_URL and APP_URL not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(APP_URL)

# Respect X-Forwarded-Proto and X-Forwarded-Host from TLS-terminating proxies
# (e.g., Cloud Run frontend + local container nginx)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "fitness",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "fitness.middleware.IframeSafeCookieMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

# Safe defaults for local HTTP; IframeSafeCookieMiddleware dynamically upgrades
# cookies to SameSite=None; Secure; Partitioned (CHIPS) on HTTPS requests so
# authentication persists reliably inside cross-site preview iframes AND local HTTP.
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False
CSRF_FAILURE_VIEW = "fitness.views.csrf_failure_view"

# Allow embedding inside preview iframe when hosted via HTTPS proxy,
# while preserving standard clickjacking protection for local execution.
if not APP_URL.startswith("https://"):
    MIDDLEWARE.append("django.middleware.clickjacking.XFrameOptionsMiddleware")
    X_FRAME_OPTIONS = "SAMEORIGIN"

AUTHENTICATION_BACKENDS = [
    "fitness.backends.EmailOrUsernameModelBackend",
    "django.contrib.auth.backends.ModelBackend",
]

ROOT_URLCONF = "fitness_companion.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "fitness_companion.wsgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Django messages tags mapped to Bootstrap 5 alert classes
from django.contrib.messages import constants as message_constants

MESSAGE_TAGS = {
    message_constants.DEBUG: "secondary",
    message_constants.INFO: "info",
    message_constants.SUCCESS: "success",
    message_constants.WARNING: "warning",
    message_constants.ERROR: "danger",
}

# Authentication & Password Reset
LOGIN_URL = "fitness:login"
LOGIN_REDIRECT_URL = "fitness:dashboard"
LOGOUT_REDIRECT_URL = "fitness:landing"

EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = "FitTrack Support <noreply@fittrack.local>"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

