# core/urls.py
from django.urls import path
from .views import legal_page, support_safety_page

urlpatterns = [
    path('legal/', legal_page, name='legal_page'),
    path('support-safety/', support_safety_page, name='support_safety'),
]
