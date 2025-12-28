import os

# MUST be set before importing Django modules
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "textbook_marketplace.settings")

# Initialize Django ASGI application early to populate AppRegistry
# before importing models or other Django-dependent modules
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

# Now safe to import Django-dependent modules
from channels.security.websocket import AllowedHostsOriginValidator
from channels.routing import ProtocolTypeRouter, URLRouter
from chat.jwt_middleware import CustomJWTAuthMiddlewareStack
from chat import routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        CustomJWTAuthMiddlewareStack(
            URLRouter(
                routing.websocket_urlpatterns,
            )
        )
    )
})
