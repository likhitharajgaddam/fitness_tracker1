"""
URL configuration for fitness_companion project.
"""

from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "FitTrack Administration"
admin.site.site_title = "FitTrack Admin"
admin.site.index_title = "Manage Users, Profiles, Activities, Sports, Workouts & Goals"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("fitness.urls")),
]
