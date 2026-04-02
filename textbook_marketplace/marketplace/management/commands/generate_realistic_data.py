"""
Management command to generate realistic test data for the textbook marketplace.

Uses a YAML fixture (marketplace/fixtures/textbooks.yaml) that maps real textbook
cover images to metadata. Creates 5 listings per image with varied titles/descriptions.

Usage:
    python manage.py generate_realistic_data
    python manage.py generate_realistic_data --listings-per-image 3
"""

import os
import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.files.storage import default_storage
from django.utils import timezone
from django.utils.text import slugify
from faker import Faker
from faker.providers import BaseProvider

import yaml

from marketplace.models import Textbook, Block, Report, Order
from chat.models import Message

User = get_user_model()

FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'fixtures'
)


class SerbianContactProvider(BaseProvider):
    """Custom Faker provider for Serbian contact data."""

    authors = [
        'Milan Petrović', 'Jovan Jovanović', 'Ana Stojanović', 'Marko Nikolić',
        'Jelena Đorđević', 'Stefan Popović', 'Milica Radović', 'Nikola Marković',
        'Sara Jović', 'Luka Stanković', 'Maja Ilić', 'Đorđe Milić',
        'Tijana Pavlović', 'Nemanja Lazić', 'Ivana Todorović', 'Filip Đukić',
        'Jovana Stojković', 'Aleksandar Ristić', 'Teodora Vasić', 'Lazar Živković'
    ]

    def serbian_phone_number(self):
        prefixes = ['060', '061', '062', '063', '064', '065', '066']
        prefix = self.random_element(prefixes)
        number = ''.join([str(random.randint(0, 9)) for _ in range(7)])
        return f'{prefix}{number}'

    def serbian_telegram_contact(self):
        return f'@{self.generator.user_name()}'

    def serbian_author(self):
        return self.random_element(self.authors)


class Command(BaseCommand):
    help = 'Generate realistic test data from textbook image fixtures'

    def add_arguments(self, parser):
        parser.add_argument(
            '--listings-per-image',
            type=int,
            default=5,
            help='Number of listings per textbook image (default: 5)'
        )
        parser.add_argument(
            '--users',
            type=int,
            default=0,
            help='Number of users to generate (default: auto-calculated)'
        )
        parser.add_argument(
            '--skip-users',
            action='store_true',
            help='Skip user generation if users already exist'
        )

    def handle(self, *args, **options):
        fake = Faker(['en_US'])
        fake.add_provider(SerbianContactProvider)

        listings_per_image = options['listings_per_image']
        users_count = options['users']
        skip_users = options['skip_users']

        # Load fixture
        fixture_path = os.path.join(FIXTURES_DIR, 'textbooks.yaml')
        if not os.path.exists(fixture_path):
            self.stderr.write(self.style.ERROR(
                f'Fixture not found: {fixture_path}\n'
                f'Expected YAML fixture at marketplace/fixtures/textbooks.yaml'
            ))
            return

        with open(fixture_path, 'r', encoding='utf-8') as f:
            fixture = yaml.safe_load(f)

        textbook_entries = fixture['textbooks']
        descriptions = fixture['descriptions']
        total_textbooks = len(textbook_entries) * listings_per_image

        self.stdout.write(self.style.SUCCESS('Starting data generation from fixture...'))
        self.stdout.write(f'  {len(textbook_entries)} textbook images x {listings_per_image} listings = {total_textbooks} textbooks')

        # Step 1: Generate users
        if not skip_users:
            if users_count == 0:
                users_count = max(40, total_textbooks // 3)

            sellers_needed = int(users_count * 0.6)
            buyers_count = users_count - sellers_needed

            self.stdout.write(f'Generating {users_count} users ({sellers_needed} sellers, {buyers_count} buyers)...')
            users = self._generate_users(fake, sellers_needed, buyers_count)
            self.stdout.write(self.style.SUCCESS(f'  Generated {len(users)} users'))
        else:
            users = list(User.objects.all())
            if not users:
                self.stderr.write(self.style.ERROR('No users found! Remove --skip-users to generate users.'))
                return
            self.stdout.write(self.style.SUCCESS(f'  Using {len(users)} existing users'))

        sellers = [u for u in users if u.is_seller]
        if not sellers:
            self.stderr.write(self.style.ERROR('No sellers found! Cannot generate textbooks.'))
            return

        # Step 2: Generate textbooks from fixture
        self.stdout.write(f'Generating {total_textbooks} textbooks from fixture...')
        textbooks = self._generate_textbooks(fake, textbook_entries, descriptions, listings_per_image, sellers)
        self.stdout.write(self.style.SUCCESS(f'  Generated {len(textbooks)} textbooks'))

        # Step 3: Generate messages
        messages_count = random.randint(80, 100)
        self.stdout.write(f'Generating {messages_count} messages...')
        messages = self._generate_messages(fake, messages_count, users)
        self.stdout.write(self.style.SUCCESS(f'  Generated {len(messages)} messages'))

        # Step 4: Generate blocks
        blocks_count = random.randint(5, 8)
        self.stdout.write(f'Generating {blocks_count} user blocks...')
        blocks = self._generate_blocks(blocks_count, users)
        self.stdout.write(self.style.SUCCESS(f'  Generated {len(blocks)} blocks'))

        # Step 5: Generate reports
        reports_count = random.randint(3, 5)
        self.stdout.write(f'Generating {reports_count} reports...')
        reports = self._generate_reports(fake, reports_count, users)
        self.stdout.write(self.style.SUCCESS(f'  Generated {len(reports)} reports'))

        # Step 6: Generate orders
        orders_count = random.randint(10, 15)
        self.stdout.write(f'Generating {orders_count} orders...')
        orders = self._generate_orders(orders_count, textbooks, users)
        self.stdout.write(self.style.SUCCESS(f'  Generated {len(orders)} orders'))

        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 50))
        self.stdout.write(self.style.SUCCESS('Data generation completed!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(f'Users: {User.objects.count()}')
        self.stdout.write(f'Textbooks: {Textbook.objects.count()}')
        self.stdout.write(f'Messages: {Message.objects.count()}')
        self.stdout.write(f'Blocks: {Block.objects.count()}')
        self.stdout.write(f'Reports: {Report.objects.count()}')
        self.stdout.write(f'Orders: {Order.objects.count()}')

    def _generate_users(self, fake, sellers_count, buyers_count):
        users = []

        for _ in range(sellers_count):
            user = User.objects.create_user(
                username=fake.unique.user_name(),
                email=fake.unique.email(),
                password='password123',
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                telegram_id=fake.uuid4()[:20],
                telephone=fake.serbian_phone_number(),
                is_seller=True,
                is_active=True
            )
            users.append(user)

        for _ in range(buyers_count):
            user = User.objects.create_user(
                username=fake.unique.user_name(),
                email=fake.unique.email(),
                password='password123',
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                telegram_id=fake.uuid4()[:20] if random.random() > 0.3 else None,
                telephone=fake.serbian_phone_number() if random.random() > 0.2 else None,
                is_seller=False,
                is_active=True
            )
            users.append(user)

        return users

    def _generate_textbooks(self, fake, textbook_entries, descriptions, listings_per_image, sellers):
        textbooks = []
        images_dir = os.path.join(FIXTURES_DIR, 'textbook_images')
        counter = 0

        for entry in textbook_entries:
            image_filename = entry['image']
            image_path = os.path.join(images_dir, image_filename)

            if not os.path.exists(image_path):
                self.stdout.write(self.style.WARNING(f'  Image not found, skipping: {image_filename}'))
                continue

            title_variants = entry['title_variants']

            for i in range(listings_per_image):
                title = title_variants[i % len(title_variants)]
                seller = random.choice(sellers)
                description = random.choice(descriptions)
                price = round(random.uniform(300, 3000), 2)

                condition = random.choices(
                    ['New', 'Used - Excellent', 'Used - Good', 'Used - Fair'],
                    weights=[5, 25, 50, 20]
                )[0]

                # Contact info
                whatsapp = fake.serbian_phone_number() if random.random() > 0.2 else None
                viber = fake.serbian_phone_number() if random.random() > 0.3 else None
                telegram = fake.serbian_telegram_contact() if random.random() > 0.25 else None
                phone = fake.serbian_phone_number() if random.random() > 0.1 else None

                # Copy image
                image = None
                try:
                    with open(image_path, 'rb') as img_file:
                        django_file = File(img_file)
                        ext = os.path.splitext(image_filename)[1]
                        safe_name = f"{slugify(title)}_{counter}{ext}"
                        saved_image = default_storage.save(
                            os.path.join('textbook_images', safe_name),
                            django_file
                        )
                        image = saved_image
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Could not attach image: {e}'))

                textbook = Textbook.objects.create(
                    title=title,
                    author=fake.serbian_author(),
                    school_class=entry['school_class'],
                    publisher=entry['publisher'],
                    subject=entry['subject'],
                    price=price,
                    seller=seller,
                    description=description,
                    whatsapp_contact=whatsapp,
                    viber_contact=viber,
                    telegram_contact=telegram,
                    phone_contact=phone,
                    condition=condition,
                    image=image,
                )
                textbooks.append(textbook)
                counter += 1

            if counter % 20 == 0:
                self.stdout.write(f'  Generated {counter} textbooks...')

        return textbooks

    def _generate_messages(self, fake, count, users):
        messages = []
        conversations = []
        for _ in range(count // 3):
            user1, user2 = random.sample(users, 2)
            conversations.append((user1, user2))

        message_texts = [
            'Zdravo, da li je još uvek dostupna knjiga?',
            'Interesuje me ova knjiga. Možemo li se dogovoriti?',
            'Koliko košta dostava?',
            'Gde se možemo naći?',
            'Da li mogu da vidim još slika knjige?',
            'Hvala, knjiga je odlična!',
            'Kada bi mogao da preuzmem knjigu?',
            'Da li prihvatate rezervaciju?',
            'Možemo li se naći sutra?',
            'Hvala na odgovoru!',
            'Da li je knjiga u dobrom stanju?',
            'Interesuje me, možemo li se dogovoriti za cenu?',
            'Kada je najranije moguće preuzeti?',
            'Hvala, knjiga je tačno onako kako ste opisali.',
            'Možemo li se naći u centru grada?',
        ]

        for _ in range(count):
            if conversations and random.random() > 0.3:
                sender, recipient = random.choice(conversations)
                if random.random() > 0.5:
                    sender, recipient = recipient, sender
            else:
                sender, recipient = random.sample(users, 2)
                conversations.append((sender, recipient))

            message = Message.objects.create(
                sender=sender,
                recipient=recipient,
                text=random.choice(message_texts),
                seen=random.random() > 0.4,
                sent_at=timezone.now() - timedelta(
                    days=random.randint(0, 30),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                ),
            )
            messages.append(message)

        return messages

    def _generate_blocks(self, count, users):
        blocks = []
        existing = set()

        for _ in range(count):
            user1, user2 = random.sample(users, 2)
            key = tuple(sorted([user1.id, user2.id]))

            if key in existing:
                continue
            if Block.objects.filter(
                initiator_user=user1, blocked_user=user2
            ).exists() or Block.objects.filter(
                initiator_user=user2, blocked_user=user1
            ).exists():
                continue

            block = Block.objects.create(initiator_user=user1, blocked_user=user2)
            blocks.append(block)
            existing.add(key)

        return blocks

    def _generate_reports(self, fake, count, users):
        reports = []
        topics = [
            'Neprikladno ponašanje', 'Lažna reklama', 'Spam poruke',
            'Nepoštovanje dogovora', 'Uvredljive poruke',
        ]

        for _ in range(count):
            reporter = random.choice(users)
            reported = random.choice([u for u in users if u != reporter])
            report = Report.objects.create(
                user=reporter,
                user_reported=reported,
                topic=random.choice(topics),
                description=fake.text(max_nb_chars=200),
            )
            reports.append(report)

        return reports

    def _generate_orders(self, count, textbooks, users):
        orders = []
        buyers = [u for u in users if not u.is_seller]
        if not buyers:
            self.stdout.write(self.style.WARNING('No buyers found, skipping orders'))
            return []

        for _ in range(count):
            textbook = random.choice(textbooks)
            buyer = random.choice(buyers)
            if buyer == textbook.seller:
                continue

            order = Order.objects.create(
                textbook=textbook,
                quantity=random.randint(1, 3),
                order_date=timezone.now() - timedelta(
                    days=random.randint(0, 60),
                    hours=random.randint(0, 23)
                ),
            )
            orders.append(order)

        return orders
