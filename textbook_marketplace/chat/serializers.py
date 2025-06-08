from rest_framework import serializers

from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    text = serializers.CharField(max_length=255)

    class Meta:
        model = Message
        fields = ['sender', 'recipient', 'text', 'sent_at']
