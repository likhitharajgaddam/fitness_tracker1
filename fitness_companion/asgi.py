"""
ASGI config for fitness_companion project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from fitness_companion.bootstrap import ensure_django_dependencies

ensure_django_dependencies()

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fitness_companion.settings')

application = get_asgi_application()
