import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async
from urllib.parse import parse_qs
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None

class JwtAuthMiddleware:
    """
    Custom middleware for authenticating via JWT token in query string
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Parse query string properly
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        
        token = None
        if 'token' in query_params:
            token = query_params['token'][0]

        scope["user"] = None

        if token:
            try:
                # Add more debugging
                logger.info(f"Attempting to decode token: {token[:50]}...")
                
                # Decode the JWT token
                payload = jwt.decode(
                    token, 
                    settings.SECRET_KEY, 
                    algorithms=["HS256"],
                    options={"verify_exp": True}
                )
                
                user_id = payload.get("user_id")
                logger.info(f"Extracted user_id from token: {user_id}")
                
                if user_id:
                    user = await get_user(user_id)
                    if user:
                        scope["user"] = user
                        logger.info(f"User authenticated: {user.name} (ID: {user.id})")
                    else:
                        logger.warning(f"User not found with ID: {user_id}")
                else:
                    logger.warning("No user_id found in token payload")
                    
            except jwt.ExpiredSignatureError:
                logger.warning("JWT token has expired")
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid JWT token: {e}")
            except Exception as e:
                logger.error(f"Unexpected error during JWT authentication: {e}")

        # Log authentication result
        if scope["user"]:
            logger.info(f"WebSocket connection authenticated for user: {scope['user'].name}")
        else:
            logger.warning("WebSocket connection anonymous - no valid authentication")

        return await self.app(scope, receive, send)