# campuscare/analytics/urls.py — Step 10
from django.urls import path

from analytics.views import EtaView, HistoryView, TriageView

app_name = 'analytics'

urlpatterns = [
    path('triage/', TriageView.as_view(), name='triage'),
    path('history/', HistoryView.as_view(), name='history'),
    path('eta/', EtaView.as_view(), name='eta'),
]
