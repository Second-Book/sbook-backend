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
def ws_url() -> str:
    return 'ws/chat/'


@pytest.fixture
def first_user() -> User:
    yield User.objects.create_user(
        username='testusername1', password='testpassword1'
    )


@pytest.fixture
def second_user() -> User:
    yield User.objects.create_user(
        username='testusername2', password='testpassword2'
    )


@pytest.fixture
def third_user() -> User:
    yield User.objects.create_user(
        username='testusername3', password='testpassword3'
    )


@pytest.fixture
def client() -> APIClient:
    yield APIClient()


@pytest.fixture
def test_unseen_messages(first_user: User,
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


@pytest.fixture
def test_seen_messages(first_user: User,
                       second_user: User,
                       third_user: User) -> tuple:
    msg1 = Message.objects.create(text="i'm user1, you saw me",
                                  sender=first_user,
                                  recipient=second_user,
                                  seen=True)
    msg2 = Message.objects.create(text='hello, user1, you saw me too',
                                  sender=second_user,
                                  recipient=first_user,
                                  seen=True)
    msg3 = Message.objects.create(text='hi, (seen)',
                                  sender=third_user,
                                  recipient=first_user,
                                  seen=True)
    yield msg1, msg2, msg3


@pytest.fixture(scope='module')
def application() -> JWTAuthMiddlewareStack:
    yield JWTAuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    )


@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_ws_conn_success(
        ws_url: str,
        first_user: User,
        application: JWTAuthMiddlewareStack
):
    token = AccessToken.for_user(first_user)
    communicator = WebsocketCommunicator(
        application, f'{ws_url}?token={token}'
    )
    connected, subprotocol = await communicator.connect(timeout=1)
    assert connected


@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_retrieve_new_messages_after_ws_conn_success(
        ws_url: str,
        first_user: User,
        test_unseen_messages: tuple[Message],
        application: JWTAuthMiddlewareStack
):
    token = AccessToken.for_user(first_user)
    communicator = WebsocketCommunicator(
        application, f'{ws_url}?token={token}'
    )
    connected, subprotocol = await communicator.connect(timeout=1)
    assert connected
    initial_message = await communicator.receive_json_from(timeout=1)
    assert initial_message['type'] == 'notification'
    assert len(initial_message['new_messages']) == 2
    for msg in initial_message['new_messages']:
        assert msg['recipient'] == 'testusername1'


@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_seen_messages_not_retrieved_after_ws_conn(
        ws_url: str,
        first_user: User,
        test_seen_messages: tuple[Message],
        application: JWTAuthMiddlewareStack,
):
    token = AccessToken.for_user(first_user)
    communicator = WebsocketCommunicator(
        application, f'{ws_url}?token={token}'
    )
    connected, subprotocol = await communicator.connect(timeout=1)
    assert connected
    initial_message = await communicator.receive_json_from(timeout=1)
    assert initial_message['type'] == 'notification'
    assert len(initial_message['new_messages']) == 0

    await communicator.disconnect()


@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_websocket_with_token_get_unseen_messages_success(
        ws_url: str,
        application: JWTAuthMiddlewareStack,
        first_user: User,
        second_user: User
):
    """
    Testing that after ws connection user gets a 'notification' type message,
    consisting of new (unseen) messages;
    """
    token_1 = AccessToken.for_user(first_user)
    communicator_1 = WebsocketCommunicator(
        application, f'{ws_url}?token={token_1}'
    )
    connected, subprotocol = await communicator_1.connect()
    assert connected
    response_1_init: Response = await communicator_1.receive_json_from()
    assert response_1_init['type'] == 'notification'
    await communicator_1.send_json_to(
        data={'message': 'test123123NEW',
              'sender': first_user.username,
              'recipient': second_user.username}
    )
    response_1_after_send: Response = await communicator_1.receive_json_from()
    assert response_1_after_send['type'] == 'message'
    assert response_1_after_send['sender'] == first_user.username
    assert response_1_after_send['recipient'] == second_user.username
    assert response_1_after_send['message'] == 'test123123NEW'

    token_2 = AccessToken.for_user(second_user)
    communicator_2 = WebsocketCommunicator(
        application, f'{ws_url}?token={token_2}'
    )
    connected, subprotocol = await communicator_2.connect()
    assert connected
    response_2_init: Response = await communicator_2.receive_json_from()
    assert response_2_init['type'] == 'notification'
    assert len(response_2_init['new_messages']) == 1
    assert response_2_init['new_messages'][0]['text'] == 'test123123NEW'

    # unseen messages wont be copied to 'message' type messages
    with pytest.raises(TimeoutError):
        await communicator_2.receive_json_from()

    await communicator_1.disconnect()
    await communicator_2.disconnect()


@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_websocket_with_token_get_new_message_success(
        ws_url: str,
        application: JWTAuthMiddlewareStack,
        first_user: User,
        second_user: User
):
    token_1 = AccessToken.for_user(first_user)
    communicator_1 = WebsocketCommunicator(
        application, f'{ws_url}?token={token_1}'
    )
    connected, subprotocol = await communicator_1.connect()
    assert connected

    token_2 = AccessToken.for_user(second_user)
    communicator_2 = WebsocketCommunicator(
        application, f'{ws_url}?token={token_2}'
    )
    connected, subprotocol = await communicator_2.connect()
    assert connected

    await communicator_1.send_json_to(
        data={'message': 'hi, user2',
              'sender': first_user.username,
              'recipient': second_user.username})

    response_1_init = await communicator_1.receive_json_from(timeout=5)
    assert response_1_init['type'] == 'notification'
    assert len(response_1_init['new_messages']) == 0
    response_1 = await communicator_1.receive_json_from(timeout=5)
    assert response_1['message'] == 'hi, user2'

    response_2_init = await communicator_2.receive_json_from(timeout=5)
    assert response_2_init['type'] == 'notification'
    assert len(response_2_init['new_messages']) == 0
    response_2 = await communicator_2.receive_json_from(timeout=5)
    assert response_2['type'] == 'message'
    assert response_2['message'] == 'hi, user2'

    await communicator_1.disconnect()
    await communicator_2.disconnect()


@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_websocket_with_token_send_message_bad_recipient_failure(
        ws_url: str,
        application: JWTAuthMiddlewareStack,
        first_user: User,
):
    token_1 = AccessToken.for_user(first_user)
    communicator_1 = WebsocketCommunicator(
        application, f'{ws_url}?token={token_1}'
    )
    connected, subprotocol = await communicator_1.connect()
    assert connected
    await communicator_1.receive_json_from(timeout=5)  # init message

    await communicator_1.send_json_to(
        data={'message': 'hello!',
              'sender': first_user.username,
              'recipient': 'someone_idk'}
    )
    response_1 = await communicator_1.receive_json_from(timeout=5)
    assert response_1['type'] == 'error'

    await communicator_1.disconnect()


@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_websocket_with_token_send_message_to_blocked_user_failure(
        ws_url: str,
        application: JWTAuthMiddlewareStack,
        first_user: User,
        second_user: User
):
    await sync_to_async(Block.objects.create)(initiator_user=first_user,
                                        blocked_user=second_user)
    token_1 = AccessToken.for_user(first_user)
    communicator_1 = WebsocketCommunicator(
        application, f'{ws_url}?token={token_1}'
    )
    connected, subprotocol = await communicator_1.connect()
    assert connected
    await communicator_1.receive_json_from(timeout=5)  # init message

    await communicator_1.send_json_to(
        data={'message': 'hello!',
              'sender': first_user.username,
              'recipient': second_user.username}
    )

    response_1 = await communicator_1.receive_json_from(timeout=5)
    assert response_1['type'] == 'error'
    assert response_1['message'] == 'You cannot message this user due to a block.'

    token_2 = AccessToken.for_user(second_user)
    communicator_2 = WebsocketCommunicator(
        application, f'{ws_url}?token={token_2}'
    )
    connected, subprotocol = await communicator_2.connect()
    assert connected
    response_2_init = await communicator_2.receive_json_from(timeout=5)  # init message
    assert response_2_init['type'] == 'notification'
    # assert that blocked message was not sent
    assert len(response_2_init['new_messages']) == 0

    await communicator_1.disconnect()
    await communicator_2.disconnect()
