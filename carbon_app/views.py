from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Avg, Count
from django.http import JsonResponse
import pandas as pd
import plotly.express as px
import plotly.io as pio
from datetime import datetime, timedelta
import random
# В начале файла добавьте импорт
from django.db.models import Sum, Count, Q
import json
from .models import UserActivity, ActivityCategory, EmissionFactor, Recommendation
from .forms import UserActivityForm
from django.contrib.auth import login, logout as auth_logout, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
import json
import os
from django.conf import settings
from django.utils import timezone 

def home(request):
    # Просто берём все активные рекомендации
    recommendations = Recommendation.objects.filter(is_active=True)
    
    # Группируем по категориям для красивого отображения
    rec_by_category = {}
    for rec in recommendations:
        if rec.category not in rec_by_category:
            rec_by_category[rec.category] = []
        rec_by_category[rec.category].append(rec)
    
    context = {
        'recommendations': recommendations,
        'rec_by_category': rec_by_category,
    }
    return render(request, 'carbon_app/home.html', context)

@login_required
def dashboard(request):
    """Личный кабинет пользователя с аналитикой"""
    from datetime import date, timedelta
    import json
    
    # Получаем данные пользователя
    user_activities = UserActivity.objects.filter(user=request.user)
    
    # 1. Базовая статистика
    total_co2 = user_activities.aggregate(Sum('calculated_co2'))['calculated_co2__sum'] or 0
    avg_daily = user_activities.aggregate(Avg('calculated_co2'))['calculated_co2__avg'] or 0
    activity_count = user_activities.count()
    
    # 2. Аналитика по категориям (Pandas + сложные расчеты)
    category_stats = []
    chart_data = []
    
    if user_activities.exists():
        # Группировка по категориям
        categories = ActivityCategory.objects.all()
        
        for category in categories:
            cat_activities = user_activities.filter(category=category)
            cat_total = cat_activities.aggregate(Sum('calculated_co2'))['calculated_co2__sum'] or 0
            cat_count = cat_activities.count()
            
            if cat_count > 0:
                percentage = (cat_total / total_co2 * 100) if total_co2 > 0 else 0
                category_stats.append({
                    'category': category,
                    'total_co2': round(cat_total, 2),
                    'count': cat_count,
                    'percentage': round(percentage, 1),
                })
                
                chart_data.append({
                    'category': category.name,
                    'value': round(cat_total, 2),
                    'color': '#28a745' if percentage < 30 else '#ffc107' if percentage < 60 else '#dc3545'
                })
    
    # 3. Еженедельная статистика (для графика)
    weekly_data = []
    for i in range(6, -1, -1):
        day = date.today() - timedelta(days=i)
        day_activities = user_activities.filter(date=day)
        day_total = day_activities.aggregate(Sum('calculated_co2'))['calculated_co2__sum'] or 0
        weekly_data.append({
            'day': day.strftime('%a'),
            'date': day.strftime('%d.%m'),
            'co2': round(day_total, 2),
        })
    
    # 4. Рекомендации (простая логика)
    recommendations = []
    if total_co2 > 50:  # Если общий след больше 50 кг
        recommendations.append({
            'title': 'Снизьте использование автомобиля',
            'description': 'Попробуйте общественный транспорт 2 раза в неделю',
            'saving': '~5 кг CO₂ в неделю',
            'priority': 'high'
        })
    
    if len(category_stats) > 0:
        max_category = max(category_stats, key=lambda x: x['percentage'])
        if max_category['percentage'] > 40:
            recommendations.append({
                'title': f'Сфокусируйтесь на категории "{max_category["category"].name}"',
                'description': f'Эта категория составляет {max_category["percentage"]}% вашего следа',
                'saving': '~10-30% от общего следа',
                'priority': 'medium'
            })
    
    # 5. Сравнение со средним (16000 кг/год = ~44 кг/день)
    daily_average_global = 44  # кг/день
    user_daily_avg = avg_daily
    comparison = "ниже" if user_daily_avg < daily_average_global else "выше"
    comparison_percent = abs((user_daily_avg - daily_average_global) / daily_average_global * 100)

    context = {
        # Статистика
        'total_co2': round(total_co2, 2),
        'avg_daily': round(avg_daily, 2),
        'activity_count': activity_count,
        
        # Аналитика
        'category_stats': category_stats,
        'chart_data_json': json.dumps(chart_data),
        'weekly_data': weekly_data,
        'weekly_data_json': json.dumps([item['co2'] for item in weekly_data]),
        
        # Рекомендации
        'recommendations': recommendations,
        
        # Сравнение
        'daily_average_global': daily_average_global,
        'comparison': comparison,
        'comparison_percent': round(comparison_percent, 1),
        
        # Последние активности
        'recent_activities': user_activities.order_by('-date')[:10],
    }
    
    return render(request, 'carbon_app/dashboard.html', context)

@login_required
def add_activity(request):
    """Добавление новой активности - РАБОЧАЯ ВЕРСИЯ"""
    
    # Получаем все категории из базы
    categories = ActivityCategory.objects.all()
    
    if request.method == 'POST':
        # Получаем данные напрямую из request.POST
        category_id = request.POST.get('category')
        activity_type = request.POST.get('activity_type', '').strip()
        quantity = request.POST.get('quantity', '0')
        unit = request.POST.get('unit', '').strip()
        notes = request.POST.get('notes', '').strip()
        
        # Валидация
        errors = []
        
        if not category_id:
            errors.append('Выберите категорию')
        
        if not activity_type:
            errors.append('Введите тип активности')
        
        try:
            quantity = float(quantity)
            if quantity <= 0:
                errors.append('Количество должно быть больше 0')
        except ValueError:
            errors.append('Введите корректное число')
        
        if not unit:
            errors.append('Введите единицу измерения')
        
        # Если есть ошибки - показываем их
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # СОЗДАЕМ запись вручную
            try:
                category = ActivityCategory.objects.get(id=category_id)
                
                activity = UserActivity(
                    user=request.user,
                    category=category,
                    activity_type=activity_type,
                    quantity=quantity,
                    unit=unit,
                    notes=notes
                )
                activity.save()  # Автоматически рассчитается CO₂
                
                messages.success(request, '✅ Активность успешно добавлена!')
                update_user_recommendations(request.user)
                return redirect('dashboard')
                
            except ActivityCategory.DoesNotExist:
                messages.error(request, '❌ Выбранная категория не найдена')
            except Exception as e:
                messages.error(request, f'❌ Ошибка при сохранении: {str(e)}')
        
    # Контекст для шаблона
    context = {
        'categories': categories,  # Передаем категории в шаблон
    }
    
    return render(request, 'carbon_app/add_activity.html', context)

def update_user_recommendations(user):
    """Генерирует рекомендации на основе активности за последние 30 дней"""
    from .models import UserActivity, UserRecommendation, Recommendation
    from datetime import datetime, timedelta

    # Проверяем, сколько уже рекомендаций
    existing_count = UserRecommendation.objects.filter(user=user).count()
    
    # Если меньше 4 — добавим начальные (на всякий случай)
    if existing_count < 4:
        assign_initial_recommendations(user)
        return

    # Если прошло меньше 7 дней с последнего обновления — не обновляем
    last_update = UserRecommendation.objects.filter(user=user).order_by('-created_at').first()
    if last_update and (timezone.now() - last_update.created_at).days < 7:
        return

    # Анализируем активность за 30 дней
    month_ago = timezone.now() - timedelta(days=30)
    activities = UserActivity.objects.filter(user=user, date__gte=month_ago.date())
    
    if not activities.exists():
        return

    # Считаем CO₂ по категориям
    from collections import defaultdict
    co2_by_cat = defaultdict(float)
    for act in activities:
        cat_name = act.category.name.lower()
        co2_by_cat[cat_name] += act.calculated_co2

    if not co2_by_cat:
        return

    # Находим категорию с макс. выбросами
    top_cat = max(co2_by_cat, key=co2_by_cat.get)

    # Маппинг ActivityCategory.name → Recommendation.category
    category_map = {
        'transport': 'transport',
        'транспорт': 'transport',
        'food': 'food',
        'питание': 'food',
        'energy': 'energy',
        'энергия': 'energy',
        'lifestyle': 'shopping',
        'образ жизни': 'shopping',
        'покупки': 'shopping',
    }

    target_cat = category_map.get(top_cat, 'general')

    # Берём 1–2 рекомендации из этой категории
    new_recs = Recommendation.objects.filter(
        category=target_cat,
        is_active=True
    ).exclude(
        id__in=UserRecommendation.objects.filter(user=user).values_list('recommendation_id', flat=True)
    ).order_by('-co2_saving')[:2]

    for rec in new_recs:
        UserRecommendation.objects.create(user=user, recommendation=rec, is_viewed=False)


def add_new_recommendation(user):
    """Добавляет новую рекомендацию пользователю"""
    from .models import UserRecommendation, Recommendation
    import random
    
    # Получаем рекомендации, которые у пользователя еще нет
    user_recs = UserRecommendation.objects.filter(user=user).values_list('recommendation_id', flat=True)
    available_recs = Recommendation.objects.exclude(id__in=user_recs)
    
    if available_recs.exists():
        # Выбираем случайную рекомендацию
        new_rec = random.choice(list(available_recs))
        
        # Создаем новую связь
        UserRecommendation.objects.create(
            user=user,
            recommendation=new_rec,
            is_viewed=False
        )
        
        return True
    
    return False

@login_required
def activities_list(request):
    """Список всех активностей пользователя"""
    activities = UserActivity.objects.filter(user=request.user).order_by('-date')
    return render(request, 'carbon_app/activities_list.html', {'activities': activities})

def calculator(request):
    """Калькулятор углеродного следа"""
    result = None
    error = None
    
    if request.method == 'POST':
        try:
            category = request.POST.get('category')
            activity_type = request.POST.get('activity_type', '').strip()
            quantity = float(request.POST.get('quantity', 0))
            
            if not activity_type:
                error = "Введите тип активности"
                return render(request, 'carbon_app/calculator.html', {'error': error})
            
            # Определяем единицу измерения по категории
            if category == 'transport':
                unit = 'км'
                co2_per_unit = 0.1  # Среднее значение
            elif category == 'food':
                unit = 'кг'
                co2_per_unit = 5.0  # Среднее значение
            elif category == 'energy':
                unit = 'кВт·ч'
                co2_per_unit = 0.5  # Среднее значение
            else:
                unit = 'ед.'
                co2_per_unit = 0.1
            
            # Рассчитываем CO2
            calculated_co2 = quantity * co2_per_unit
            
            result = {
                'category': category,
                'activity_type': activity_type,
                'quantity': quantity,
                'unit': unit,
                'co2_per_unit': co2_per_unit,
                'calculated_co2': round(calculated_co2, 2)
            }
            
            # Сохраняем если пользователь авторизован
            if request.user.is_authenticated:
                from .models import UserActivity, ActivityCategory
                
                category_obj, created = ActivityCategory.objects.get_or_create(
                    name=category,
                    defaults={'description': f'Категория {category}'}
                )
                
                UserActivity.objects.create(
                    user=request.user,
                    category=category_obj,
                    activity_type=activity_type,
                    quantity=quantity,
                    unit=unit,
                    calculated_co2=calculated_co2
                )
                
                result['saved'] = True
                
        except ValueError:
            error = "Введите корректное числовое значение количества"
        except Exception as e:
            error = f"Ошибка расчета: {str(e)}"
    
    return render(request, 'carbon_app/calculator.html', {'result': result, 'error': error})

@login_required
def delete_activity(request, activity_id):
    """Удаление активности"""
    activity = get_object_or_404(UserActivity, id=activity_id, user=request.user)
    activity.delete()
    messages.success(request, 'Активность удалена')
    return redirect('activities_list')

@login_required
def recommendations_page(request):
    from .models import UserRecommendation
    
    user_recs = UserRecommendation.objects.filter(user=request.user).select_related('recommendation')
    
    stats = {
        'applied': user_recs.filter(is_applied=True).count(),
        'total': user_recs.count(),
        'new': user_recs.filter(is_viewed=False).count(),
    }
    
    # Группировка по категории из модели Recommendation (строка: 'transport', 'food' и т.д.)
    recs_by_category = {}
    for ur in user_recs:
        cat = ur.recommendation.category  # Это строка!
        if cat not in recs_by_category:
            recs_by_category[cat] = []
        recs_by_category[cat].append(ur)
    
    return render(request, 'carbon_app/recommendations.html', {
        'recs_by_category': recs_by_category,
        'stats': stats,
    })

@login_required
def generate_recommendations(request):
    """Генерирует новые рекомендации на основе активности пользователя"""
    update_user_recommendations(request.user)
    messages.success(request, '✅ Рекомендации обновлены!')
    return redirect('recommendations')

def assign_initial_recommendations(user):
    """Назначает начальные рекомендации пользователю"""
    from .models import Recommendation, UserRecommendation
    
    # Получаем 6 случайных рекомендаций
    all_recs = Recommendation.objects.all()
    if all_recs.count() > 6:
        selected_recs = random.sample(list(all_recs), 6)
    else:
        selected_recs = all_recs
    
    # Создаем связи
    for rec in selected_recs:
        UserRecommendation.objects.get_or_create(
            user=user,
            recommendation=rec,
            defaults={'is_viewed': False}
        )

@login_required
def mark_recommendation_viewed(request, rec_id):
    """Отметить как просмотренное"""
    try:
        from .models import UserRecommendation
        user_rec = UserRecommendation.objects.get(id=rec_id, user=request.user)
        user_rec.is_viewed = True
        user_rec.save()
        return JsonResponse({'success': True})
    except:
        return JsonResponse({'success': False})


@login_required
def mark_recommendation_applied(request, rec_id):
    """Отметить как примененное"""
    try:
        from .models import UserRecommendation
        user_rec = UserRecommendation.objects.get(id=rec_id, user=request.user)
        user_rec.is_applied = True
        user_rec.save()
        return JsonResponse({'success': True})
    except:
        return JsonResponse({'success': False})


@login_required
def recommendation_detail(request, rec_id):
    """Детальная страница"""
    from .models import UserRecommendation
    try:
        user_rec = UserRecommendation.objects.get(id=rec_id, user=request.user)
        context = {'user_rec': user_rec}
        return render(request, 'carbon_app/recommendation_detail.html', context)
    except:
        return redirect('recommendations')
    
def login_view(request):
    """Вход в систему"""
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
    return render(request, 'carbon_app/login.html')

def register_view(request):
    """Регистрация"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            assign_initial_recommendations(user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'carbon_app/register.html', {'form': form})

@login_required
def logout_view(request):
    """Выход из системы"""
    auth_logout(request)
    return redirect('home')


def create_initial_recommendations():
    """Создает начальные рекомендации в базе данных"""
    from .models import Recommendation
    
    recommendations = [
        # Транспорт
        {
            'title': 'Используйте общественный транспорт',
            'description': 'Автобусы и метро производят меньше CO₂ на пассажира, чем личные автомобили.',
            'category': 'transport',
            'difficulty': 'medium',
            'co2_saving': 30.0,
            'icon': 'bus-front'
        },
        {
            'title': 'Выбирайте велосипед на короткие расстояния',
            'description': 'Поездки на велосипеде до 5 км вместо авто полностью исключают выбросы.',
            'category': 'transport',
            'difficulty': 'easy',
            'co2_saving': 20.0,
            'icon': 'bicycle'
        },
        {
            'title': 'Планируйте поездки',
            'description': 'Объединяйте несколько дел в одну поездку, чтобы сократить километраж.',
            'category': 'transport',
            'difficulty': 'easy',
            'co2_saving': 15.0,
            'icon': 'geo-alt'
        },
        
        # Питание
        {
            'title': 'Введите вегетарианский день',
            'description': 'Один день без мяса в неделю может снизить углеродный след на 10-15%.',
            'category': 'food',
            'difficulty': 'medium',
            'co2_saving': 15.0,
            'icon': 'egg-fried'
        },
        {
            'title': 'Покупайте местные продукты',
            'description': 'Продукты местного производства требуют меньше транспортировки.',
            'category': 'food',
            'difficulty': 'easy',
            'co2_saving': 8.0,
            'icon': 'geo'
        },
        {
            'title': 'Сократите пищевые отходы',
            'description': 'Планируйте покупки и используйте остатки. 30% еды выбрасывается.',
            'category': 'food',
            'difficulty': 'medium',
            'co2_saving': 12.0,
            'icon': 'trash'
        },
        
        # Энергия
        {
            'title': 'Выключайте свет',
            'description': 'Выключайте свет в пустых комнатах и используйте LED-лампочки.',
            'category': 'energy',
            'difficulty': 'easy',
            'co2_saving': 10.0,
            'icon': 'lightbulb'
        },
        {
            'title': 'Оптимизируйте отопление',
            'description': 'Снижение температуры на 1°C зимой экономит до 10% энергии.',
            'category': 'energy',
            'difficulty': 'medium',
            'co2_saving': 25.0,
            'icon': 'thermometer-snow'
        },
        {
            'title': 'Отключайте технику от сети',
            'description': 'Техника в режиме standby потребляет до 10% электроэнергии.',
            'category': 'energy',
            'difficulty': 'easy',
            'co2_saving': 8.0,
            'icon': 'plug'
        },
        
        # Образ жизни
        {
            'title': 'Используйте многоразовые сумки',
            'description': 'Отказ от пластиковых пакетов снижает выбросы и количество отходов.',
            'category': 'lifestyle',
            'difficulty': 'easy',
            'co2_saving': 5.0,
            'icon': 'bag'
        },
        {
            'title': 'Сортируйте отходы',
            'description': 'Переработка помогает снизить выбросы от производства новых материалов.',
            'category': 'lifestyle',
            'difficulty': 'medium',
            'co2_saving': 10.0,
            'icon': 'recycle'
        },
        {
            'title': 'Экономьте воду',
            'description': 'Выключайте воду при чистке зубов, принимайте душ вместо ванны.',
            'category': 'lifestyle',
            'difficulty': 'easy',
            'co2_saving': 4.0,
            'icon': 'droplet'
        },
    ]
    
    for rec_data in recommendations:
        Recommendation.objects.get_or_create(
            title=rec_data['title'],
            defaults=rec_data
        )
    
    print(f"✅ Создано {len(recommendations)} рекомендаций")