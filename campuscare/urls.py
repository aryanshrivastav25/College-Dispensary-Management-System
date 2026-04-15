"""Root URL configuration for CampusCare."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='accounts:dashboard', permanent=False)),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('appointments/', include('appointments.urls', namespace='appointments')),
    path('analytics/', include('analytics.urls', namespace='analytics')),
    path('calendar/', include('calendar_app.urls', namespace='calendar')),
    path('consultation/', include('consultation.urls', namespace='consultation')),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('pharmacy/', include('pharmacy.urls', namespace='pharmacy')),
    path('admin/', admin.site.urls),
]
