from django.shortcuts import render
from api.serializers import RegisterSerializer, UserSerializer, LoginSerializer
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import generics, status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from sppd.models import ActiveRole
from sppd.utils import get_role

class RegisterCreateAPIView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response({
            "user": UserSerializer(user).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        }, status=status.HTTP_201_CREATED)

class UserRetrieveAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

class LoginAPIView(TokenObtainPairView):
    serializer_class = LoginSerializer

class ProfileRoleAPIView(viewsets.GenericViewSet):
    def set_active_role(self, request):
        role = request.data.get('role')
        user = request.user
        data = get_role(user)
        print("data", data)
        
        if role not in data:
            return Response({"msg": "You can't activate this role"}, status=status.HTTP_403_FORBIDDEN)
        
        active_role, created = ActiveRole.objects.update_or_create(
            user = user,
            defaults={
                "active_role" : role
            }
        )
        
        data = {
            "user": {user.username},
            "active_role": {role}
        }
        return Response({"msg": "success", "data": data}, status=status.HTTP_200_OK)
        