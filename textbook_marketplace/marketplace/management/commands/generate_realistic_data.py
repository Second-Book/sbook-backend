"""
Management command to generate realistic test data for the textbook marketplace.

This command creates:
- 40-50 users (60% sellers, 40% buyers)
- 100 textbooks with realistic Serbian textbook data
- 80-100 messages between users
- 5-8 user blocks
- 3-5 reports
- 10-15 orders

Usage:
    python manage.py generate_realistic_data
    python manage.py generate_realistic_data --textbooks 150  # Custom textbook count
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
from django.conf import settings
from faker import Faker
from faker.providers import BaseProvider

from marketplace.models import Textbook, Block, Report, Order
from chat.models import Message

User = get_user_model()


class SerbianTextbookProvider(BaseProvider):
    """Custom Faker provider for Serbian textbook data."""

    # Realistic Serbian textbook subjects
    subjects = [
        'Matematika', 'Srpski jezik', 'Engleski jezik', 'Istorija',
        'Biologija', 'Geografija', 'Fizika', 'Hemija', 'Informatika',
        'Muzička kultura', 'Likovna kultura', 'Fizičko vaspitanje',
        'Nemački jezik', 'Francuski jezik', 'Ruski jezik', 'Latinski jezik',
        'Filozofija', 'Sociologija', 'Psihologija', 'Ekonomija',
        'Pravni sistem', 'Tehnička kultura'
    ]

    # Realistic Serbian publishers
    publishers = [
        'Klett', 'Zavod za udžbenike', 'Zavod za udžbenike i nastavna sredstva',
        'Eduka', 'Logos', 'Bigz', 'Narodna knjiga', 'Alfa', 'Prosveta',
        'Zavod za izdavanje udžbenika', 'Kreativni centar', 'Mladost',
        'Školska knjiga', 'Znanje', 'Mozaik knjiga'
    ]

    # Realistic textbook titles by subject
    textbook_titles = {
        'Matematika': [
            'Matematika za {grade}. razred', 'Matematika - Zbirka zadataka',
            'Matematika - Radna sveska', 'Matematika - Priručnik'
        ],
        'Srpski jezik': [
            'Srpski jezik za {grade}. razred', 'Srpski jezik - Čitanka',
            'Srpski jezik - Gramatika', 'Srpski jezik - Pravopis'
        ],
        'Engleski jezik': [
            'English for {grade} Grade', 'English Grammar',
            'English Reader', 'English Workbook'
        ],
        'Istorija': [
            'Istorija za {grade}. razred', 'Istorija Srbije',
            'Istorija - Atlas', 'Istorija - Hronologija'
        ],
        'Biologija': [
            'Biologija za {grade}. razred', 'Biologija - Praktikum',
            'Biologija - Atlas', 'Biologija - Zbirka zadataka'
        ],
        'Geografija': [
            'Geografija za {grade}. razred', 'Geografija - Atlas',
            'Geografija Srbije', 'Geografija - Radna sveska'
        ],
        'Fizika': [
            'Fizika za {grade}. razred', 'Fizika - Zbirka zadataka',
            'Fizika - Praktikum', 'Fizika - Priručnik'
        ],
        'Hemija': [
            'Hemija za {grade}. razred', 'Hemija - Zbirka zadataka',
            'Hemija - Praktikum', 'Hemija - Priručnik'
        ],
    }

    # Realistic Serbian author names
    authors = [
        'Milan Petrović', 'Jovan Jovanović', 'Ana Stojanović', 'Marko Nikolić',
        'Jelena Đorđević', 'Stefan Popović', 'Milica Radović', 'Nikola Marković',
        'Sara Jović', 'Luka Stanković', 'Maja Ilić', 'Đorđe Milić',
        'Tijana Pavlović', 'Nemanja Lazić', 'Ivana Todorović', 'Filip Đukić',
        'Jovana Stojković', 'Aleksandar Ristić', 'Teodora Vasić', 'Lazar Živković'
    ]

    def serbian_subject(self):
        return self.random_element(self.subjects)

    def serbian_publisher(self):
        return self.random_element(self.publishers)

    def serbian_textbook_title(self, subject: str, grade: int):
        titles = self.textbook_titles.get(subject, [
            f'{subject} za {grade}. razred',
            f'{subject} - Priručnik',
            f'{subject} - Zbirka zadataka'
        ])
        title_template = self.random_element(titles)
        return title_template.format(grade=grade)

    def serbian_author(self):
        return self.random_element(self.authors)

    def serbian_phone_number(self):
        """Generate realistic Serbian phone number."""
        prefixes = ['060', '061', '062', '063', '064', '065', '066']
        prefix = self.random_element(prefixes)
        number = ''.join([str(random.randint(0, 9)) for _ in range(7)])
        return f'{prefix}{number}'

    def serbian_telegram_contact(self):
        """Generate realistic Telegram username."""
        return f'@{self.generator.user_name()}'

    def serbian_description(self):
        """Generate realistic textbook description in Serbian."""
        descriptions = [
            'Udobro stanje, malo korišćeno. Bez napomena i beleški.',
            'Odlično očuvana knjiga, kao nova. Bez oštećenja.',
            'Korišćena knjiga u dobrom stanju. Ima nekoliko beleški olovkom.',
            'Knjiga je u dobrom stanju, ima nekoliko podvlačenja markerom.',
            'Korišćena, ali funkcionalna. Ima nekoliko oštećenih stranica.',
            'Knjiga je u odličnom stanju, bez napomena.',
            'Malo korišćena, bez oštećenja. Idealna za učenje.',
            'Korišćena knjiga u dobrom stanju. Ima nekoliko podvlačenja.',
            'Knjiga je kao nova, nikad korišćena.',
            'Udobro stanje, ima nekoliko beleški na marginama.'
        ]
        return self.random_element(descriptions)


class Command(BaseCommand):
    help = 'Generate realistic test data for the textbook marketplace'

    def add_arguments(self, parser):
        parser.add_argument(
            '--textbooks',
            type=int,
            default=100,
            help='Number of textbooks to generate (default: 100)'
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
        fake.add_provider(SerbianTextbookProvider)

        textbooks_count = options['textbooks']
        users_count = options['users']
        skip_users = options['skip_users']

        self.stdout.write(self.style.SUCCESS('Starting data generation...'))

        # Step 1: Generate users
        if not skip_users:
            existing_users = User.objects.count()
            if users_count == 0:
                # Auto-calculate: need enough sellers for textbooks
                # Assume each seller has 2-5 textbooks on average
                users_count = max(40, textbooks_count // 3)
            
            sellers_needed = int(users_count * 0.6)  # 60% sellers
            buyers_count = users_count - sellers_needed
            
            self.stdout.write(f'Generating {users_count} users ({sellers_needed} sellers, {buyers_count} buyers)...')
            users = self._generate_users(fake, sellers_needed, buyers_count)
            self.stdout.write(self.style.SUCCESS(f'✓ Generated {len(users)} users'))
        else:
            users = list(User.objects.all())
            if not users:
                self.stdout.write(self.style.ERROR('No users found! Use --skip-users=false to generate users.'))
                return
            self.stdout.write(self.style.SUCCESS(f'✓ Using {len(users)} existing users'))

        sellers = [u for u in users if u.is_seller]
        if not sellers:
            self.stdout.write(self.style.ERROR('No sellers found! Cannot generate textbooks.'))
            return

        # Step 2: Generate textbooks
        self.stdout.write(f'Generating {textbooks_count} textbooks...')
        textbooks = self._generate_textbooks(fake, textbooks_count, sellers)
        self.stdout.write(self.style.SUCCESS(f'✓ Generated {len(textbooks)} textbooks'))

        # Step 3: Generate messages
        messages_count = random.randint(80, 100)
        self.stdout.write(f'Generating {messages_count} messages...')
        messages = self._generate_messages(fake, messages_count, users)
        self.stdout.write(self.style.SUCCESS(f'✓ Generated {len(messages)} messages'))

        # Step 4: Generate blocks
        blocks_count = random.randint(5, 8)
        self.stdout.write(f'Generating {blocks_count} user blocks...')
        blocks = self._generate_blocks(blocks_count, users)
        self.stdout.write(self.style.SUCCESS(f'✓ Generated {len(blocks)} blocks'))

        # Step 5: Generate reports
        reports_count = random.randint(3, 5)
        self.stdout.write(f'Generating {reports_count} reports...')
        reports = self._generate_reports(fake, reports_count, users)
        self.stdout.write(self.style.SUCCESS(f'✓ Generated {len(reports)} reports'))

        # Step 6: Generate orders
        orders_count = random.randint(10, 15)
        self.stdout.write(f'Generating {orders_count} orders...')
        orders = self._generate_orders(orders_count, textbooks, users)
        self.stdout.write(self.style.SUCCESS(f'✓ Generated {len(orders)} orders'))

        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('Data generation completed!'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Users: {User.objects.count()}')
        self.stdout.write(f'Textbooks: {Textbook.objects.count()}')
        self.stdout.write(f'Messages: {Message.objects.count()}')
        self.stdout.write(f'Blocks: {Block.objects.count()}')
        self.stdout.write(f'Reports: {Report.objects.count()}')
        self.stdout.write(f'Orders: {Order.objects.count()}')

    def _generate_users(self, fake: Faker, sellers_count: int, buyers_count: int):
        """Generate users with realistic Serbian data."""
        users = []
        
        for _ in range(sellers_count):
            username = fake.unique.user_name()
            email = fake.unique.email()
            user = User.objects.create_user(
                username=username,
                email=email,
                password='password123',  # Default password for testing
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                telegram_id=fake.uuid4()[:20],
                telephone=fake.serbian_phone_number(),
                is_seller=True,
                is_active=True
            )
            users.append(user)

        for _ in range(buyers_count):
            username = fake.unique.user_name()
            email = fake.unique.email()
            user = User.objects.create_user(
                username=username,
                email=email,
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

    def _generate_textbooks(self, fake: Faker, count: int, sellers: list):
        """Generate textbooks with realistic Serbian data."""
        textbooks = []
        
        # Get sample images if available
        image_folder = os.path.join(settings.BASE_DIR, 'marketplace', 'sample_images')
        image_files = []
        if os.path.exists(image_folder):
            for filename in os.listdir(image_folder):
                full_path = os.path.join(image_folder, filename)
                if os.path.isfile(full_path) and filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    image_files.append(full_path)

        for i in range(count):
            subject = fake.serbian_subject()
            grade = random.randint(1, 12)
            title = fake.serbian_textbook_title(subject, grade)
            author = fake.serbian_author()
            publisher = fake.serbian_publisher()
            
            # Realistic price range: 500-5000 RSD (approximately 5-50 EUR)
            price = round(random.uniform(500, 5000), 2)
            
            seller = random.choice(sellers)
            description = fake.serbian_description()
            
            # Contact info (not all sellers provide all contacts)
            whatsapp = fake.serbian_phone_number() if random.random() > 0.2 else None
            viber = fake.serbian_phone_number() if random.random() > 0.3 else None
            telegram = fake.serbian_telegram_contact() if random.random() > 0.25 else None
            phone = fake.serbian_phone_number() if random.random() > 0.1 else None
            
            condition = random.choices(
                ['New', 'Used - Excellent', 'Used - Good', 'Used - Fair'],
                weights=[5, 25, 50, 20]  # Most books are "Used - Good"
            )[0]

            # Handle image
            image = None
            if image_files:
                try:
                    selected_image = random.choice(image_files)
                    with open(selected_image, 'rb') as img_file:
                        django_file = File(img_file)
                        image_name = f"{slugify(title)}_{i}_{os.path.basename(selected_image)}"
                        saved_image = default_storage.save(
                            os.path.join('textbook_images', image_name),
                            django_file
                        )
                        image = saved_image
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Could not attach image to textbook {i+1}: {str(e)}')
                    )

            textbook = Textbook.objects.create(
                title=title,
                author=author,
                school_class=str(grade),
                publisher=publisher,
                subject=subject,
                price=price,
                seller=seller,
                description=description,
                whatsapp_contact=whatsapp,
                viber_contact=viber,
                telegram_contact=telegram,
                phone_contact=phone,
                condition=condition,
                image=image
            )
            textbooks.append(textbook)

            if (i + 1) % 20 == 0:
                self.stdout.write(f'  Generated {i + 1}/{count} textbooks...')

        return textbooks

    def _generate_messages(self, fake: Faker, count: int, users: list):
        """Generate messages between users."""
        messages = []
        
        # Create some conversation threads
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
            'Možemo li se naći u centru grada?'
        ]

        for i in range(count):
            if conversations and random.random() > 0.3:
                # Continue existing conversation
                sender, recipient = random.choice(conversations)
                if random.random() > 0.5:
                    sender, recipient = recipient, sender  # Alternate sender
            else:
                # New conversation
                sender, recipient = random.sample(users, 2)
                conversations.append((sender, recipient))

            text = random.choice(message_texts)
            
            # Some messages are seen, some are not
            seen = random.random() > 0.4
            
            # Random time in the last 30 days
            sent_at = timezone.now() - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )

            message = Message.objects.create(
                sender=sender,
                recipient=recipient,
                text=text,
                seen=seen,
                sent_at=sent_at
            )
            messages.append(message)

        return messages

    def _generate_blocks(self, count: int, users: list):
        """Generate user blocks."""
        blocks = []
        existing_blocks = set()

        for _ in range(count):
            user1, user2 = random.sample(users, 2)
            block_key = tuple(sorted([user1.id, user2.id]))
            
            if block_key in existing_blocks:
                continue
            
            # Check if block already exists
            if Block.objects.filter(
                initiator_user=user1,
                blocked_user=user2
            ).exists() or Block.objects.filter(
                initiator_user=user2,
                blocked_user=user1
            ).exists():
                continue

            block = Block.objects.create(
                initiator_user=user1,
                blocked_user=user2
            )
            blocks.append(block)
            existing_blocks.add(block_key)

        return blocks

    def _generate_reports(self, fake: Faker, count: int, users: list):
        """Generate user reports."""
        reports = []
        
        report_topics = [
            'Neprikladno ponašanje',
            'Lažna reklama',
            'Spam poruke',
            'Nepoštovanje dogovora',
            'Uvredljive poruke'
        ]

        for _ in range(count):
            reporter = random.choice(users)
            reported = random.choice([u for u in users if u != reporter])
            
            topic = random.choice(report_topics)
            description = fake.text(max_nb_chars=200)

            report = Report.objects.create(
                user=reporter,
                user_reported=reported,
                topic=topic,
                description=description
            )
            reports.append(report)

        return reports

    def _generate_orders(self, count: int, textbooks: list, users: list):
        """Generate orders."""
        orders = []
        
        # Only buyers can make orders
        buyers = [u for u in users if not u.is_seller]
        if not buyers:
            self.stdout.write(self.style.WARNING('No buyers found, skipping order generation'))
            return []

        for _ in range(count):
            textbook = random.choice(textbooks)
            buyer = random.choice(buyers)
            
            # Don't allow users to order their own textbooks
            if buyer == textbook.seller:
                continue

            quantity = random.randint(1, 3)
            
            # Random order date in the last 60 days
            order_date = timezone.now() - timedelta(
                days=random.randint(0, 60),
                hours=random.randint(0, 23)
            )

            order = Order.objects.create(
                textbook=textbook,
                quantity=quantity,
                order_date=order_date
            )
            orders.append(order)

        return orders

