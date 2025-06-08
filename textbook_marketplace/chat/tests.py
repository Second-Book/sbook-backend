import time

import pytest
from asgiref.sync import async_to_sync, sync_to_async

from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django_channels_jwt_auth_middleware.auth import JWTAuthMiddlewareStack

from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.test import force_authenticate, APIRequestFactory, \
    APIClient

from .routing import websocket_urlpatterns
from .models import Message
from .views import MessageView
from marketplace.models import Block

# TODO rewrite tests from api request factory to api client
User = get_user_model()


@pytest.fixture
def channel_layer():
    yield get_channel_layer()


@pytest.mark.asyncio
async def test_call_group_send_once_success(channel_layer):
    await channel_layer.group_send('channel_1',
                                   {'message': 'message'})


@pytest.mark.asyncio
async def test_call_group_send_twice_success(channel_layer):
    await channel_layer.group_send('channel_1',
                                   {'message': 'message'})
    await channel_layer.group_send('channel_2',
                                   {'message': 'message'})


@pytest.fixture
def first_user() -> User:
    yield User.objects.create(
        username='testusername1', password='testpassword1'
    )


@pytest.fixture
def second_user() -> User:
    yield User.objects.create(
        username='testusername2', password='testpassword2'
    )


@pytest.fixture
def third_user() -> User:
    yield User.objects.create(
        username='testusername3', password='testpassword3'
    )


@pytest.fixture
def client() -> APIClient:
    yield APIClient()


@pytest.fixture
def test_messages(first_user: User,
                  second_user: User,
                  third_user: User) -> tuple:
    msg1 = Message.objects.create(text="hello user2, i'm user1",
                                  sender=first_user,
                                  recipient=second_user)
    msg2 = Message.objects.create(text='hello, user1',
                                  sender=second_user,
                                  recipient=first_user)
    msg3 = Message.objects.create(text='hi',
                                  sender=third_user,
                                  recipient=first_user)
    yield msg1, msg2, msg3


@pytest.fixture(scope='module')
def application() -> JWTAuthMiddlewareStack:
    yield JWTAuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    )


@pytest.mark.asyncio
async def test_websocket_with_token(transactional_db,
                                    application: JWTAuthMiddlewareStack,
                                    first_user: User,
                                    second_user: User):
    chat_url = 'chat/new_test_room/'
    token = AccessToken.for_user(first_user)
    communicator = WebsocketCommunicator(
        application, f'{chat_url}?token={token}'
    )
    connected, subprotocol = await communicator.connect()
    assert connected

    await communicator.send_json_to(
        data={'message': 'test',
              'sender': first_user.username,
              'recipient': second_user.username}
    )
    response: Response = await communicator.receive_json_from()
    assert response['sender'] == 'testusername1'
    assert response['recipient'] == 'testusername2'
    assert response['message'] == 'test'

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_websocket_message_receive_success(
        transactional_db,
        application: JWTAuthMiddlewareStack,
        first_user: User,
        second_user: User):
    chat_url = 'chat/myroom/'
    sender_token = AccessToken.for_user(first_user)
    sender_communicator = WebsocketCommunicator(
        application, f'{chat_url}?token={sender_token}'
    )
    connected, subprotocol = await sender_communicator.connect()
    assert connected

    recipient_token = AccessToken.for_user(second_user)
    recipient_communicator = WebsocketCommunicator(
        application, f'{chat_url}?token={recipient_token}'
    )

    connected, subprotocol = await recipient_communicator.connect()
    assert connected

    await sender_communicator.send_json_to(
        data={'message': 'test_message1',
              'sender': first_user.username,
              'recipient': second_user.username}
    )

    response = await recipient_communicator.receive_json_from()
    assert response['message'] == 'test_message1'
    assert response['sender'] == 'testusername1'
    assert response['recipient'] == 'testusername2'

    await sender_communicator.disconnect()
    await recipient_communicator.disconnect()


@pytest.mark.asyncio
async def test_websocket_message_creation_success(
        transactional_db,
        application: JWTAuthMiddlewareStack,
        first_user: User,
        second_user: User):
    chat_url = 'chat/test_room/'
    token = AccessToken.for_user(first_user)
    communicator = WebsocketCommunicator(
        application, f'{chat_url}?token={token}'
    )
    connected, subprotocol = await communicator.connect()
    assert connected

    await communicator.send_json_to(
        data={'message': 'test123',
              'sender': first_user.username,
              'recipient': second_user.username}
    )
    first_response = await communicator.receive_json_from()
    assert first_response['message'] == 'test123'

    await communicator.send_json_to(
        data={'message': 'test321',
              'sender': second_user.username,
              'recipient': first_user.username}
    )
    second_response = await communicator.receive_json_from()
    assert second_response['message'] == 'test321'

    messages = await sync_to_async(Message.objects.all)()
    assert await sync_to_async(len)(messages) == 2
    assert messages[0]

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_websocket_with_invalid_url(application: JWTAuthMiddlewareStack):
    with pytest.raises(ValueError):
        communicator = WebsocketCommunicator(
            application, 'juifgjsiufj'
        )
        await communicator.connect()


@pytest.mark.django_db(reset_sequences=True, transaction=True)
def test_user_messages_retrieve_success(
        first_user: User,
        second_user: User,
        third_user: User,
        test_messages,
        client: APIClient):
    token = AccessToken.for_user(first_user)
    client.force_authenticate(user=first_user, token=token)
    response: Response = client.get(reverse('chat'))
    assert len(response.data) == 3


@pytest.mark.django_db(reset_sequences=True, transaction=True)
def test_user_only_related_messages_retrieve_success(
        first_user: User,
        second_user: User,
        test_messages,
        client: APIClient):
    token: AccessToken = AccessToken.for_user(second_user)
    client.force_authenticate(user=second_user, token=token)
    response: Response = client.get(reverse('chat'))
    data = response.data
    assert len(response.data) == 2
    assert data[0]['sender'] == 1
    assert data[0]['recipient'] == 2
    assert data[0]['text'] == "hello user2, i'm user1"


@pytest.fixture
def blocking_user() -> User:
    yield User.objects.create(username='blocker_user', password='password')


@pytest.fixture
def blocked_user() -> User:
    yield User.objects.create(username='blocked_user', password='password')


@pytest.fixture
def block(blocking_user: User, blocked_user: User) -> Block:
    yield Block.objects.create(initiator_user=blocking_user,
                               blocked_user=blocked_user)


@pytest.mark.django_db(reset_sequences=True, transaction=True)
@pytest.mark.asyncio
async def test_blocked_user_cannot_message(application: JWTAuthMiddlewareStack,
                                           blocking_user: User,
                                           blocked_user: User, block: Block):
    room_url = 'chat/brand_new_test_room/'
    token = AccessToken.for_user(blocked_user)
    communicator = WebsocketCommunicator(
        application, f'{room_url}?token={token}'
    )
    connected, subprotocol = await communicator.connect()
    assert connected

    await communicator.send_json_to(
        data={'message': 'test',
              'sender': blocked_user.username,
              'recipient': blocking_user.username}
    )

    response: Response = await communicator.receive_json_from()
    assert response['message'] == 'You cannot message this user due to block.'
    # assert that no message objects has been created
    assert await sync_to_async(Message.objects.all().exists)() is False

    await communicator.disconnect()


@pytest.mark.django_db(reset_sequences=True, transaction=True)
@pytest.mark.asyncio
async def test_websocket_message_blocked_success(
        application: JWTAuthMiddlewareStack,
        blocking_user: User,
        blocked_user: User,
        block: Block) -> None:
    room_url = 'chat/blocked_room/'
    sender_token = AccessToken.for_user(blocking_user)
    sender_communicator = WebsocketCommunicator(
        application, f'{room_url}?token={sender_token}'
    )
    connected, subprotocol = await sender_communicator.connect()
    assert connected

    recipient_token = AccessToken.for_user(blocked_user)
    recipient_communicator = WebsocketCommunicator(
        application, f'{room_url}?token={recipient_token}'
    )

    connected, subprotocol = await recipient_communicator.connect()
    assert connected

    await sender_communicator.send_json_to(
        data={'message': 'test_message1',
              'sender': blocked_user.username,
              'recipient': blocking_user.username}
    )
    # Checking that blocked user couldn't send message to the recipient
    with pytest.raises(TimeoutError):
        await recipient_communicator.receive_json_from()

    await sender_communicator.disconnect()
    await recipient_communicator.disconnect()


@pytest.mark.django_db(reset_sequences=True, transaction=True)
@pytest.mark.asyncio
async def test_websocket_connect_decline(
        application: JWTAuthMiddlewareStack,
        blocking_user: User):
    room_url = 'chat/brand_new_test_room/'
    blocked_user = AnonymousUser()
    token = AccessToken.for_user(blocked_user)
    communicator = WebsocketCommunicator(
        application, f'{room_url}?token={token}'
    )
    connected, subprotocol = await communicator.connect()
    assert connected is False
