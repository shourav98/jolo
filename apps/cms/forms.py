# core/forms.py   (create this file if it doesn't exist)
from django import forms
from .models import DataDeletionRequest   # we'll create model next

class DataDeletionRequestForm(forms.ModelForm):
    class Meta:
        model = DataDeletionRequest
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={
                'placeholder': 'Tell us why you are requesting data deletion (optional)',
                'rows': 4,
                'class': 'w-full p-3 bg-[#1a1a1a] text-white rounded-lg border border-gray-700'
            })
        }