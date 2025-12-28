from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from faker import Faker
import random

from chat.models import Message


User = get_user_model()


class Command(BaseCommand):
    help = 'Generate fake messages with specified count'

    def add_arguments(self, parser):
        parser.add_argument('count', type=int, help='Number of messages to generate')

    def handle(self, *args, **options):
        def get_two_users() -> tuple[User, User]:
            last = User.objects.count() - 1
            if last < 2:
                raise ValueError('No users in db to generate messages')
            index1 = random.randint(0, last)
            index2 = random.randint(0, last - 1)

            if index2 == index1:
                index2 = last

            return User.objects.all()[index1], User.objects.all()[index2]

        count = options['count']
        fake = Faker()

        for _ in range(count):
            sender, recipient = get_two_users()
            text: str = fake.text(max_nb_chars=255)

            message_obj: Message = Message.objects.create(
                sender=sender,
                recipient=recipient,
                text=text
            )

            self.stdout.write(self.style.SUCCESS(
                f'Successfully created message {message_obj.pk} '
                f'between {sender.username} and {recipient.username}'))