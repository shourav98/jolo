from django.urls import path, include

urlpatterns = [
    path('account/', include('apps.account.urls')),
    path('chat/', include('apps.messaging.urls')),

]