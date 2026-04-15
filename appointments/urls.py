from django.urls import path

from appointments.views import BookSlotView, MyTokenView, SlotListView, SlotUpdateView, queue_count_view

app_name = 'appointments'

urlpatterns = [
    path('', SlotListView.as_view(), name='slot_list'),
    path('slot/<int:slot_id>/book/', BookSlotView.as_view(), name='book'),
    path('slot/<int:slot_id>/edit/', SlotUpdateView.as_view(), name='edit_slot'),
    path('my-token/', MyTokenView.as_view(), name='my_token'),
    path('queue/<int:token_id>/', queue_count_view, name='queue_count'),
]
