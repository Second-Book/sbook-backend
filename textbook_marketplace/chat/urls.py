from django.urls import path

from .views import MessageView, MessageMarkAsSeenView, ConversationView

urlpatterns = [
    path('', MessageView.as_view(), name='chat'),
    path('conversation/<str:username>/', ConversationView.as_view(), name='conversation'),
    path('mark/', MessageMarkAsSeenView.as_view(), name='read-messages'),
]
