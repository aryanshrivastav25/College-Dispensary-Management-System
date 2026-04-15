
from django.urls import path

from accounts.views import (
    CampusCareLoginView,
    CampusCareLogoutView,
    DashboardRedirectView,
    RegistrationView,
    StudentRegistrationView
)

app_name = 'accounts'

urlpatterns = [
    path('register/', RegistrationView.as_view(), name='register'),
    path('register_student/', StudentRegistrationView.as_view(), name='register_student'),
    path('login/', CampusCareLoginView.as_view(), name='login'),
    path('logout/', CampusCareLogoutView.as_view(), name='logout'),
    path('dashboard/', DashboardRedirectView.as_view(), name='dashboard'),
]