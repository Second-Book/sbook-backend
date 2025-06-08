from django.contrib import admin

from .models import Message

# Register chat app models
admin.site.register(Message)
