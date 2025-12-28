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

        # AbstractUser requires username, so we use email as username for superuser
        username = email  # Use email as username for superuser
        
        # Check if user already exists by email
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            # Check if it's already a superuser
            if existing_user.is_superuser:
                self.stdout.write(self.style.SUCCESS(f'Superuser {email} already exists'))
            else:
                # Update existing user to superuser
                existing_user.is_superuser = True
                existing_user.is_staff = True
                existing_user.set_password(password)
                existing_user.save()
                self.stdout.write(self.style.SUCCESS(f'User {email} promoted to superuser'))
            return
        
        # Check if username is already taken (shouldn't happen if email is unique and username=email)
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(
                f'Username {username} already exists with different email. Skipping superuser creation.'
            ))
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'Superuser {email} created with username {username}'))

