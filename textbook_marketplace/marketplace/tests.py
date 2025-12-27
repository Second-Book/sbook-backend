import json
import pytest
from PIL import Image
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework.exceptions import ErrorDetail
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework.test import (
    APIClient,
    APIRequestFactory,
)
# from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Textbook, Block
from .views import TextbookViewSet, IsAuthenticatedOrReadOnly

# TODO consider reworking model creation with model_bakery library
# TODO mock db if possible in the future
User = get_user_model()


@pytest.fixture
def seller() -> User:
    yield User.objects.create_user(id=1,
                                   username='seller_name',
                                   password='password',
                                   is_seller=True)


@pytest.fixture
def user1() -> User:
    # password has to be hashed for jwt endpoints
    user = User.objects.create_user(id=2,
                                    username='username1',
                                    password='password1')
    yield user


@pytest.fixture
def test_image():
    image = Image.new('RGB', (100, 100), color='black')
    image_io = BytesIO()
    image.save(image_io, format='JPEG')
    image_io.seek(0)

    yield SimpleUploadedFile('test_image.jpg',
                             image_io.getvalue(),
                             content_type='image/jpeg')


@pytest.fixture
def textbook1(seller: User, test_image: Image):
    textbook = Textbook.objects.create(
        title='Mathematics 101',
        author='John Doe',
        school_class='10th Grade',
        publisher='Education Inc.',
        price=29.99,
        seller=seller,
        description='A comprehensive guide to mathematics.',
        whatsapp_contact='1234567890',
        viber_contact='1234567890',
        telegram_contact='@johndoe',
        phone_contact='1234567890',
        condition='New',
        image=test_image,
    )
    yield textbook


@pytest.fixture
def textbook2(seller: User, test_image: Image):
    textbook = Textbook.objects.create(
        title='History 201',
        author='Jane Smith',
        school_class='11th Grade',
        publisher='History Books',
        price=39.99,
        seller=seller,
        description='A detailed history textbook.',
        whatsapp_contact='0987654321',
        viber_contact='0987654321',
        telegram_contact='@janesmith',
        phone_contact='0987654321',
        condition='Used - Excellent',
        image=test_image,
    )
    yield textbook


@pytest.fixture
def textbook3(seller: User, test_image: Image):
    textbook = Textbook.objects.create(
        title='Science 301',
        author='Alice Johnson',
        school_class='12th Grade',
        publisher='Science Publishers',
        price=49.99,
        seller=seller,
        description='An advanced science textbook.',
        whatsapp_contact='1122334455',
        viber_contact='1122334455',
        telegram_contact='@alicejohnson',
        phone_contact='1122334455',
        condition='Used - Good',
        image=test_image,
    )
    yield textbook


@pytest.fixture
def client() -> APIClient:
    yield APIClient()


@pytest.mark.django_db(reset_sequences=True, transaction=True)
def test_textbooks_retrieve_success(seller: User,
                                    textbook1: Textbook,
                                    textbook2: Textbook,
                                    textbook3: Textbook,
                                    client: APIClient):
    response: Response = client.get(reverse('textbook-list'))
    assert response.status_code == 200
    data = response.data['results']
    assert len(data) == 3
    test_textbook = data[0]
    assert test_textbook['id'] == 1
    assert test_textbook['seller'] == seller.username
    assert test_textbook['title'] == 'Mathematics 101'
    assert test_textbook['author'] == 'John Doe'
    assert test_textbook['school_class'] == '10th Grade'
    assert test_textbook['publisher'] == 'Education Inc.'
    assert test_textbook['price'] == '29.99'
    assert (test_textbook['description'] ==
            'A comprehensive guide to mathematics.')


@pytest.mark.django_db(reset_sequences=True, transaction=True)
def test_textbook_detail_view_success(seller: User,
                                      textbook1: Textbook,
                                      client: APIClient):
    response: Response = client.get(reverse('textbook-detail',
                                            kwargs={'pk': 1}))
    assert response.status_code == 200
    data = response.data
    assert data['id'] == 1
    assert data['seller'] == seller.username
    assert data['title'] == 'Mathematics 101'
    assert data['author'] == 'John Doe'
    assert data['school_class'] == '10th Grade'
    assert data['publisher'] == 'Education Inc.'
    assert data['price'] == '29.99'
    assert data['description'] == 'A comprehensive guide to mathematics.'


@pytest.mark.django_db(reset_sequences=True, transaction=True)
def test_textbook_image_view_success(textbook1: Textbook,
                                     client: APIClient):
    response: Response = client.get(reverse('textbook-detail',
                                            kwargs={'pk': 1}))
    assert response.status_code == 200
    assert 'image' in response.data
    image_data = response.data['image']
    assert 'preview' in image_data
    assert 'detail' in image_data


@pytest.mark.django_db(reset_sequences=True, transaction=True)
def test_textbook_create_success(seller: User,
                                 test_image: Image,
                                 client: APIClient):
    token: AccessToken = AccessToken.for_user(user=seller)
    client.force_authenticate(user=seller, token=token)
    response: Response = client.post(
        reverse('textbook-list'),
        data={'title': 'Science 301',
              'author': 'Alice Johnson',
              'school_class': '12th Grade',
              'publisher': 'Science Publishers',
              'subject': 'Science',
              'price': 49.99,
              'description': 'An advanced science textbook.',
              'whatsapp_contact': '1122334455',
              'viber_contact': '1122334455',
              'telegram_contact': '@alicejohnson',
              'phone_contact': '1122334455',
              'condition': 'Used - Good',
              'image': test_image}
    )
    assert response.status_code == 201
    data = response.data
    assert data['id'] == 1
    assert data['seller'] == 'seller_name'


@pytest.mark.django_db(reset_sequences=True, transaction=True)
def test_token_obtain_pair_success(user1: User, client: APIClient):
    response = client.post(reverse("token_obtain_pair"),
                           data={"username": "username1",
                                 "password": "password1"},
                           format="json")
    assert response.status_code == 200
    data = response.data
    assert len(data) == 2
    assert data['refresh']
    assert data['access']


@pytest.mark.django_db(reset_sequences=True, transaction=True)
def test_token_obtain_pair_bad_creds(user1: User, client: APIClient):
    response = client.post(reverse("token_obtain_pair"),
                           data=json.dumps({"username": "random_username_idk",
                                            "password": "password1"}),
                           format="json")
    assert response.status_code == 400
    data = response.data
    assert 'refresh' not in data
    assert 'access' not in data


@pytest.mark.django_db(reset_sequences=True, transaction=True)
def test_token_refresh_success(user1: User, client: APIClient):
    refresh = RefreshToken.for_user(user=user1)
    response = client.post(reverse('token_refresh'), data={"refresh": refresh})
    assert response.status_code == 200
    data = response.data
    assert data['access']
    assert 'refresh' not in data


@pytest.mark.django_db(reset_sequences=True, transaction=True)
def test_token_refresh_bad_refresh(user1: User, client: APIClient):
    refresh = 'hgiushgfsfn'
    response = client.post(reverse('token_refresh'), data={"refresh": refresh})
    assert response.status_code == 401
    data = response.data
    assert 'refresh' not in data
    assert 'access' not in data


@pytest.mark.django_db(reset_sequences=True, transaction=True)
def test_token_verify_success(user1: User, client: APIClient):
    refresh = RefreshToken.for_user(user=user1)
    response = client.post(reverse('token_verify'), data={"token": refresh})
    assert response.status_code == 200


@pytest.mark.django_db(reset_sequences=True, transaction=True)
def test_token_verify_failure(user1: User, client: APIClient):
    refresh = 'badtoken'
    response = client.post(reverse('token_verify'), data={"token": refresh})
    assert response.status_code == 401


@pytest.mark.django_db(reset_sequences=True, transaction=True)
def test_protected_view_success(user1: User, client: APIClient):
    token = AccessToken.for_user(user=user1)
    client.force_authenticate(user=user1, token=token)
    response = client.get(reverse('protected'))
    assert response.status_code == 200


@pytest.mark.django_db(reset_sequences=True, transaction=True)
def test_protected_view_failure(client: APIClient):
    response = client.get(reverse('protected'))
    assert response.status_code == 401


@pytest.mark.django_db(reset_sequences=True, transaction=True)
def test_signup_success(client: APIClient):
    response = client.post(reverse('signup'),
                           data=json.dumps({"username": "new_user",
                                            "email": "new@example.com",
                                            "password": "password"}),
                           content_type="application/json")
    assert response.status_code == 201
    data = response.data
    assert len(data) == 2
    assert data['username'] == 'new_user'
    assert data['email'] == 'new@example.com'
    assert 'password' not in data


@pytest.mark.django_db(reset_sequences=True, transaction=True)
def test_signup_failure(client: APIClient):
    response = client.post(reverse('signup'),
                           data=json.dumps({'username': 'new_user',
                                            'email': 'new@example.com'}),
                           content_type='application/json')
    assert response.status_code == 400


@pytest.mark.django_db(reset_sequences=True, transaction=True)
def test_user_detail_success(user1: User, client: APIClient):
    token = AccessToken.for_user(user=user1)
    client.force_authenticate(user=user1, token=token)
    response = client.get(reverse('user-detail'))
    assert response.status_code == 200
    data = response.data
    assert data['username'] == 'username1'
    assert data['email'] == ''


@pytest.mark.django_db(reset_sequences=True, transaction=True)
def test_user_detail_failure(user1: User, client: APIClient):
    response = client.get(reverse('user-detail'))
    assert response.status_code == 401
    assert len(response.data) == 1


@pytest.fixture
def block_initiator_user() -> User:
    yield User.objects.create(username='username1',
                              password='password1')


@pytest.fixture
def block_user() -> User:
    yield User.objects.create(username='username2',
                              password='password2')


@pytest.fixture
def block(block_initiator_user: User,
          block_user: User) -> Block:
    yield Block.objects.create(
        initiator_user=block_initiator_user,
        blocked_user=block_user
    )


@pytest.mark.django_db(transaction=True)
def test_block_view_success(block_initiator_user: User,
                            block_user: User,
                            client: APIClient):
    token = AccessToken.for_user(block_initiator_user)
    client.force_authenticate(user=block_initiator_user, token=token)
    response: Response = client.post(
        reverse('user-block', kwargs={'username': 'username2'}))

    assert response.status_code == 201
    assert response.data == {
        'message': 'User username2 has been successfully blocked.'
    }


@pytest.mark.django_db
def test_block_view_already_blocked(block_initiator_user: User,
                                    block_user: User,
                                    block: Block,
                                    client: APIClient):
    token = AccessToken.for_user(block_initiator_user)
    client.force_authenticate(user=block_initiator_user, token=token)
    response: Response = client.post(
        reverse('user-block', kwargs={'username': 'username2'})
    )

    assert response.status_code == 304
    assert response.data == {
        'message': 'User username2 is already blocked.'}


@pytest.mark.django_db
def test_block_view_unblock_success(block_initiator_user: User,
                                    block_user: User,
                                    block: Block,
                                    client: APIClient):
    token = AccessToken.for_user(block_initiator_user)
    client.force_authenticate(user=block_initiator_user, token=token)
    response: Response = client.delete(
        reverse('user-block', kwargs={'username': 'username2'})
    )
    assert response.status_code == 204
    with pytest.raises(Block.DoesNotExist):
        Block.objects.get(initiator_user=block_initiator_user,
                          blocked_user=block_user)


@pytest.mark.django_db(transaction=True)
def test_block_view_unblock_no_user_failure(block_initiator_user: User,
                                            block_user: User,
                                            block: Block,
                                            client: APIClient):
    token = AccessToken.for_user(block_initiator_user)
    client.force_authenticate(user=block_initiator_user, token=token)
    response: Response = client.delete(
        reverse('user-block', kwargs={'username': 'random_username_idk'})
    )
    assert response.status_code == 404
    assert response.data['error'] == 'No such user random_username_idk'
    # assert that block still exists
    assert Block.objects.filter(initiator_user=block_initiator_user,
                                blocked_user=block_user).exists()


@pytest.mark.django_db(transaction=True)
def test_block_view_unblock_no_block_failure(block_initiator_user: User,
                                             block_user: User,
                                             client: APIClient):
    token = AccessToken.for_user(block_initiator_user)
    client.force_authenticate(user=block_initiator_user, token=token)
    response: Response = client.delete(
        reverse('user-block', kwargs={'username': block_user.username})
    )
    assert response.status_code == 404
    assert response.data['error'] == (f'User {block_user.username} '
                                      f'is not blocked.')


@pytest.fixture
def user_reporting() -> User:
    yield User.objects.create_user(username='i_report', password='password')


@pytest.fixture
def user_reported() -> User:
    yield User.objects.create_user(username='reported', password='password')


@pytest.mark.django_db
def test_report_success(user_reporting: User,
                        user_reported: User,
                        client: APIClient):
    token = AccessToken.for_user(user=user_reporting)
    client.force_authenticate(user=user_reporting, token=token)
    response = client.post(reverse('report'),
                           data={'user_reported': user_reported.username,
                                 'topic': 'message',
                                 'description': 'He is bad!'})
    assert response.status_code == 201
    data = response.data
    assert data['user_reported'] == 'reported'
    assert data['topic'] == 'message'
    assert data['description'] == 'He is bad!'
    assert 'created_at' in data


@pytest.mark.django_db(transaction=True)
def test_report_bad_username(user_reporting: User,
                                user_reported: User,
                                client: APIClient):
    token = AccessToken.for_user(user=user_reporting)
    client.force_authenticate(user=user_reporting, token=token)
    response = client.post(reverse('report'),
                           data={'user_reported': 'random_username',
                                 'topic': 'message',
                                 'description': 'He is bad!'})
    assert response.status_code == 404
    assert isinstance(response.data['detail'], ErrorDetail)


@pytest.mark.django_db
def test_report_unauthenticated(user_reporting: User,
                                user_reported: User,
                                client: APIClient):
    response = client.post(reverse('report'),
                           data={'user_reported': user_reported.username,
                                 'topic': 'message',
                                 'description': 'He is bad!'})
    assert response.status_code == 401
    assert isinstance(response.data['detail'], ErrorDetail)


@pytest.fixture
def factory() -> APIRequestFactory:
    yield APIRequestFactory()


@pytest.mark.django_db
def test_auth_or_read_only_permission_success(user1: User,
                                              factory: APIRequestFactory):
    request = factory.post(reverse('textbook-list'))
    request.user = user1
    permission = IsAuthenticatedOrReadOnly()
    assert permission.has_permission(
        request=request, view=TextbookViewSet.as_view({'post': 'create'})
    )


@pytest.mark.django_db
def test_auth_or_read_only_permission_anon_user(factory: APIRequestFactory):
    request = factory.post(reverse('textbook-list'))
    request.user = AnonymousUser()
    permission = IsAuthenticatedOrReadOnly()
    assert permission.has_permission(
        request=request, view=TextbookViewSet.as_view({'post': 'create'})
    ) is False
