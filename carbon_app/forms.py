from django import forms
from .models import UserActivity, ActivityCategory

class UserActivityForm(forms.ModelForm):
    """Упрощенная форма для добавления активности"""
    
    # Явно определяем поле категории
    category = forms.ModelChoiceField(
        queryset=ActivityCategory.objects.all(),
        empty_label="Выберите категорию",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Категория активности"
    )
    
    activity_type = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: Поездка на авто'
        }),
        label="Тип активности",
        max_length=100
    )
    
    quantity = forms.FloatField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'min': '0.1'
        }),
        label="Количество"
    )
    
    unit = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'км, кг, кВт·ч'
        }),
        label="Единица измерения",
        max_length=20
    )
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Дополнительные заметки...'
        }),
        label="Заметки",
        required=False
    )
    
    class Meta:
        model = UserActivity
        fields = ['category', 'activity_type', 'quantity', 'unit', 'notes']