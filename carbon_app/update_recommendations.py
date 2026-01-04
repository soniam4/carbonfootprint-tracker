from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from carbon_app.models import UserRecommendation, Recommendation
from datetime import datetime, timedelta
import random

class Command(BaseCommand):
    help = 'Обновляет рекомендации для всех пользователей'
    
    def handle(self, *args, **kwargs):
        users = User.objects.all()
        
        for user in users:
            # Проверяем, когда были последние рекомендации
            last_recs = UserRecommendation.objects.filter(
                user=user
            ).order_by('-created_at')[:1]
            
            if last_recs:
                last_date = last_recs[0].created_at
                days_since_last = (datetime.now() - last_date).days
                
                # Если прошло больше 14 дней, добавляем новую рекомендацию
                if days_since_last > 14:
                    self.add_new_recommendation(user)
                    self.stdout.write(f'Добавлена рекомендация для {user.username}')
            else:
                # Если у пользователя вообще нет рекомендаций
                self.add_initial_recommendations(user)
                self.stdout.write(f'Добавлены начальные рекомендации для {user.username}')
        
        self.stdout.write(self.style.SUCCESS('✅ Рекомендации обновлены'))
    
    def add_new_recommendation(self, user):
        """Добавляет одну новую рекомендацию"""
        user_recs = UserRecommendation.objects.filter(user=user).values_list('recommendation_id', flat=True)
        available_recs = Recommendation.objects.exclude(id__in=user_recs)
        
        if available_recs.exists():
            new_rec = random.choice(list(available_recs))
            UserRecommendation.objects.create(
                user=user,
                recommendation=new_rec,
                is_viewed=False
            )
    
    def add_initial_recommendations(self, user):
        """Добавляет 5 начальных рекомендаций"""
        all_recs = list(Recommendation.objects.all())
        if len(all_recs) > 5:
            selected_recs = random.sample(all_recs, 5)
        else:
            selected_recs = all_recs
        
        for rec in selected_recs:
            UserRecommendation.objects.create(
                user=user,
                recommendation=rec,
                is_viewed=False
            )