from django.urls import path, include
from api.views import RegisterCreateAPIView, UserRetrieveAPIView, LoginAPIView, ProfileRoleAPIView

urlpatterns = [
    path('register/', RegisterCreateAPIView.as_view(), name='register'),
    path('user/', UserRetrieveAPIView.as_view(), name='user'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('sppd/', include('apps.sppd.urls')),
    path('activate-role/', ProfileRoleAPIView.as_view({'post': 'set_active_role'}), name='role-profile')
]