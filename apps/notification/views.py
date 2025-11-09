from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Notification
from .serializers import NotificationSerializer


# Unified API Response
def api_response(success=True, message="Success", data=None, status_code=200):
    return Response(
        {
            "success": success,
            "status_code": status_code,
            "message": message,
            "data": data if data is not None else [],
        },
        status=status_code,
    )


class NotificationListView(APIView):
    
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)

        return api_response(
            success=True,
            message="Notifications fetched successfully.",
            data={
                "count": notifications.count(),
                "notifications": serializer.data
            },
            status_code=200
        )


class MarkAsReadView(APIView):
    
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        try:
            notif = Notification.objects.get(id=notification_id, user=request.user)
            notif.is_read = True
            notif.save(update_fields=["is_read"])
            return api_response(
                success=True,
                message="Notification marked as read successfully.",
                data={"notification_id": notif.id},
                status_code=200
            )
        except Notification.DoesNotExist:
            return api_response(
                success=False,
                message="Notification not found.",
                status_code=404
            )


class NotificationDeleteView(APIView):
   
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, notification_id):
        try:
            notif = Notification.objects.get(id=notification_id, user=request.user)
            notif.delete()
            return api_response(
                success=True,
                message="Notification deleted successfully.",
                data={"notification_id": notification_id},
                status_code=200
            )
        except Notification.DoesNotExist:
            return api_response(
                success=False,
                message="Notification not found.",
                status_code=404
            )
