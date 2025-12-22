"""
Custom JWT authentication middleware for WebSocket connections.
Based on django-channels-jwt-auth-middleware but with proper error handling.
"""
from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from jwt import decode as jwt_decode
from jwt import InvalidSignatureError, ExpiredSignatureError, DecodeError
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class CustomJWTAuthMiddleware:
    """
    Custom JWT auth middleware that handles expired tokens gracefully
    without printing traceback.
    """
    
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        close_old_connections()
        try:
            if(jwt_token_list := parse_qs(scope["query_string"].decode("utf8")).get('token', None)):
                jwt_token = jwt_token_list[0]
                try:
                    jwt_payload = self.get_payload(jwt_token)
                    user_credentials = self.get_user_credentials(jwt_payload)
                    user = await self.get_logged_in_user(user_credentials)
                    scope['user'] = user
                except ExpiredSignatureError:
                    logger.warning("WebSocket connection rejected: JWT token expired", exc_info=False)
                    scope['user'] = AnonymousUser()
                except (InvalidSignatureError, DecodeError) as e:
                    logger.warning(f"WebSocket connection rejected: JWT error - {type(e).__name__}", exc_info=False)
                    scope['user'] = AnonymousUser()
                except KeyError:
                    logger.warning("WebSocket connection rejected: Missing user_id in JWT token", exc_info=False)
                    scope['user'] = AnonymousUser()
            else:
                scope['user'] = AnonymousUser()
        except Exception as e:
            logger.error(f"WebSocket connection error: {type(e).__name__}: {e}", exc_info=False)
            scope['user'] = AnonymousUser()
        return await self.app(scope, receive, send)

    def get_payload(self, jwt_token):
        """Decode JWT token. Raises ExpiredSignatureError, InvalidSignatureError, or DecodeError on failure."""
        payload = jwt_decode(
            jwt_token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload

    def get_user_credentials(self, payload):
        """
        Method to get user credentials from jwt token payload.
        Defaults to user id.
        """
        user_id = payload['user_id']
        return user_id

    async def get_logged_in_user(self, user_id):
        user = await self.get_user(user_id)
        return user

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return AnonymousUser()


def CustomJWTAuthMiddlewareStack(app):
    return CustomJWTAuthMiddleware(AuthMiddlewareStack(app))

