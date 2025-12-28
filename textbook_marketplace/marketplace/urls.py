# backend/textbook_marketplace/marketplace/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from rest_framework_simplejwt.views import (
    TokenVerifyView,
)

from .views import (
    HealthCheckView,
    TextbookDetailView,
    TextbookImageView,
    ProtectedView,
    SignupView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    TextbookViewSet,
    UserDetailView,
    BlockView,
    ReportView,
)

router = DefaultRouter()
router.register(r'textbooks', TextbookViewSet, basename='textbook')

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health'),
    path('', include(router.urls)),
    path('textbook/<int:pk>/', TextbookDetailView.as_view(), name='textbook-detail'),
    path('textbook/<int:pk>/image/', TextbookImageView.as_view()),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('protected/', ProtectedView.as_view(), name='protected'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('users/me/', UserDetailView.as_view(), name='user-detail'),
    path('users/<str:username>/block/', BlockView.as_view(), name='user-block'),
    path('report/', ReportView.as_view(), name='report'),
]
