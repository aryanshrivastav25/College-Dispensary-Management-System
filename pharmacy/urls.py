
from django.urls import path

from pharmacy.views import DispensePrescriptionView, DispenseQueueView, ReceiptDetailView

app_name = 'pharmacy'

urlpatterns = [
    path('', DispenseQueueView.as_view(), name='queue'),
    path('dispense/<int:pk>/', DispensePrescriptionView.as_view(), name='dispense'),
    path('receipt/<int:pk>/', ReceiptDetailView.as_view(), name='receipt'),
]
