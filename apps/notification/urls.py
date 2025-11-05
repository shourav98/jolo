from django.urls import path
from .views import NotificationListView, MarkAsReadView, NotificationDeleteView

urlpatterns = [
    path('', NotificationListView.as_view(), name='notifications-list'),
    path('<int:notification_id>/read/', MarkAsReadView.as_view(), name='notification-read'),
    path('<int:notification_id>/delete/', NotificationDeleteView.as_view(), name='notification-delete'),
]
