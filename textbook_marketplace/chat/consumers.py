from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from django.contrib.auth import get_user_model
from django.db.models import Q

import json
from typing import Any

from .models import Message
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
        self.room_name: str = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name: str = f'chat_{self.room_name}'
        await self.channel_layer.group_add(channel=self.channel_name,
                                           group=self.room_group_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(channel=self.channel_name,
                                               group=self.room_group_name)

    @database_sync_to_async
    def save_message(self, text: str, recipient: User) -> None:
        """ Creates message in db. """
        message: Message = Message.objects.create(text=text,
                                                  sender=self.user,
                                                  recipient=recipient)
        message.save()

    @database_sync_to_async
    def is_blocked_or_get_recipient(self,
                                    recipient_username: str) -> tuple[bool, Any]:
        """ Checks if there is a block between sender and recipient.
        Returns recipient user alongside with bool value if no block found. """
        block_exist = Block.objects.filter(
            Q(initiator_user=self.user) | Q(blocked_user=self.user)
        ).exists()
        if block_exist:
            return True, None
        return False, User.objects.get(username=recipient_username)

    async def receive(self, text_data: str):
        """ Receives message, then sends it to the group and calls
        save_message() method if self.user is allowed to send messages.
        Just sends notification about block otherwise. """
        text_data_json: dict[str: str] = json.loads(text_data)
        message: str = text_data_json['message']
        recipient_username: str = text_data_json['recipient']
        is_blocked, recipient = await self.is_blocked_or_get_recipient(
            recipient_username=recipient_username
        )
        if is_blocked:
            await self.send(text_data=json.dumps(
                {'type': 'notification',
                 'message': 'You cannot message this user due to block.',
                 }))
            return
        await self.save_message(text=message,
                                recipient=recipient)
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'chat_message',
             'message': message,
             'sender': self.user.username,
             'recipient': recipient_username,
             }
        )

    async def chat_message(self, event) -> None:
        """ Sends chat message to all users in group. """
        message: str = event['message']
        sender: str = event['sender']
        recipient: str = event['recipient']

        await self.send(text_data=json.dumps({
            'message': message,
            'sender': sender,
            'recipient': recipient
        }))

    # Called with self.channel_layer.group_send
    async def notification(self, event):
        """ Sends notification only to self.user. """
        message: str = event['message']
        await self.send(text_data=json.dumps({
            'message': message,
        }))
