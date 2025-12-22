from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.decorators import action, api_view
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
    BasePermission,
)
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from .models import Textbook, Order, Block
from .serializers import (
    TextbookSerializer,
    SignupSerializer,
    UserSerializer,
    OrderSerializer,
    ReportSerializer,
)
from .filters import TextbookFilter

User = get_user_model()


# TODO add logging


class HealthCheckView(APIView):
    """Health check endpoint for monitoring."""
    
    def get(self, request):
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class TextbookDetailView(APIView):

    def get(self, request, pk):
        """ Returns full description of a textbook by pk url parameter. """
        textbook = get_object_or_404(Textbook, pk=pk)
        serializer = TextbookSerializer(textbook)
        return Response(serializer.data)


class TextbookImageView(APIView):
    def get(self, request, pk):
        """ Returns full-sized image of a textbook. """
        textbook = get_object_or_404(Textbook, pk=pk)
        return Response({'image': textbook.image.url})


class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "You have access to this protected view!"})


class SignupView(APIView):
    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PersonalCabinetView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pass

    def post(self, request):
        pass


class CustomTokenObtainPairView(TokenObtainPairView):
    """ Returns refresh_token and access_token, tied to a user. """
    serializer_class = TokenObtainPairSerializer

    @method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        return User.objects.all()


class CustomTokenRefreshView(TokenRefreshView):
    """ Token refresh view with rate limiting. """
    
    @method_decorator(ratelimit(key='ip', rate='20/m', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.seller == request.user


class TextbookViewSet(viewsets.ModelViewSet):
    """Unified ViewSet for all textbook operations."""
    queryset = Textbook.objects.all()
    serializer_class = TextbookSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_class = TextbookFilter
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwner()]
        return super().get_permissions()
    
    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer


@api_view(['GET'])
def get_user_data(request):
    if request.method == 'GET':
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)


class BlockView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, username):
        """ Creates block between request.user and target user, preventing
         the target user to send messages to request.user in the future."""
        initiator = request.user
        user_to_block = get_object_or_404(User, username=username)
        block_already_exists = Block.objects.filter(
            initiator_user=initiator, blocked_user=user_to_block).exists()
        if block_already_exists:
            return Response(
                {'message': f'User {username} is already blocked.'},
                status=status.HTTP_304_NOT_MODIFIED
            )
        Block.objects.create(
            initiator_user=initiator, blocked_user=user_to_block
        )
        return Response(
            {'message': f'User {username} has been successfully blocked.'},
            status=status.HTTP_201_CREATED
        )

    def delete(self, request, username):
        initiator_user = request.user
        try:
            user_to_unblock = User.objects.get(username=username)
            block = Block.objects.get(initiator_user=initiator_user,
                                      blocked_user=user_to_unblock)
            block.delete()
            return Response(
                {'message': 'User has been successfully unblocked.'},
                status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            return Response({'error': f'No such user {username}'},
                            status=status.HTTP_404_NOT_FOUND)
        except Block.DoesNotExist:
            return Response({'error': f'User {username} is not blocked.'},
                            status=status.HTTP_404_NOT_FOUND)


class ReportView(APIView):
    """ View that allows to report other users.
     Reports can then be seen through admin panel. """
    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key='ip', rate='3/m', method='POST', block=True))
    def post(self, request):
        serializer = ReportSerializer(data=request.data,
                                      context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
