
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import TemplateView

from accounts.models import UserProfile
from core.constants import LOW_STOCK_THRESHOLD
from core.decorators import RoleRequiredMixin
from inventory.forms import MedicineForm, StockForm
from inventory.models import Stock
from inventory.services import (
    create_inventory_entry,
    low_stock_alert,
    stock_catalog,
    update_inventory_entry,
)


class StockListView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """Display the full stock catalog and low-stock widget."""

    allowed_roles = (UserProfile.Role.PHARMACIST, UserProfile.Role.ADMIN)
    template_name = 'inventory/stock_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'stocks': stock_catalog(),
                'low_stock_stocks': low_stock_alert(),
                'alerts_only': False,
                'low_stock_threshold': LOW_STOCK_THRESHOLD,
                **kwargs,
            }
        )
        return context


class LowStockAlertView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """Display only the low-stock subset of the inventory."""

    allowed_roles = (UserProfile.Role.PHARMACIST, UserProfile.Role.ADMIN)
    template_name = 'inventory/stock_list.html'

    def get_context_data(self, **kwargs):
        low_stock_stocks = low_stock_alert()
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'stocks': low_stock_stocks,
                'low_stock_stocks': low_stock_stocks,
                'alerts_only': True,
                'low_stock_threshold': LOW_STOCK_THRESHOLD,
                **kwargs,
            }
        )
        return context


class StockCreateView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """Create a medicine plus stock entry in one flow."""

    allowed_roles = (UserProfile.Role.PHARMACIST, UserProfile.Role.ADMIN)
    template_name = 'inventory/stock_form.html'

    def get(self, request, *args, **kwargs):
        return render(
            request,
            self.template_name,
            self.get_context_data(
                medicine_form=MedicineForm(prefix='medicine'),
                stock_form=StockForm(prefix='stock'),
                page_heading='Add stock item',
            ),
        )

    def post(self, request, *args, **kwargs):
        medicine_form = MedicineForm(request.POST, prefix='medicine')
        stock_form = StockForm(request.POST, prefix='stock')

        if medicine_form.is_valid() and stock_form.is_valid():
            create_inventory_entry(
                medicine_data=medicine_form.cleaned_data,
                stock_data=stock_form.cleaned_data,
            )
            messages.success(request, 'Inventory item created successfully.')
            return redirect(reverse('inventory:list'))

        return render(
            request,
            self.template_name,
            self.get_context_data(
                medicine_form=medicine_form,
                stock_form=stock_form,
                page_heading='Add stock item',
            ),
        )


class StockUpdateView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """Update an existing medicine and stock entry."""

    allowed_roles = (UserProfile.Role.PHARMACIST, UserProfile.Role.ADMIN)
    template_name = 'inventory/stock_form.html'

    def get_stock(self) -> Stock:
        if not hasattr(self, '_stock'):
            self._stock = get_object_or_404(Stock.objects.select_related('medicine'), pk=self.kwargs['pk'])
        return self._stock

    def get(self, request, *args, **kwargs):
        stock = self.get_stock()
        return render(
            request,
            self.template_name,
            self.get_context_data(
                medicine_form=MedicineForm(instance=stock.medicine, prefix='medicine'),
                stock_form=StockForm(instance=stock, prefix='stock'),
                stock=stock,
                page_heading='Edit stock item',
            ),
        )

    def post(self, request, *args, **kwargs):
        stock = self.get_stock()
        medicine_form = MedicineForm(request.POST, instance=stock.medicine, prefix='medicine')
        stock_form = StockForm(request.POST, instance=stock, prefix='stock')

        if medicine_form.is_valid() and stock_form.is_valid():
            update_inventory_entry(
                stock=stock,
                medicine_data=medicine_form.cleaned_data,
                stock_data=stock_form.cleaned_data,
            )
            messages.success(request, 'Inventory item updated successfully.')
            return redirect(reverse('inventory:list'))

        return render(
            request,
            self.template_name,
            self.get_context_data(
                medicine_form=medicine_form,
                stock_form=stock_form,
                stock=stock,
                page_heading='Edit stock item',
            ),
        )
