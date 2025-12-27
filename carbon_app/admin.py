# carbon_app/admin.py
from django.contrib import admin
from .models import ActivityCategory, EmissionFactor, UserActivity

@admin.register(ActivityCategory)
class ActivityCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'icon']
    search_fields = ['name', 'description']
    list_filter = ['name']

@admin.register(EmissionFactor)
class EmissionFactorAdmin(admin.ModelAdmin):
    list_display = ['activity_type', 'category', 'co2_per_unit', 'unit', 'region']
    list_filter = ['category', 'region']
    search_fields = ['activity_type', 'category__name']
    ordering = ['category', 'activity_type']

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'category', 'activity_type', 'quantity', 'unit', 'date', 'calculated_co2']
    list_filter = ['category', 'date', 'user']
    search_fields = ['user__username', 'activity_type', 'notes']
    date_hierarchy = 'date'
    ordering = ['-date']