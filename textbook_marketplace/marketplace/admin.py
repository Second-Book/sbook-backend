
from django.contrib import admin
from .models import Textbook, User, Block, Report

# Register marketplace app models
admin.site.register(Textbook)
admin.site.register(User)
admin.site.register(Block)
admin.site.register(Report)
