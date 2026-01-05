# carbon_app/admin.py
from django.contrib import admin
from .models import ActivityCategory, EmissionFactor, UserActivity
from .models import Recommendation, UserRecommendation


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

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'co2_saving', 'difficulty', 'is_active']
    list_filter = ['category', 'difficulty', 'is_active']
    search_fields = ['title', 'description']
    ordering = ['-co2_saving']

@admin.register(UserRecommendation)
class UserRecommendationAdmin(admin.ModelAdmin):
    list_display = ['user', 'recommendation', 'is_viewed', 'is_applied', 'created_at']
    list_filter = ['is_viewed', 'is_applied', 'created_at', 'user']
    search_fields = ['user__username', 'recommendation__title']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
