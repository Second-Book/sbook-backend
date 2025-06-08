from django.shortcuts import get_object_or_404
from rest_framework import serializers

from django.contrib.auth import get_user_model

from .models import Textbook, Order, Report
from versatileimagefield.serializers import VersatileImageFieldSerializer
from django.conf import settings
from urllib.parse import urljoin


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


    class Meta:
        model = Textbook
        fields = '__all__'
        
    def create(self, validated_data):
        request = self.context.get('request')
        seller = request.user
        textbook = Textbook.objects.create(seller=seller, **validated_data)
        return textbook


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'


class SignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

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

