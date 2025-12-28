from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from faker import Faker
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate fake users with specified count'

    def add_arguments(self, parser):
        parser.add_argument('count', type=int, help='Number of users to generate')

    def handle(self, *args, **options):
        count = options['count']
        fake = Faker()

        for _ in range(count):
            username = fake.user_name()
            email = fake.email()
            telegram_id = fake.uuid4()  # Или другое значение для telegram_id
            telephone = fake.phone_number()
            is_seller = random.choice([True, False])

            # Создаем пользователя
            user = User.objects.create(
                username=username,
                email=email,
                telegram_id=telegram_id,
                telephone=telephone,
                is_seller=is_seller,
                is_active=True  # или False в зависимости от требований
            )

            self.stdout.write(self.style.SUCCESS(f'Successfully created user {username}'))
