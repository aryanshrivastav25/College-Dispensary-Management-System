from calendar import Calendar, month_name, monthrange
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.generic import FormView, TemplateView

from accounts.models import UserProfile
from calendar_app.forms import DispensaryScheduleForm
from calendar_app.models import DispensarySchedule
from core.constants import (
    DEFAULT_DISPENSARY_CLOSE_TIME,
    DEFAULT_DISPENSARY_OPEN_TIME,
    DISPENSARY_DETAIL_DEFAULT,
)
from core.decorators import RoleRequiredMixin


def build_default_schedule_payload() -> dict[str, object]:
    """Return the default schedule shown for days without a custom entry."""
    return {
        'is_open': True,
        'open_time': DEFAULT_DISPENSARY_OPEN_TIME,
        'close_time': DEFAULT_DISPENSARY_CLOSE_TIME,
        'note': DISPENSARY_DETAIL_DEFAULT,
    }


class CalendarMonthView(LoginRequiredMixin, TemplateView):
    """Render the dispensary schedule month grid."""

    template_name = 'calendar_app/calendar_view.html'

    def get_reference_date(self) -> date:
        today = timezone.localdate()
        year = self.request.GET.get('year')
        month = self.request.GET.get('month')

        if not year or not month:
            return today.replace(day=1)

        try:
            return date(int(year), int(month), 1)
        except ValueError:
            return today.replace(day=1)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reference_date = self.get_reference_date()
        last_day = monthrange(reference_date.year, reference_date.month)[1]
        month_end = date(reference_date.year, reference_date.month, last_day)

        schedule_map = {
            schedule.date: schedule
            for schedule in DispensarySchedule.objects.filter(date__range=(reference_date, month_end))
        }

        weeks = []
        calendar_weeks = Calendar(firstweekday=0).monthdatescalendar(reference_date.year, reference_date.month)

        for week in calendar_weeks:
            week_days = []
            for day in week:
                schedule = schedule_map.get(day)
                has_custom_schedule = schedule is not None
                week_days.append(
                    {
                        'date': day,
                        'day_number': day.day,
                        'in_current_month': day.month == reference_date.month,
                        'is_today': day == timezone.localdate(),
                        'schedule': schedule or build_default_schedule_payload(),
                        'has_custom_schedule': has_custom_schedule,
                    }
                )
            weeks.append(week_days)

        previous_month = (reference_date.replace(day=1) - timedelta(days=1)).replace(day=1)
        if reference_date.month == 12:
            next_month = date(reference_date.year + 1, 1, 1)
        else:
            next_month = date(reference_date.year, reference_date.month + 1, 1)

        context.update(
            {
                'reference_date': reference_date,
                'calendar_title': f'{month_name[reference_date.month]} {reference_date.year}',
                'weeks': weeks,
                'weekday_labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                'previous_month': previous_month,
                'next_month': next_month,
            }
        )
        return context


class ScheduleManageView(LoginRequiredMixin, RoleRequiredMixin, FormView):
    """Create or update a daily schedule entry."""

    allowed_roles = (UserProfile.Role.ADMIN,)
    form_class = DispensaryScheduleForm
    template_name = 'calendar_app/schedule_form.html'
    success_url = reverse_lazy('calendar:manage')

    def get_selected_date(self) -> date:
        today = timezone.localdate()
        raw_date = self.request.GET.get('date') or self.request.POST.get('date')
        selected_date = parse_date(raw_date) if raw_date else None
        return selected_date or today

    def get_existing_schedule(self):
        return DispensarySchedule.objects.filter(date=self.get_selected_date()).first()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        schedule = self.get_existing_schedule()
        kwargs['instance'] = schedule
        initial = kwargs.setdefault('initial', {})
        if schedule is None:
            initial['date'] = self.get_selected_date()
            initial['is_open'] = True
            initial['open_time'] = DEFAULT_DISPENSARY_OPEN_TIME
            initial['close_time'] = DEFAULT_DISPENSARY_CLOSE_TIME
        return kwargs

    def form_valid(self, form):
        schedule = form.save()
        messages.success(self.request, f'Schedule saved for {schedule.date:%d %b %Y}.')
        return redirect(f"{reverse('calendar:manage')}?date={schedule.date.isoformat()}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_date = self.get_selected_date()
        context.update(
            {
                'selected_date': selected_date,
                'existing_schedule': self.get_existing_schedule(),
                'recent_schedules': DispensarySchedule.objects.order_by('-date')[:10],
                'default_schedule_preview': build_default_schedule_payload(),
            }
        )
        return context
