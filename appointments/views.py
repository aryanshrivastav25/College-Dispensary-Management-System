from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import FormView, ListView, TemplateView, UpdateView

from accounts.models import UserProfile
from appointments.forms import SlotBookingForm, SlotCreateForm
from appointments.models import Slot, Token
from appointments.services import (
    BookingError,
    expire_stale_tokens,
    generate_token,
    get_active_token,
    get_queue_snapshot,
    is_slot_bookable,
    slot_booking_note,
)
from core.constants import QUEUE_POLL_INTERVAL_MS
from core.decorators import RoleRequiredMixin, role_required


class SlotListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """Show upcoming slots available for student booking."""

    allowed_roles = (UserProfile.Role.STUDENT, UserProfile.Role.ADMIN)
    model = Slot
    template_name = 'appointments/slot_list.html'
    context_object_name = 'slots'

    def get_queryset(self):
        expire_stale_tokens()
        return Slot.objects.filter(date__gte=timezone.localdate()).order_by('date', 'start_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        is_admin = profile.role == UserProfile.Role.ADMIN
        is_student = profile.role == UserProfile.Role.STUDENT
        context['active_token'] = get_active_token(profile) if profile.role == UserProfile.Role.STUDENT else None
        context['slot_cards'] = [
            {
                'slot': slot,
                'bookable': is_slot_bookable(slot),
                'booking_note': (
                    'Open for student booking.' if is_admin and is_slot_bookable(slot) else slot_booking_note(slot)
                ),
            }
            for slot in context['slots']
        ]
        context['is_admin'] = is_admin
        context['is_student'] = is_student
        context['slot_form'] = kwargs.get('slot_form', SlotCreateForm(prefix='slot')) if is_admin else None
        return context

    def post(self, request, *args, **kwargs):
        if request.user.profile.role != UserProfile.Role.ADMIN:
            raise PermissionDenied

        self.object_list = self.get_queryset()
        slot_form = SlotCreateForm(request.POST, prefix='slot')

        if slot_form.is_valid():
            slot = slot_form.save()
            messages.success(request, f'Slot "{slot.title}" was created successfully.')
            return redirect(reverse('appointments:slot_list'))

        return self.render_to_response(self.get_context_data(slot_form=slot_form))


class BookSlotView(LoginRequiredMixin, RoleRequiredMixin, FormView):
    """Confirm and create a token for a selected slot."""

    allowed_roles = (UserProfile.Role.STUDENT,)
    form_class = SlotBookingForm
    template_name = 'appointments/book_slot.html'

    def dispatch(self, request, *args, **kwargs):
        expire_stale_tokens()
        self.slot = get_object_or_404(Slot, pk=kwargs['slot_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self) -> str:
        return reverse('appointments:my_token')

    def form_valid(self, form):
        try:
            token = generate_token(self.request.user.profile, self.slot)
        except BookingError as exc:
            form.add_error(None, exc.messages[0] if exc.messages else str(exc))
            return self.form_invalid(form)

        messages.success(self.request, f'Your token {token.token_code} has been generated.')
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slot'] = self.slot
        context['booking_note'] = slot_booking_note(self.slot)
        return context


class SlotUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    """Allow admins to update an existing slot from the appointments area."""

    allowed_roles = (UserProfile.Role.ADMIN,)
    model = Slot
    form_class = SlotCreateForm
    template_name = 'appointments/slot_form.html'
    pk_url_kwarg = 'slot_id'

    def get_success_url(self) -> str:
        return reverse('appointments:slot_list')

    def form_valid(self, form):
        slot = form.save()
        messages.success(self.request, f'Slot "{slot.title}" was updated successfully.')
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'slot': self.object,
                'page_heading': 'Edit slot',
                'page_summary': 'Update appointment timing, capacity, or notes for this slot.',
            }
        )
        return context


class MyTokenView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """Render the current token and its live queue state."""

    allowed_roles = (UserProfile.Role.STUDENT, UserProfile.Role.ADMIN)
    template_name = 'appointments/my_token.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token = get_active_token(self.request.user.profile)
        context['token'] = token
        context['queue_poll_interval_ms'] = QUEUE_POLL_INTERVAL_MS
        context['queue_snapshot'] = get_queue_snapshot(token) if token else None
        return context


@login_required
@role_required(UserProfile.Role.STUDENT, UserProfile.Role.ADMIN)
def queue_count_view(request, token_id):
    """Return live queue data for the student's token."""
    expire_stale_tokens()
    token = get_object_or_404(Token, pk=token_id)

    if request.user.profile.role != UserProfile.Role.ADMIN and token.student_id != request.user.profile.pk:
        return JsonResponse({'detail': 'Forbidden'}, status=403)

    snapshot = get_queue_snapshot(token)
    return JsonResponse(snapshot)
