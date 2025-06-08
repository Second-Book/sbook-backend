import os

from django_channels_jwt_auth_middleware.auth import JWTAuthMiddlewareStack
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
        JWTAuthMiddlewareStack(
            URLRouter(
                routing.websocket_urlpatterns,
            )
        )
    )
})
