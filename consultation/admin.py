
from django.contrib import admin

from consultation.models import DoctorProfile, Prescription, PrescriptionMedicine


class PrescriptionMedicineInline(admin.TabularInline):
    """Inline medicine rows for prescriptions."""

    model = PrescriptionMedicine
    extra = 0


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    """Admin configuration for doctor availability profiles."""

    list_display = ('user', 'specialization', 'is_available')
    list_filter = ('is_available', 'specialization')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'specialization')
    ordering = ('user__username',)


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    """Admin configuration for prescriptions."""

    list_display = ('token', 'doctor', 'created_at')
    list_filter = ('doctor', 'created_at')
    search_fields = ('token__student__user__username', 'doctor__user__username')
    inlines = [PrescriptionMedicineInline]
