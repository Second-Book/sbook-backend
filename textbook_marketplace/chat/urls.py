from django.urls import path

from .views import MessageView, MessageMarkAsSeenView

urlpatterns = [
    path('', MessageView.as_view(), name='chat'),
    path('mark/', MessageMarkAsSeenView.as_view(), name='read-messages'),
]
