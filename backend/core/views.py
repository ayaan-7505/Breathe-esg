"""
Core views — registration, login, current-user profile, tenant list.
"""

from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Tenant, CustomUser
from .permissions import IsSuperAdmin
from .serializers import (
    TenantSerializer,
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
)


class RegisterView(APIView):
    """
    POST /api/auth/register/
    Creates a new user (and optionally a new tenant).
    Returns the auth token on success.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    POST /api/auth/login/
    Authenticates and returns the token.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user": UserSerializer(user).data,
            }
        )


class MeView(APIView):
    """
    GET /api/auth/me/
    Returns the current authenticated user's profile.
    """

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Deletes the user's auth token.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            request.user.auth_token.delete()
            return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"detail": "Token not found or already deleted."}, status=status.HTTP_400_BAD_REQUEST)


class TenantListView(generics.ListCreateAPIView):
    """
    GET  /api/tenants/  — list all tenants (super-admin only)
    POST /api/tenants/  — create a new tenant (super-admin only)
    """

    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
