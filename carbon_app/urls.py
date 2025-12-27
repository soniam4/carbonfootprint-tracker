from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add-activity/', views.add_activity, name='add_activity'),
    path('activities/', views.activities_list, name='activities_list'),
    path('calculator/', views.calculator, name='calculator'),
    path('activity/delete/<int:activity_id>/', views.delete_activity, name='delete_activity'),
    path('recommendations/', views.recommendations_page, name='recommendations'),
]