# core/views.py
from django.shortcuts import render
from .models import InfoSection

def legal_page(request):
    sections = InfoSection.objects.filter(page='legal', is_active=True)
    return render(request, 'pages/legal.html', {'sections': sections})


def support_safety_page(request):
    sections = InfoSection.objects.filter(page='support', is_active=True)
    return render(request, 'pages/support_safety.html', {'sections': sections})


def legal_page_user(request):
    sections = InfoSection.objects.filter(page='legal_user', is_active=True)
    return render(request, 'pages/legal_user.html', {'sections': sections})


def support_safety_page_user(request):
    sections = InfoSection.objects.filter(page='support_user', is_active=True)
    return render(request, 'pages/support_safety_user.html', {'sections': sections})
