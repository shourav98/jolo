# core/urls.py
from django.urls import path
from .views import legal_page, support_safety_page, legal_page_user, support_safety_page_user, privacy_policy, data_usage_overview, request_data_deletion, DataDeletionAPIView

urlpatterns = [
    path('legal/', legal_page, name='legal_page'),
    path('support-safety/', support_safety_page, name='support_safety'),

    #user 
    path('legal-user/', legal_page_user, name='legal_page'),
    path('support-safety-user/', support_safety_page_user, name='support_safety'),

    #Privacy Policy and Data Usage sections
    path('privacy/',                privacy_policy,               name='privacy_policy'),
    path('data-usage/',             data_usage_overview,          name='data_usage_overview'),
    path('request-data-deletion/',  request_data_deletion,        name='request_data_deletion'),
    
    # API endpoints
    path('api/request-data-deletion/', DataDeletionAPIView.as_view(), name='api_request_data_deletion'),
]

