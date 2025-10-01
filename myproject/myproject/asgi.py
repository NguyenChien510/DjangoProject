import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import realtime.routing


# Gói static handler cho HTTP trong dev mode
from django.core.asgi import get_asgi_application
django_asgi_app = ASGIStaticFilesHandler(get_asgi_application())


application = ProtocolTypeRouter({
    "http": django_asgi_app,  # Dùng handler này để load static
    "websocket": AuthMiddlewareStack(
        URLRouter(
            realtime.routing.websocket_urlpatterns
        )
    ),
})
