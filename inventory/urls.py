
from django.urls import path

from inventory.views import LowStockAlertView, StockCreateView, StockListView, StockUpdateView

app_name = 'inventory'

urlpatterns = [
    path('', StockListView.as_view(), name='list'),
    path('add/', StockCreateView.as_view(), name='add'),
    path('edit/<int:pk>/', StockUpdateView.as_view(), name='edit'),
    path('alerts/', LowStockAlertView.as_view(), name='alerts'),
]
