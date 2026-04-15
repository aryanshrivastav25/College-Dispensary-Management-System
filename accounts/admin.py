from django.contrib import admin

from accounts.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for user profiles."""

    list_display = ('user', 'role', 'roll_number', 'phone', 'year_of_study')
    list_filter = ('role', 'year_of_study')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email', 'roll_number')
    ordering = ('user__username',)