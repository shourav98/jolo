# middleware.py
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from .models import UserActivity
from apps.account.models import CustomUser as User
from datetime import timedelta

class OnlineStatusMiddleware(MiddlewareMixin):
    """
    Enhanced middleware to track user online status in real-time
    """

    def process_request(self, request):
        """
        Update user online status on each request with proper timezone handling
        """
        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                # Get or create user activity with proper timezone
                activity, created = UserActivity.objects.get_or_create(
                    user=request.user,
                    defaults={
                        'is_online': True,
                        'last_online': timezone.now(),
                        'last_seen': timezone.now()
                    }
                )
                
                if not created:
                    # Update with current time (timezone aware)
                    activity.is_online = True
                    activity.last_seen = timezone.now()
                    activity.last_online = timezone.now()
                    activity.save(update_fields=['is_online', 'last_seen', 'last_online'])
                
                # Also update UserProfile if it exists
                if hasattr(request.user, 'profile'):
                    request.user.profile.is_online = True
                    request.user.profile.last_online = timezone.now()
                    request.user.profile.save(update_fields=['is_online', 'last_online'])
                    
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error updating online status for {request.user.name}: {e}")

    def process_response(self, request, response):
        """
        No need to mark offline here - let the WebSocket handle disconnections
        """
        return response

class RealTimeOnlineMiddleware(MiddlewareMixin):
    """
    Middleware to provide real-time online status to templates
    """
    
    def process_request(self, request):
        """
        Add online users count and status to request context
        """
        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                # Get online creators count
                online_creators_count = UserActivity.objects.filter(
                    is_online=True,
                    user__profile__is_creator=True
                ).count()
                
                # Get user's own online status
                user_activity = UserActivity.objects.filter(user=request.user).first()
                if user_activity:
                    request.user_online_status = user_activity.get_status_display()
                
                request.online_creators_count = online_creators_count
                
            except Exception as e:
                request.online_creators_count = 0
                request.user_online_status = "Offline"
        
        return None

class JwtAuthMiddleware(BaseMiddleware):
    """
    Enhanced JWT Authentication middleware with better online status tracking
    """

    def __init__(self, inner):
        super().__init__(inner)

    async def __call__(self, scope, receive, send):
        """
        Extract JWT token and update online status for WebSocket connections
        """
        # Get query parameters from scope
        query_string = scope.get('query_string', b'').decode('utf-8')
        query_params = {}

        if query_string:
            for param in query_string.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    query_params[key] = value

        # Extract token from query parameters
        token = query_params.get('token')

        if token:
            try:
                # Decode JWT token
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                user_id = payload.get('user_id')

                if user_id:
                    # Get user from database
                    user = await self.get_user(user_id)
                    if user:
                        scope['user'] = user
                        # Mark user as online for WebSocket connections
                        await self.mark_user_online(user)
                    else:
                        scope['user'] = None
                else:
                    scope['user'] = None
            except jwt.ExpiredSignatureError:
                scope['user'] = None
            except jwt.InvalidTokenError:
                scope['user'] = None
        else:
            scope['user'] = None

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user(self, user_id):
        """Get user from database"""
        User = get_user_model()
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def mark_user_online(self, user):
        """Mark user as online for WebSocket connections"""
        activity, created = UserActivity.objects.get_or_create(
            user=user,
            defaults={
                'is_online': True,
                'last_online': timezone.now(),
                'last_seen': timezone.now()
            }
        )
        
        if not created:
            activity.mark_online()



# import jwt
# from django.conf import settings
# from django.contrib.auth import get_user_model
# from django.utils import timezone
# from django.utils.deprecation import MiddlewareMixin
# from channels.middleware import BaseMiddleware
# from channels.db import database_sync_to_async
# from .models import UserActivity
# from apps.account.models import CustomUser as User


# class OnlineStatusMiddleware(MiddlewareMixin):
#     """
#     Middleware to track user online status for messaging/whisper functionality
#     """

#     def process_request(self, request):
#         """
#         Update user online status on each request
#         """
#         if hasattr(request, 'user') and request.user.is_authenticated:
#             # Update UserActivity for online status tracking
#             activity, created = UserActivity.objects.get_or_create(
#                 user=request.user,
#                 defaults={
#                     'is_online': True,
#                     'last_online': timezone.now()
#                 }
#             )

#             # Update existing activity
#             if not created:
#                 activity.is_online = True
#                 activity.last_online = timezone.now()
#                 activity.save(update_fields=['is_online', 'last_online'])

#             # Also update UserProfile if it exists
#             if hasattr(request.user, 'profile'):
#                 request.user.profile.is_online = True
#                 request.user.profile.last_online = timezone.now()
#                 request.user.profile.save(update_fields=['is_online', 'last_online'])

#     def process_response(self, request, response):
#         """
#         Mark user as offline after request completion (optional)
#         This can be used to implement more sophisticated online tracking
#         """
#         return response


# class WhisperOnlineMiddleware(MiddlewareMixin):
#     """
#     Middleware specifically for whisper/online messaging features
#     """

#     def process_request(self, request):
#         """
#         Add online status information to request for easy access in views
#         """
#         if hasattr(request, 'user') and request.user.is_authenticated:
#             # Add online status to request for easy access
#             try:
#                 activity = request.user.activity
#                 request.user_is_online = activity.is_online
#                 request.user_last_online = activity.last_online
#             except UserActivity.DoesNotExist:
#                 request.user_is_online = False
#                 request.user_last_online = None

#         return None

#     def process_response(self, request, response):
#         """
#         Clean up any temporary attributes added to request
#         """
#         if hasattr(request, 'user_is_online'):
#             delattr(request, 'user_is_online')
#         if hasattr(request, 'user_last_online'):
#             delattr(request, 'user_last_online')

#         return response


# class JwtAuthMiddleware(BaseMiddleware):
#     """
#     JWT Authentication middleware for WebSocket connections
#     """

#     def __init__(self, inner):
#         super().__init__(inner)

#     async def __call__(self, scope, receive, send):
#         """
#         Extract JWT token from WebSocket connection and authenticate user
#         """
#         # Get query parameters from scope
#         query_string = scope.get('query_string', b'').decode('utf-8')
#         query_params = {}

#         if query_string:
#             for param in query_string.split('&'):
#                 if '=' in param:
#                     key, value = param.split('=', 1)
#                     query_params[key] = value

#         # Extract token from query parameters
#         token = query_params.get('token')

#         if token:
#             try:
#                 # Decode JWT token
#                 payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
#                 user_id = payload.get('user_id')

#                 if user_id:
#                     # Get user from database
#                     user = await self.get_user(user_id)
#                     if user:
#                         scope['user'] = user
#                         # Update online status for WebSocket connections
#                         await self.update_online_status(user)
#                     else:
#                         scope['user'] = None
#                 else:
#                     scope['user'] = None
#             except jwt.ExpiredSignatureError:
#                 scope['user'] = None
#             except jwt.InvalidTokenError:
#                 scope['user'] = None
#         else:
#             scope['user'] = None

#         return await super().__call__(scope, receive, send)

#     @database_sync_to_async
#     def get_user(self, user_id):
#         """
#         Get user from database
#         """
#         User = get_user_model()
#         try:
#             return User.objects.get(id=user_id)
#         except User.DoesNotExist:
#             return None

#     @database_sync_to_async
#     def update_online_status(self, user):
#         """
#         Update user online status for WebSocket connections
#         """
#         # Update UserActivity
#         activity, created = UserActivity.objects.get_or_create(
#             user=user,
#             defaults={
#                 'is_online': True,
#                 'last_online': timezone.now()
#             }
#         )

#         if not created:
#             activity.is_online = True
#             activity.last_online = timezone.now()
#             activity.save(update_fields=['is_online', 'last_online'])

#         # Update UserProfile
#         if hasattr(user, 'profile'):
#             user.profile.is_online = True
#             user.profile.last_online = timezone.now()
#             user.profile.save(update_fields=['is_online', 'last_online'])