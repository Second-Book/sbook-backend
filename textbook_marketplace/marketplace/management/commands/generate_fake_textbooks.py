import os
import random
from django.core.management.base import BaseCommand
from faker import Faker
from marketplace.models import Textbook
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.exceptions import SuspiciousFileOperation
from django.utils.text import slugify
from django.core.files.storage import default_storage


User = get_user_model()


class Command(BaseCommand):
    help = 'Generate fake textbooks with images from the sample_images folder and save them in the media directory'

    def add_arguments(self, parser):
        parser.add_argument('count', type=int, help='Number of textbooks to generate')

    def handle(self, *args, **options):
        count = options['count']
        fake = Faker()

        # Путь к папке с изображениями
        image_folder = os.path.join(settings.BASE_DIR, 'marketplace', 'sample_images')

        # Получаем список файлов в папке, но проверяем, что путь безопасен
        image_files = []
        for filename in os.listdir(image_folder):
            full_path = os.path.join(image_folder, filename)
            real_path = os.path.realpath(full_path)  # Получаем абсолютный путь
            # Проверяем, что файл действительно находится внутри этой папки
            if os.path.isfile(full_path) and real_path.startswith(os.path.abspath(image_folder)):
                image_files.append(filename)
            else:
                self.stdout.write(self.style.WARNING(f"Skipping suspicious file: {filename}"))

        # Проверяем, что в папке есть изображения
        if not image_files:
            self.stdout.write(self.style.ERROR('No valid images found in the sample_images folder!'))
            return

        # Получаем случайных пользователей, которые будут продавцами учебников
        users = User.objects.filter(is_seller=True)

        if not users:
            self.stdout.write(self.style.ERROR('No sellers found! Please ensure you have sellers in the system.'))
            return

        for _ in range(count):
            title = fake.bs()  # Генерация случайного названия учебника
            author = fake.name()  # Случайное имя автора
            school_class = f'{random.randint(1, 11)}'  # Случайный класс от 1 до 11
            publisher = fake.company()  # Генерация названия издательства
            subject = random.choice(
                ['Mathematics', 'Serbian', 'English', 'History', 'Biology',
                 'Geography', 'Physics', 'Chemistry']
            )
            price = random.uniform(5, 100)  # Случайная цена учебника
            seller = random.choice(users)  # Случайный продавец
            description = fake.text()  # Описание учебника
            whatsapp_contact = fake.phone_number()  # Контакт в WhatsApp
            viber_contact = fake.phone_number()  # Контакт в Viber
            telegram_contact = fake.phone_number()  # Контакт в Telegram
            phone_contact = fake.phone_number()  # Простой номер телефона
            condition = random.choice(['New', 'Used - Excellent', 'Used - Good', 'Used - Fair'])  # Состояние учебника

            # Случайным образом выбираем изображение из папки
            selected_image_file = random.choice(image_files)
            image_path = os.path.join(image_folder, selected_image_file)

            # Новый путь в директории media
            media_image_path = os.path.join('textbook_images', selected_image_file)

            # Копируем изображение в директорию media с помощью default_storage
            try:
                # Сохраняем изображение с помощью default_storage
                with open(image_path, 'rb') as image_file:
                    django_file = File(image_file)
                    image_name = slugify(selected_image_file)  # Убираем пробелы и спецсимволы

                    # Сохраняем файл в директорию media/textbook_images/ автоматически
                    saved_image = default_storage.save(os.path.join('textbook_images', image_name), django_file)

                    # Создаем учебник с изображением
                    textbook = Textbook.objects.create(
                        title=title,
                        author=author,
                        school_class=school_class,
                        publisher=publisher,
                        subject=subject,
                        price=price,
                        seller=seller,
                        description=description,
                        whatsapp_contact=whatsapp_contact,
                        viber_contact=viber_contact,
                        telegram_contact=telegram_contact,
                        phone_contact=phone_contact,
                        condition=condition,
                        image=saved_image  # Ссылка на сохранённое изображение
                    )

                self.stdout.write(self.style.SUCCESS(f'Successfully created textbook "{title}" with image {saved_image}'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing image {selected_image_file}: {str(e)}"))
