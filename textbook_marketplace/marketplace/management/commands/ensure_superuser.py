"""
Management command to ensure superuser exists (idempotent).

Usage:
    python manage.py ensure_superuser

Requires environment variables (from .env file):
    DJANGO_SUPERUSER_EMAIL - Email for superuser
    DJANGO_SUPERUSER_PASSWORD - Password for superuser
"""

from decouple import config
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


User = get_user_model()


class Command(BaseCommand):
    help = 'Create superuser if not exists (idempotent)'

    def handle(self, *args, **options):
        email = config('DJANGO_SUPERUSER_EMAIL', default=None)
        password = config('DJANGO_SUPERUSER_PASSWORD', default=None)

        if not email or not password:
            self.stdout.write(self.style.WARNING(
                'DJANGO_SUPERUSER_EMAIL or DJANGO_SUPERUSER_PASSWORD not set, skipping'
            ))
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.SUCCESS(f'Superuser {email} already exists'))
            return

        User.objects.create_superuser(email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'Superuser {email} created'))

