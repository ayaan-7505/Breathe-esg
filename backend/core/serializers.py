"""
Core serializers — user registration, login, tenant listing.
"""

from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import Tenant, CustomUser


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name", "slug", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.name", read_only=True, default=None)

    class Meta:
        model = CustomUser
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "role", "tenant", "tenant_name", "date_joined",
        ]
        read_only_fields = ["id", "date_joined"]


class RegisterSerializer(serializers.Serializer):
    """
    Register a new user. Optionally creates a new tenant or joins an
    existing one.
    """

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, default="")
    last_name = serializers.CharField(max_length=150, required=False, default="")
    role = serializers.ChoiceField(
        choices=CustomUser.Role.choices, default=CustomUser.Role.VIEWER
    )
    # Either supply an existing tenant id or a new tenant name + slug
    tenant_id = serializers.UUIDField(required=False, allow_null=True)
    tenant_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    tenant_slug = serializers.SlugField(max_length=255, required=False, allow_blank=True)

    def validate_username(self, value):
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value

    def validate(self, attrs):
        # Must provide either an existing tenant_id or a new tenant_name
        tid = attrs.get("tenant_id")
        tname = attrs.get("tenant_name", "").strip()
        if not tid and not tname and attrs.get("role") != "super_admin":
            raise serializers.ValidationError(
                "Provide either tenant_id or tenant_name/tenant_slug."
            )
        if tid and not Tenant.objects.filter(id=tid).exists():
            raise serializers.ValidationError({"tenant_id": "Tenant not found."})
        return attrs

    def create(self, validated_data):
        tenant_id = validated_data.get("tenant_id")
        tenant_name = validated_data.get("tenant_name", "").strip()
        tenant_slug = validated_data.get("tenant_slug", "").strip()

        if tenant_id:
            tenant = Tenant.objects.get(id=tenant_id)
        elif tenant_name:
            slug = tenant_slug or tenant_name.lower().replace(" ", "-")
            tenant, _ = Tenant.objects.get_or_create(
                slug=slug, defaults={"name": tenant_name}
            )
        else:
            tenant = None  # super-admin

        user = CustomUser.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            role=validated_data.get("role", CustomUser.Role.VIEWER),
            tenant=tenant,
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Authenticate by username/email + password -> return token."""

    username = serializers.CharField(required=False)
    email = serializers.CharField(required=False)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        email = attrs.get("email")
        password = attrs.get("password")

        if not username and not email:
            raise serializers.ValidationError("Please provide either username or email.")

        # Try to resolve email/username to an actual username
        resolved_username = None
        identifier = email or username

        # 1. Try finding by email
        user_obj = CustomUser.objects.filter(email__iexact=identifier).first()
        if user_obj:
            resolved_username = user_obj.username
        else:
            # 2. Try finding by username directly
            user_obj = CustomUser.objects.filter(username__iexact=identifier).first()
            if user_obj:
                resolved_username = user_obj.username

        # Fallback to the raw identifier if no user was found (to let Django authenticate raise appropriate error)
        if not resolved_username:
            resolved_username = identifier

        user = authenticate(
            username=resolved_username, password=password
        )
        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")
        attrs["user"] = user
        return attrs
