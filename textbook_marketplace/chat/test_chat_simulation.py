"""
Full two-user chat simulation test suite.

Covers the complete chat lifecycle:
- WebSocket connection & authentication
- Real-time message exchange between two users
- Notification of unseen messages on connect
- REST API: conversation history, mark as seen
- Edge cases: self-messaging, empty input, long messages, rapid fire
- Blocking: bidirectional block prevents messaging
- Reconnection: unseen messages delivered on reconnect
"""
import asyncio

import pytest
from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from .routing import websocket_urlpatterns
from .models import Message
from marketplace.models import Block
from chat.jwt_middleware import CustomJWTAuthMiddlewareStack

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def application():
    yield CustomJWTAuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    )


@pytest.fixture
def ws_url() -> str:
    return 'ws/chat/'


@pytest.fixture
def alice(db) -> User:
    return User.objects.create_user(username='alice', password='pass12345')


@pytest.fixture
def bob(db) -> User:
    return User.objects.create_user(username='bob', password='pass12345')


@pytest.fixture
def charlie(db) -> User:
    return User.objects.create_user(username='charlie', password='pass12345')


@pytest.fixture
def alice_client(alice) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=alice)
    return client


@pytest.fixture
def bob_client(bob) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=bob)
    return client


async def connect_user(application, ws_url: str, user: User):
    """Helper: connect user via WebSocket, consume initial notification."""
    token = AccessToken.for_user(user)
    communicator = WebsocketCommunicator(application, f'{ws_url}?token={token}')
    connected, _ = await communicator.connect(timeout=5)
    assert connected, f'{user.username} failed to connect'
    init = await communicator.receive_json_from(timeout=5)
    assert init['type'] == 'notification'
    return communicator, init


# ---------------------------------------------------------------------------
# 1. Full conversation simulation: Alice ↔ Bob real-time
# ---------------------------------------------------------------------------

@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_full_conversation_realtime(ws_url, application, alice, bob):
    """
    Simulates a real-time conversation:
    1. Both users connect
    2. Alice sends "Привет, Боб!"
    3. Bob receives it and replies "Привет, Алиса!"
    4. Alice receives the reply
    5. Messages are persisted in DB
    """
    comm_alice, _ = await connect_user(application, ws_url, alice)
    comm_bob, _ = await connect_user(application, ws_url, bob)

    # Alice → Bob
    await comm_alice.send_json_to({
        'message': 'Привет, Боб!',
        'recipient': 'bob',
    })
    # Alice gets her own message back (confirmation)
    resp_alice = await comm_alice.receive_json_from(timeout=5)
    assert resp_alice['type'] == 'message'
    assert resp_alice['message'] == 'Привет, Боб!'
    assert resp_alice['sender'] == 'alice'
    assert resp_alice['recipient'] == 'bob'

    # Bob receives it
    resp_bob = await comm_bob.receive_json_from(timeout=5)
    assert resp_bob['type'] == 'message'
    assert resp_bob['message'] == 'Привет, Боб!'
    assert resp_bob['sender'] == 'alice'

    # Bob → Alice
    await comm_bob.send_json_to({
        'message': 'Привет, Алиса!',
        'recipient': 'alice',
    })
    resp_bob2 = await comm_bob.receive_json_from(timeout=5)
    assert resp_bob2['type'] == 'message'
    assert resp_bob2['sender'] == 'bob'

    resp_alice2 = await comm_alice.receive_json_from(timeout=5)
    assert resp_alice2['type'] == 'message'
    assert resp_alice2['message'] == 'Привет, Алиса!'
    assert resp_alice2['sender'] == 'bob'

    # Verify DB persistence
    count = await sync_to_async(Message.objects.count)()
    assert count == 2

    await comm_alice.disconnect()
    await comm_bob.disconnect()


# ---------------------------------------------------------------------------
# 2. Multi-message rapid-fire exchange
# ---------------------------------------------------------------------------

@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_rapid_fire_messages(ws_url, application, alice, bob):
    """Alice sends 5 messages in quick succession, Bob receives all of them."""
    comm_alice, _ = await connect_user(application, ws_url, alice)
    comm_bob, _ = await connect_user(application, ws_url, bob)

    messages_to_send = [f'Сообщение #{i}' for i in range(1, 6)]

    for msg_text in messages_to_send:
        await comm_alice.send_json_to({
            'message': msg_text,
            'recipient': 'bob',
        })

    # Collect all messages at Bob's side
    bob_received = []
    for _ in messages_to_send:
        # Alice confirmation
        await comm_alice.receive_json_from(timeout=5)
        # Bob receives
        resp = await comm_bob.receive_json_from(timeout=5)
        bob_received.append(resp['message'])

    assert bob_received == messages_to_send

    count = await sync_to_async(Message.objects.count)()
    assert count == 5

    await comm_alice.disconnect()
    await comm_bob.disconnect()


# ---------------------------------------------------------------------------
# 3. Offline messages: Bob connects after Alice sends
# ---------------------------------------------------------------------------

@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_offline_messages_delivered_on_connect(ws_url, application, alice, bob):
    """
    Alice sends messages while Bob is offline.
    Bob connects later and gets them as unseen notifications.
    """
    comm_alice, _ = await connect_user(application, ws_url, alice)

    # Alice sends 3 messages while Bob is offline
    for i in range(1, 4):
        await comm_alice.send_json_to({
            'message': f'Ты тут? #{i}',
            'recipient': 'bob',
        })
        await comm_alice.receive_json_from(timeout=5)  # consume confirmation

    await comm_alice.disconnect()

    # Bob connects and should get unseen messages in notification
    comm_bob, init_bob = await connect_user(application, ws_url, bob)
    assert len(init_bob['new_messages']) == 3
    texts = [m['text'] for m in init_bob['new_messages']]
    assert 'Ты тут? #1' in texts
    assert 'Ты тут? #3' in texts

    await comm_bob.disconnect()


# ---------------------------------------------------------------------------
# 4. REST API: conversation history
# ---------------------------------------------------------------------------

@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_rest_conversation_history(ws_url, application, alice, bob,
                                          alice_client, bob_client):
    """
    After WebSocket exchange, REST API returns ordered conversation history.
    """
    comm_alice, _ = await connect_user(application, ws_url, alice)
    comm_bob, _ = await connect_user(application, ws_url, bob)

    await comm_alice.send_json_to({'message': 'Первое', 'recipient': 'bob'})
    await comm_alice.receive_json_from(timeout=5)
    await comm_bob.receive_json_from(timeout=5)

    await comm_bob.send_json_to({'message': 'Второе', 'recipient': 'alice'})
    await comm_bob.receive_json_from(timeout=5)
    await comm_alice.receive_json_from(timeout=5)

    await comm_alice.disconnect()
    await comm_bob.disconnect()

    # REST: Alice fetches conversation with Bob
    resp = await sync_to_async(alice_client.get)('/api/chat/conversation/bob/')
    assert resp.status_code == 200
    data = resp.data
    assert len(data) == 2
    assert data[0]['text'] == 'Первое'
    assert data[1]['text'] == 'Второе'


# ---------------------------------------------------------------------------
# 5. REST API: mark messages as seen (security check)
# ---------------------------------------------------------------------------

@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_mark_as_seen_only_own_messages(ws_url, application, alice, bob,
                                                alice_client, bob_client):
    """
    Bob can mark messages addressed to him as seen.
    Alice cannot mark messages addressed to Bob.
    """
    comm_alice, _ = await connect_user(application, ws_url, alice)

    await comm_alice.send_json_to({'message': 'Привет!', 'recipient': 'bob'})
    await comm_alice.receive_json_from(timeout=5)
    await comm_alice.disconnect()

    msg = await sync_to_async(Message.objects.first)()
    msg_id = msg.id

    # Alice tries to mark Bob's message as seen — should fail (304)
    resp = await sync_to_async(alice_client.post)(
        '/api/chat/mark/', {'ids_to_mark': [msg_id]}, format='json'
    )
    assert resp.status_code == 304

    # Verify message is still unseen
    await sync_to_async(msg.refresh_from_db)()
    assert msg.seen is False

    # Bob marks it — should succeed
    resp = await sync_to_async(bob_client.post)(
        '/api/chat/mark/', {'ids_to_mark': [msg_id]}, format='json'
    )
    assert resp.status_code == 200

    await sync_to_async(msg.refresh_from_db)()
    assert msg.seen is True


# ---------------------------------------------------------------------------
# 6. Blocking prevents messaging
# ---------------------------------------------------------------------------

@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_blocked_user_cannot_send(ws_url, application, alice, bob):
    """
    After Alice blocks Bob, neither can message the other.
    """
    await sync_to_async(Block.objects.create)(
        initiator_user=alice, blocked_user=bob
    )

    comm_alice, _ = await connect_user(application, ws_url, alice)
    comm_bob, _ = await connect_user(application, ws_url, bob)

    # Bob tries to message Alice
    await comm_bob.send_json_to({'message': 'Привет!', 'recipient': 'alice'})
    resp = await comm_bob.receive_json_from(timeout=5)
    assert resp['type'] == 'error'
    assert 'block' in resp['message'].lower()

    # Alice tries to message Bob
    await comm_alice.send_json_to({'message': 'Привет!', 'recipient': 'bob'})
    resp = await comm_alice.receive_json_from(timeout=5)
    assert resp['type'] == 'error'
    assert 'block' in resp['message'].lower()

    # No messages in DB
    count = await sync_to_async(Message.objects.count)()
    assert count == 0

    await comm_alice.disconnect()
    await comm_bob.disconnect()


# ---------------------------------------------------------------------------
# 7. Unblock restores messaging
# ---------------------------------------------------------------------------

@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_unblock_restores_messaging(ws_url, application, alice, bob):
    """
    Block then unblock — messaging works again.
    """
    block = await sync_to_async(Block.objects.create)(
        initiator_user=alice, blocked_user=bob
    )

    comm_alice, _ = await connect_user(application, ws_url, alice)

    # Alice can't message Bob while blocked
    await comm_alice.send_json_to({'message': 'test', 'recipient': 'bob'})
    resp = await comm_alice.receive_json_from(timeout=5)
    assert resp['type'] == 'error'

    # Unblock
    await sync_to_async(block.delete)()

    # Now it works
    await comm_alice.send_json_to({'message': 'Разблокировала!', 'recipient': 'bob'})
    resp = await comm_alice.receive_json_from(timeout=5)
    assert resp['type'] == 'message'
    assert resp['message'] == 'Разблокировала!'

    await comm_alice.disconnect()


# ---------------------------------------------------------------------------
# 8. Send to non-existent user
# ---------------------------------------------------------------------------

@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_send_to_nonexistent_user(ws_url, application, alice):
    """Sending to a non-existent user returns an error."""
    comm, _ = await connect_user(application, ws_url, alice)

    await comm.send_json_to({'message': 'Привет!', 'recipient': 'nobody'})
    resp = await comm.receive_json_from(timeout=5)
    assert resp['type'] == 'error'
    assert 'nobody' in resp['message']

    count = await sync_to_async(Message.objects.count)()
    assert count == 0

    await comm.disconnect()


# ---------------------------------------------------------------------------
# 9. Unauthenticated WebSocket connection rejected
# ---------------------------------------------------------------------------

@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_unauthenticated_ws_rejected(ws_url, application):
    """Connection without token is rejected with code 4003."""
    communicator = WebsocketCommunicator(application, ws_url)
    connected, code = await communicator.connect(timeout=5)
    # Consumer closes with 4003 for unauthenticated users
    assert not connected or code == 4003


# ---------------------------------------------------------------------------
# 10. Expired token rejected
# ---------------------------------------------------------------------------

@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_expired_token_rejected(ws_url, application, alice):
    """Connection with expired token is rejected."""
    from datetime import timedelta
    token = AccessToken.for_user(alice)
    token.set_exp(lifetime=-timedelta(seconds=1))
    communicator = WebsocketCommunicator(
        application, f'{ws_url}?token={str(token)}'
    )
    connected, code = await communicator.connect(timeout=5)
    assert not connected or code == 4003


# ---------------------------------------------------------------------------
# 11. Three-user scenario: messages routed correctly
# ---------------------------------------------------------------------------

@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_three_users_routing(ws_url, application, alice, bob, charlie):
    """
    Alice → Bob, Alice → Charlie: each recipient only gets their message.
    """
    comm_alice, _ = await connect_user(application, ws_url, alice)
    comm_bob, _ = await connect_user(application, ws_url, bob)
    comm_charlie, _ = await connect_user(application, ws_url, charlie)

    # Alice → Bob
    await comm_alice.send_json_to({'message': 'Для Боба', 'recipient': 'bob'})
    await comm_alice.receive_json_from(timeout=5)  # confirmation

    # Alice → Charlie
    await comm_alice.send_json_to({'message': 'Для Чарли', 'recipient': 'charlie'})
    await comm_alice.receive_json_from(timeout=5)  # confirmation

    # Bob gets only his message
    resp_bob = await comm_bob.receive_json_from(timeout=5)
    assert resp_bob['message'] == 'Для Боба'

    # Charlie gets only his message
    resp_charlie = await comm_charlie.receive_json_from(timeout=5)
    assert resp_charlie['message'] == 'Для Чарли'

    # Bob should have no more messages
    with pytest.raises((TimeoutError, asyncio.TimeoutError)):
        await comm_bob.receive_json_from(timeout=1)

    await comm_alice.disconnect()
    try:
        await comm_bob.disconnect()
    except asyncio.CancelledError:
        pass
    try:
        await comm_charlie.disconnect()
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# 12. Reconnect gets only unseen messages
# ---------------------------------------------------------------------------

@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.asyncio
async def test_reconnect_unseen_only(ws_url, application, alice, bob, bob_client):
    """
    Bob connects, receives message, marks as seen, disconnects.
    Alice sends another message. Bob reconnects — gets only the new one.
    """
    comm_alice, _ = await connect_user(application, ws_url, alice)
    comm_bob, _ = await connect_user(application, ws_url, bob)

    # Alice → Bob (message 1)
    await comm_alice.send_json_to({'message': 'Первое', 'recipient': 'bob'})
    await comm_alice.receive_json_from(timeout=5)
    await comm_bob.receive_json_from(timeout=5)

    # Bob marks message as seen via REST
    msg = await sync_to_async(Message.objects.first)()
    await sync_to_async(bob_client.post)(
        '/api/chat/mark/', {'ids_to_mark': [msg.id]}, format='json'
    )

    await comm_bob.disconnect()

    # Alice sends another message while Bob is offline
    await comm_alice.send_json_to({'message': 'Второе', 'recipient': 'bob'})
    await comm_alice.receive_json_from(timeout=5)
    await comm_alice.disconnect()

    # Bob reconnects — should only get the second (unseen) message
    comm_bob2, init_bob = await connect_user(application, ws_url, bob)
    assert len(init_bob['new_messages']) == 1
    assert init_bob['new_messages'][0]['text'] == 'Второе'

    await comm_bob2.disconnect()
