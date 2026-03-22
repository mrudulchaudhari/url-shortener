"""
Views for user authentication and management.
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
import secrets

# Optional drf_spectacular support
try:
    from drf_spectacular.utils import extend_schema
except ImportError:
    # Fallback decorator that does nothing
    def extend_schema(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from .serializers import (
    UserRegistrationSerializer,
    UserSerializer,
    ChangePasswordSerializer,
    APIKeyRegenerateSerializer
)

User = get_user_model()


@extend_schema(
    request=UserRegistrationSerializer,
    responses={201: UserSerializer},
    description="Register a new user account"
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user.

    POST /auth/register
    """
    serializer = UserRegistrationSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'username': {'type': 'string'},
                'password': {'type': 'string'}
            }
        }
    },
    responses={200: UserSerializer},
    description="Login with username and password"
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Login user and return JWT tokens.

    POST /auth/login
    """
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'error': 'Please provide both username and password'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(username=username, password=password)

    if not user:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)

    return Response({
        'user': UserSerializer(user).data,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    })


@extend_schema(
    responses={200: UserSerializer},
    description="Get current user profile"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """
    Get current user profile.

    GET /auth/profile
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@extend_schema(
    request=ChangePasswordSerializer,
    responses={200: {'description': 'Password changed successfully'}},
    description="Change user password"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change user password.

    POST /auth/change-password
    """
    serializer = ChangePasswordSerializer(data=request.data)

    if serializer.is_valid():
        user = request.user

        # Check old password
        if not user.check_password(serializer.data.get('old_password')):
            return Response(
                {'error': 'Wrong password'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password
        user.set_password(serializer.data.get('new_password'))
        user.save()

        return Response({'message': 'Password changed successfully'})

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    responses={200: APIKeyRegenerateSerializer},
    description="Regenerate API key"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def regenerate_api_key(request):
    """
    Regenerate user's API key.

    POST /auth/regenerate-api-key
    """
    user = request.user
    user.api_key = secrets.token_urlsafe(32)
    user.save()

    return Response({
        'api_key': user.api_key
    })


@extend_schema(
    responses={200: UserSerializer},
    description="Get list of user's URLs"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_urls(request):
    """
    Get all URLs created by the current user.

    GET /auth/my-urls
    """
    from shortener.serializers import UrlSerializer

    urls = request.user.urls.filter(is_active=True).order_by('-created_at')

    # Pagination
    offset = int(request.query_params.get('offset', 0))
    limit = int(request.query_params.get('limit', 50))

    total = urls.count()
    page_urls = urls[offset:offset + limit]

    return Response({
        'count': total,
        'offset': offset,
        'limit': limit,
        'results': UrlSerializer(page_urls, many=True).data
    })
