import os

from chat.jwt_middleware import CustomJWTAuthMiddlewareStack
from django.core.asgi import get_asgi_application  # DEBUG
from channels.security.websocket import AllowedHostsOriginValidator
from channels.routing import (
    ProtocolTypeRouter,
    URLRouter,
)

from chat import routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                      "textbook_marketplace.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),  # DEBUG
    "websocket": AllowedHostsOriginValidator(
        CustomJWTAuthMiddlewareStack(
            URLRouter(
                routing.websocket_urlpatterns,
            )
        )
    )
})
