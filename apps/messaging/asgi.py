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





# import os
# import django
# from channels.routing import ProtocolTypeRouter, URLRouter
# from django.core.asgi import get_asgi_application
# from channels.auth import AuthMiddlewareStack
# from . import routing as chat_routing

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
# django.setup()

# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": AuthMiddlewareStack(
#         URLRouter(chat_routing.websocket_urlpatterns)
#     ),
# })





# import os
# import django
# from channels.routing import ProtocolTypeRouter, URLRouter
# from django.core.asgi import get_asgi_application
# from channels.auth import AuthMiddlewareStack
# from . import routing as chat_routing

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
# django.setup()

# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": AuthMiddlewareStack(
#         URLRouter(chat_routing.websocket_urlpatterns)
#     ),
# })