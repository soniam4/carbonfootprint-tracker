from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Avg, Count
from django.http import JsonResponse
import pandas as pd
import plotly.express as px
import plotly.io as pio
from datetime import datetime, timedelta

from .models import UserActivity, ActivityCategory, EmissionFactor
from .forms import UserActivityForm

def home(request):
    """Главная страница для гостей"""
    return render(request, 'carbon_app/home.html')

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

@login_required
def activities_list(request):
    """Список всех активностей пользователя"""
    activities = UserActivity.objects.filter(user=request.user).order_by('-date')
    return render(request, 'carbon_app/activities_list.html', {'activities': activities})

def calculator(request):
    """Упрощенный калькулятор"""
    result = None
    
    if request.method == 'POST':
        activity_type = request.POST.get('activity_type', '')
        quantity = request.POST.get('quantity', '0')
        
        try:
            quantity = float(quantity)
            if quantity <= 0:
                messages.error(request, 'Количество должно быть больше 0')
                return redirect('calculator')
        except ValueError:
            messages.error(request, 'Введите корректное число')
            return redirect('calculator')
        
        # Простые коэффициенты
        co2_factors = {
            'car': 0.12,      # авто - 0.12 кг/км
            'bus': 0.03,      # автобус - 0.03 кг/км
            'plane': 0.25,    # самолет - 0.25 кг/км
            'beef': 27.0,     # говядина - 27 кг/кг
            'chicken': 6.0,   # курица - 6 кг/кг
            'electricity': 0.4, # электричество - 0.4 кг/кВт·ч
        }
        
        activity_names = {
            'car': 'Поездка на автомобиле',
            'bus': 'Поездка на автобусе',
            'plane': 'Перелет на самолете',
            'beef': 'Употребление говядины',
            'chicken': 'Употребление курицы',
            'electricity': 'Потребление электроэнергии',
        }
        
        units = {
            'car': 'км', 'bus': 'км', 'plane': 'км',
            'beef': 'кг', 'chicken': 'кг',
            'electricity': 'кВт·ч',
        }
        
        if activity_type in co2_factors:
            calculated_co2 = quantity * co2_factors[activity_type]
            result = {
                'activity_type': activity_names[activity_type],
                'quantity': quantity,
                'unit': units[activity_type],
                'calculated_co2': round(calculated_co2, 2),
            }
        else:
            messages.error(request, 'Выберите тип активности')
    
    return render(request, 'carbon_app/calculator.html', {'result': result})

@login_required
def delete_activity(request, activity_id):
    """Удаление активности"""
    activity = get_object_or_404(UserActivity, id=activity_id, user=request.user)
    activity.delete()
    messages.success(request, 'Активность удалена')
    return redirect('activities_list')

@login_required
def recommendations_page(request):
    """Страница со всеми рекомендациями"""
    # Персонализированные рекомендации
    from carbon_app.models import Recommendation
    
    all_recommendations = Recommendation.objects.all()
    
    # Группируем по категориям
    recommendations_by_category = {}
    for rec in all_recommendations:
        category_name = rec.category.name if rec.category else "Общие"
        if category_name not in recommendations_by_category:
            recommendations_by_category[category_name] = []
        recommendations_by_category[category_name].append(rec)
    
    context = {
        'recommendations_by_category': recommendations_by_category,
        'total_recommendations': all_recommendations.count(),
    }
    
    return render(request, 'carbon_app/recommendations.html', context)