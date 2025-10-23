# project/asgi.py
import os
import django
from django.core.asgi import get_asgi_application

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

# Setup Django first
django.setup()

# Now import the rest after Django is configured
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.sessions import SessionMiddlewareStack
from apps.messaging.routing import websocket_urlpatterns
from apps.messaging.middleware import JwtAuthMiddleware

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JwtAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})



# import os
# from django.core.asgi import get_asgi_application
# from channels.auth import AuthMiddlewareStack
# from channels.routing import ProtocolTypeRouter, URLRouter

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

# import django
# django.setup()  # ensures apps are loaded

# from apps.messaging import routing

# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": AuthMiddlewareStack(
#         URLRouter(
#             routing.websocket_urlpatterns
#         )
#     ),
# })


# import os
# from django.core.asgi import get_asgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
# django_asgi_app = get_asgi_application()

# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# from apps.messaging import routing as chat_routing  # ✅ safe to import AFTER settings

# application = ProtocolTypeRouter({
#     "http": django_asgi_app,
#     "websocket": AuthMiddlewareStack(
#         URLRouter(
#             chat_routing.websocket_urlpatterns
#         )
#     ),
# })
