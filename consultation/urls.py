
from django.urls import path

from consultation.views import (
    DoctorListView,
    PrescriptionCreateView,
    PrescriptionPrintView,
    toggle_availability_view,
)

app_name = 'consultation'

urlpatterns = [
    path('', DoctorListView.as_view(), name='doctor_list'),
    path('toggle-availability/', toggle_availability_view, name='toggle_availability'),
    path('prescribe/<int:token_id>/', PrescriptionCreateView.as_view(), name='prescribe'),
    path('print/<int:pk>/', PrescriptionPrintView.as_view(), name='print'),
]
