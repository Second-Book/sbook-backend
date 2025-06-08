from django.urls import path, include

urlpatterns = [
    path('', include('marketplace.urls')),
    path('chat', include('chat.urls')),
]