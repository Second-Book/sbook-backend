# backend/textbook_marketplace/marketplace/urls.py
from django.urls import path

from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)

from .views import (
    TextbookListViewSet,
    TextbookDetailView,
    TextbookImageView,
    ProtectedView,
    SignupView,
    CustomTokenObtainPairView,
    TextbookViewSet,
    UserDetailView,
    BlockView,
    ReportView,
)

urlpatterns = [
    path('textbooks/', TextbookListViewSet.as_view({'get': 'list'}), name='textbook-list'),
    path('textbook/<int:pk>/', TextbookDetailView.as_view(), name='textbook-detail'),
    path('textbook/<int:pk>/image/', TextbookImageView.as_view()),
    path('textbook/create/', TextbookViewSet.as_view({'post': 'create'}), name='textbook-create'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('protected/', ProtectedView.as_view(), name='protected'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('users/me/', UserDetailView.as_view(), name='user-detail'),
    path('users/<str:username>/block/', BlockView.as_view(), name='user-block'),
    path('report/', ReportView.as_view(), name='report'),
]
