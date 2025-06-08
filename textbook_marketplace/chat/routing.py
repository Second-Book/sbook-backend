from django.urls import path

from .consumers import ChatConsumer


websocket_urlpatterns = [
    path('chat/<str:room_name>/', ChatConsumer.as_asgi()),
]
