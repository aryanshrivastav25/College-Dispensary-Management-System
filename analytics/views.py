# campuscare/analytics/views.py — Step 10

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import TemplateView

from accounts.models import UserProfile
from appointments.services import get_active_token
from analytics.services import eta_calculator, medicine_history, triage_suggest
from core.decorators import RoleRequiredMixin


class TriageForm(forms.Form):
    """Capture symptom details for the local triage rule engine."""

    symptoms = forms.CharField(
        label='Describe your symptoms',
        widget=forms.Textarea(attrs={'rows': 5}),
    )


class TriageView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """Run the symptom triage rule engine for a student."""

    allowed_roles = (UserProfile.Role.STUDENT,)
    template_name = 'analytics/triage.html'

    def get(self, request, *args, **kwargs):
        return render(
            request,
            self.template_name,
            self.get_context_data(triage_form=TriageForm()),
        )

    def post(self, request, *args, **kwargs):
        triage_form = TriageForm(request.POST)
        suggestion = None

        if triage_form.is_valid():
            suggestion = triage_suggest(triage_form.cleaned_data['symptoms'])

        return render(
            request,
            self.template_name,
            self.get_context_data(
                triage_form=triage_form,
                suggestion=suggestion,
            ),
        )


class HistoryView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """Show the student's dispensed medicine history."""

    allowed_roles = (UserProfile.Role.STUDENT,)
    template_name = 'analytics/history.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'history_records': medicine_history(self.request.user.profile),
                **kwargs,
            }
        )
        return context


class EtaView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """Show the student's current queue ETA summary."""

    allowed_roles = (UserProfile.Role.STUDENT,)
    template_name = 'analytics/history.html'

    def get_context_data(self, **kwargs):
        token = get_active_token(self.request.user.profile)
        eta = eta_calculator(token) if token else None
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'eta': eta,
                'active_token': token,
                'history_records': medicine_history(self.request.user.profile)[:3],
                'show_eta_panel': True,
                **kwargs,
            }
        )
        return context

