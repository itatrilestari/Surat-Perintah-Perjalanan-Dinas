from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password"
        ]

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data.get("username"),
            email=validated_data.get("email", ""),
            password=validated_data.get("password")
        )

        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email"
        ]

class LoginSerializer(TokenObtainPairSerializer):        
    def validate(self, obj):
        data = super().validate(obj)

        data['user'] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email
        }

        return data