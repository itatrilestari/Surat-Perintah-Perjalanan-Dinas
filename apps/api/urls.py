from django.urls import path
from api.views import RegisterCreateAPIView, UserRetrieveAPIView, LoginAPIView

urlpatterns = [
    path('register/', RegisterCreateAPIView.as_view(), name='register'),
    path('user/', UserRetrieveAPIView.as_view(), name='user'),
    path('login/', LoginAPIView.as_view(), name='login'),
]