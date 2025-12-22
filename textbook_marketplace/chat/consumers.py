from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from django.contrib.auth import get_user_model
from django.db.models import Q, ObjectDoesNotExist

import json
from typing import List

from .models import Message
from .serializers import MessageSerializer
from marketplace.models import Block

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """ Consumer for chat system. """

    async def connect(self):
        """ Adds connection to channel layer. """
        self.user: User = self.scope['user']
        if not self.user.is_authenticated:
            await self.close(code=4003)
            return
        self.room_group_name: str = f'personal_{self.user.username}'
        await self.channel_layer.group_add(channel=self.channel_name,
                                           group=self.room_group_name)
        await self.accept()
        unseen_messages: List[Message] = await self.retrieve_unseen_messages(
            self.user
        )
        await self.send(text_data=json.dumps(
            {'type': 'notification',
             'new_messages': unseen_messages}
        ))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(channel=self.channel_name,
                                               group=self.room_group_name)

    @database_sync_to_async
    def retrieve_unseen_messages(self, user: User) -> List[Message]:
        query = user.message_recipient.filter(seen=False)
        serializer = MessageSerializer(query, many=True)
        return serializer.data

    @database_sync_to_async
    def save_message(self, text: str, recipient: User) -> None:
        """ Creates message in db. """
        message: Message = Message.objects.create(text=text,
                                                  sender=self.user,
                                                  recipient=recipient)
        message.save()

    @database_sync_to_async
    def is_blocked(self, recipient: User) -> bool:
        """Check if sender blocked recipient OR recipient blocked sender."""
        return Block.objects.filter(
            Q(initiator_user=recipient, blocked_user=self.user) |
            Q(initiator_user=self.user, blocked_user=recipient)
        ).exists()

    @staticmethod
    @database_sync_to_async
    def get_user_by_username(username: str) -> User | None:
        try:
            return User.objects.get(username=username)
        except ObjectDoesNotExist:
            return None

    async def receive(self, text_data: str):
        """ Receives message, then sends it to the group and calls
        save_message() method if self.user is allowed to send messages.
        Just sends notification about block otherwise. """
        text_data_json: dict[str: str] = json.loads(text_data)
        message: str = text_data_json['message']
        recipient_username: str = text_data_json['recipient']
        recipient = await self.get_user_by_username(username=recipient_username)
        
        if recipient is None:
            await self.send(text_data=json.dumps(
                {'type': 'error',
                 'message': f'No such user found with username '
                            f'{recipient_username}.',
                 'sender': self.user.username}
            ))
            return
        
        if await self.is_blocked(recipient):
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'You cannot message this user due to a block.',
                'sender': self.user.username
            }))
            return
        
        await self.save_message(text=message,
                                recipient=recipient)

        # send message to recipient ws room
        await self.channel_layer.group_send(
            f'personal_{recipient_username}',
            {'type': 'chat_message',
             'message': message,
             'sender': self.user.username,
             'recipient': recipient_username,
             }
        )
        await self.send(text_data=json.dumps(
                {'type': 'message',
                 'message': message,
                 'sender': self.user.username,
                 'recipient': recipient_username,
                 }
            ))

    async def chat_message(self, event) -> None:
        """ Sends chat message to user in group. """
        message: str = event['message']
        sender: str = event['sender']
        recipient: str = event['recipient']

        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': message,
            'sender': sender,
            'recipient': recipient
        }))
