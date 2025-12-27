from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator

class ActivityCategory(models.Model):
    """Категория активности (транспорт, питание, энергия)"""
    name = models.CharField(max_length=100, verbose_name="Название категории")
    description = models.TextField(verbose_name="Описание", blank=True)
    icon = models.CharField(max_length=50, default="bi-activity", verbose_name="Иконка")
    emission_factor_source = models.CharField(max_length=200, verbose_name="Источник данных", blank=True)
    
    class Meta:
        verbose_name = "Категория активности"
        verbose_name_plural = "Категории активностей"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class EmissionFactor(models.Model):
    """Коэффициенты выбросов для расчетов"""
    activity_type = models.CharField(max_length=100, verbose_name="Тип активности")
    category = models.ForeignKey(ActivityCategory, on_delete=models.CASCADE, verbose_name="Категория")
    co2_per_unit = models.FloatField(verbose_name="кг CO₂ на единицу", validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=20, verbose_name="Единица измерения")
    region = models.CharField(max_length=50, default="global", verbose_name="Регион")
    source = models.CharField(max_length=200, verbose_name="Источник данных", blank=True)
    
    class Meta:
        verbose_name = "Коэффициент выбросов"
        verbose_name_plural = "Коэффициенты выбросов"
        ordering = ['category', 'activity_type']
    
    def __str__(self):
        return f"{self.activity_type} ({self.co2_per_unit} кг/{self.unit})"

class UserActivity(models.Model):
    """Активность пользователя с расчетом CO₂"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    category = models.ForeignKey(ActivityCategory, on_delete=models.CASCADE, verbose_name="Категория")
    activity_type = models.CharField(max_length=100, verbose_name="Тип активности")
    quantity = models.FloatField(verbose_name="Количество", validators=[MinValueValidator(0.1)])
    unit = models.CharField(max_length=20, verbose_name="Единица измерения")
    date = models.DateField(auto_now_add=True, verbose_name="Дата")
    calculated_co2 = models.FloatField(verbose_name="Рассчитанный CO₂ (кг)", editable=False, default=0)
    notes = models.TextField(verbose_name="Заметки", blank=True)
    
    class Meta:
        verbose_name = "Активность пользователя"
        verbose_name_plural = "Активности пользователей"
        ordering = ['-date']
    
    def save(self, *args, **kwargs):
        """Автоматический расчет CO₂ при сохранении"""
        try:
            # Пытаемся найти коэффициент для данного типа активности
            factor = EmissionFactor.objects.get(
                activity_type=self.activity_type,
                category=self.category,
                unit=self.unit
            )
            self.calculated_co2 = self.quantity * factor.co2_per_unit
        except EmissionFactor.DoesNotExist:
            # Значение по умолчанию для демонстрации
            self.calculated_co2 = self.quantity * 2.5
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.username}: {self.activity_type} ({self.date}) - {self.calculated_co2} кг CO₂"

class Recommendation(models.Model):
    """Рекомендации по снижению углеродного следа"""
    PRIORITY_CHOICES = [
        ('high', 'Высокий приоритет'),
        ('medium', 'Средний приоритет'),
        ('low', 'Низкий приоритет'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Заголовок рекомендации")
    description = models.TextField(verbose_name="Подробное описание")
    category = models.ForeignKey(ActivityCategory, on_delete=models.CASCADE, 
                                verbose_name="Категория", null=True, blank=True)
    co2_saving = models.FloatField(verbose_name="Экономия CO₂ (кг/месяц)", default=0)
    difficulty = models.CharField(max_length=20, choices=PRIORITY_CHOICES, 
                                 default='medium', verbose_name="Сложность внедрения")
    is_general = models.BooleanField(default=True, verbose_name="Общая рекомендация")
    
    class Meta:
        verbose_name = "Рекомендация"
        verbose_name_plural = "Рекомендации"
        ordering = ['-co2_saving']
    
    def __str__(self):
        return self.title