from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.contrib.auth import get_user_model
from django.db.models import Q

from typing import List

from .models import Message
from .serializers import MessageSerializer

User = get_user_model()


class MessageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """ Returns list of messages request.user is member of. """
        user = request.user
        messages = Message.objects.filter(Q(sender=user) | Q(recipient=user))
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)


class MessageMarkAsSeenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids: List[int] = request.data['ids_to_mark']
        messages = Message.objects.filter(id__in=ids)
        if not messages.exists():
            return Response(status=status.HTTP_304_NOT_MODIFIED)
        for m in messages:
            m.seen = True
        Message.objects.bulk_update(messages, ['seen'])
        return Response(status=status.HTTP_200_OK)

