from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.cms.urls')),
    path('api/', include('apps.account.urls')),
    path('api/', include('apps.feed.urls')),
    path("api/", include("apps.monetization.urls")),
    path("api/", include("apps.messaging.urls")),
    path("api/notifications/", include("apps.notification.urls")),
    path('ckeditor5/', include('django_ckeditor_5.urls')),
    # path("api/", include("apps.chatting_app.urls")),
]

if settings.DEBUG:
    # Development only: serve media & static files
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
