from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from apps.messaging.middleware import JWTAuthMiddleware
import apps.messaging.routing

application = ProtocolTypeRouter({
    "websocket": JWTAuthMiddleware(
        AuthMiddlewareStack(
            URLRouter(
                apps.messaging.routing.websocket_urlpatterns
            )
        )
    ),
})
