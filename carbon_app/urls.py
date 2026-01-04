from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('my-footprint/', views.dashboard, name='my_footprint'),
    path('add-activity/', views.add_activity, name='add_activity'),
    path('activities/', views.activities_list, name='activities_list'),
    path('calculator/', views.calculator, name='calculator'),
    path('activity/delete/<int:activity_id>/', views.delete_activity, name='delete_activity'),
    
    # Аутентификация
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Рекомендации
    path('recommendations/', views.recommendations_page, name='recommendations'),
    path('recommendations/generate/', views.generate_recommendations, name='generate_recommendations'),
    path('recommendations/<int:rec_id>/mark-viewed/', views.mark_recommendation_viewed, name='mark_recommendation_viewed'),
    path('recommendations/<int:rec_id>/mark-applied/', views.mark_recommendation_applied, name='mark_recommendation_applied'),
    path('recommendations/<int:rec_id>/', views.recommendation_detail, name='recommendation_detail'),
]