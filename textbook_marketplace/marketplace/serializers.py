from django.shortcuts import get_object_or_404
from rest_framework import serializers
from django.core.validators import MinValueValidator, MaxValueValidator

from django.contrib.auth import get_user_model

from .models import Textbook, Order, Report
from versatileimagefield.serializers import VersatileImageFieldSerializer
from django.conf import settings
from urllib.parse import urljoin
import bleach


class AbsoluteVersatileImageFieldSerializer(VersatileImageFieldSerializer):
    def to_representation(self, value):
        data = super().to_representation(value)
        if isinstance(data, dict):
            return {
                key: urljoin(settings.MEDIA_HOST, url)
                for key, url in data.items()
            }
        return data


User = get_user_model()


class TextbookSerializer(serializers.ModelSerializer):
    seller = serializers.ReadOnlyField(source='seller.username')
    image = AbsoluteVersatileImageFieldSerializer(sizes='marketplace')
    price = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0.01), MaxValueValidator(99999.99)]
    )

    class Meta:
        model = Textbook
        fields = '__all__'
    
    def validate_description(self, value):
        # Sanitize HTML/XSS
        if value:
            return bleach.clean(value, tags=[], strip=True)
        return value
        
    def create(self, validated_data):
        # seller is passed via serializer.save(seller=...) in perform_create
        # In DRF, kwargs passed to save() are available in validated_data
        # But seller might already be in validated_data, so we need to handle it properly
        # The perform_create method passes seller via save(), which should set it correctly
        # If seller is in validated_data, use it; otherwise it should come from context
        seller = validated_data.pop('seller', None)
        if seller is None:
            request = self.context.get('request')
            if request and hasattr(request, 'user'):
                seller = request.user
        if seller is None:
            raise ValueError("seller is required")
        textbook = Textbook.objects.create(seller=seller, **validated_data)
        return textbook


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                  'telegram_id', 'telephone', 'is_seller', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class SignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class OrderSerializer(serializers.ModelSerializer):
    buyer = serializers.ReadOnlyField(source='buyer.username')
    textbook = serializers.ReadOnlyField(source='textbook.title')

    class Meta:
        model = Order
        fields = '__all__'


class ReportSerializer(serializers.ModelSerializer):
    user_reported = serializers.CharField()
    topic = serializers.CharField()
    description = serializers.CharField()

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        reported_username = validated_data.pop('user_reported', '')
        reported_user = get_object_or_404(User, username=reported_username)
        report = Report.objects.create(
            user=user, user_reported=reported_user, **validated_data
        )
        return report

    class Meta:
        model = Report
        fields = ['user_reported', 'topic', 'description', 'created_at']

