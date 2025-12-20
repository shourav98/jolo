# core/urls.py
from django.urls import path
from .views import legal_page, support_safety_page, legal_page_user, support_safety_page_user

urlpatterns = [
    path('legal/', legal_page, name='legal_page'),
    path('support-safety/', support_safety_page, name='support_safety'),

    #user 
    path('legal-user/', legal_page_user, name='legal_page'),
    path('support-safety-user/', support_safety_page_user, name='support_safety'),
]
