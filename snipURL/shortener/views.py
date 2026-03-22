from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, FileResponse
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_page
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from io import BytesIO

# Optional drf_spectacular support
try:
    from drf_spectacular.utils import extend_schema, OpenApiResponse
except ImportError:
    def extend_schema(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    class OpenApiResponse:
        def __init__(self, *args, **kwargs):
            pass

from .models import Url, URLStats
from .serializers import (
    ShortenURLSerializer,
    ShortenURLResponseSerializer,
    StatsResponseSerializer
)
from .utils import (
    encode_base62,
    generate_qr_code,
    qr_code_to_bytes
)
from .cache import (
    cache_url,
    get_cached_url,
    increment_click_redis,
    get_buffered_click_count
)


@extend_schema(
    request=ShortenURLSerializer,
    responses={
        201: ShortenURLResponseSerializer,
        400: OpenApiResponse(description="Bad request - invalid URL or custom code"),
        409: OpenApiResponse(description="Conflict - custom code already exists")
    },
    description="Create a shortened URL with optional custom alias and expiration"
)
@csrf_exempt
@api_view(['POST'])
def shorten_url(request):
    """
    Create a shortened URL.

    POST /shorten
    """
    serializer = ShortenURLSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    validated_data = serializer.validated_data
    normalized_url = validated_data['url']
    custom_code = validated_data.get('custom')
    expires_at_dt = validated_data.get('expires_at')

    # Get user if authenticated
    user = request.user if request.user.is_authenticated else None

    # Create URL entry
    with transaction.atomic():
        if custom_code:
            # Use custom code directly
            url_obj = Url.objects.create(
                code=custom_code,
                original_url=normalized_url,
                expires_at=expires_at_dt,
                user=user
            )
        else:
            # Create with temporary code, then update with base62 encoded ID
            url_obj = Url.objects.create(
                code='tmp',
                original_url=normalized_url,
                expires_at=expires_at_dt,
                user=user
            )
            # Generate base62 code from ID
            url_obj.code = encode_base62(url_obj.id)
            url_obj.save()

        # Initialize stats entry
        URLStats.objects.create(url=url_obj)

    # Generate short URL
    short_url = f"http://{settings.HOST}/{url_obj.code}"

    # Generate QR code
    qr_base64 = generate_qr_code(short_url)

    # Cache the URL
    cache_url(url_obj.code, {
        'url_id': url_obj.id,
        'original_url': url_obj.original_url,
        'expires_at': url_obj.expires_at,
        'is_active': url_obj.is_active
    })

    response_serializer = ShortenURLResponseSerializer({
        'code': url_obj.code,
        'short_url': short_url,
        'qr_base64': qr_base64
    })

    return Response(response_serializer.data, status=status.HTTP_201_CREATED)


def redirect_url(request, code):
    """
    Redirect to original URL - Optimized for speed.

    GET /<code>

    Returns:
        - 302 redirect to original URL
        - 404 if not found
        - 410 if expired
    """
    # Fast path: Check cache
    cached = get_cached_url(code)

    if cached:
        # Quick validation checks
        if not cached['is_active']:
            return HttpResponse('URL has been deactivated', status=410)

        if cached['expires_at']:
            expires_at = datetime.fromisoformat(cached['expires_at'])
            if timezone.now() > expires_at:
                return HttpResponse('URL has expired', status=410)

        # Increment Redis buffer (fire and forget - don't wait)
        try:
            increment_click_redis(cached['url_id'])
        except:
            pass  # Don't let analytics slow down redirects

        # Fast redirect
        return redirect(cached['original_url'])

    # Cold path: Query database (select only needed fields)
    try:
        url_obj = Url.objects.only('id', 'original_url', 'expires_at', 'is_active').get(code=code)
    except Url.DoesNotExist:
        return HttpResponse('URL not found', status=404)

    # Quick validation
    if not url_obj.is_active:
        return HttpResponse('URL has been deactivated', status=410)

    if url_obj.expires_at and timezone.now() > url_obj.expires_at:
        return HttpResponse('URL has expired', status=410)

    # Cache for next time (non-blocking)
    try:
        cache_url(code, {
            'url_id': url_obj.id,
            'original_url': url_obj.original_url,
            'expires_at': url_obj.expires_at,
            'is_active': url_obj.is_active
        })
    except:
        pass  # Don't let cache failures slow down redirects

    # Increment Redis buffer (fire and forget)
    try:
        increment_click_redis(url_obj.id)
    except:
        pass

    # Fast redirect
    return redirect(url_obj.original_url)


def qr_code_image(request, code):
    """
    Return QR code PNG image for a short URL.

    GET /<code>/qr.png

    Returns:
        - PNG image
        - 404 if URL not found
    """
    # Check cache first
    cached = get_cached_url(code)

    if not cached:
        # Query database
        try:
            url_obj = Url.objects.get(code=code)
        except Url.DoesNotExist:
            return HttpResponse('URL not found', status=404)

    # Generate short URL
    short_url = f"http://{settings.HOST}/{code}"

    # Generate QR code
    qr_base64 = generate_qr_code(short_url)

    # Convert to bytes
    qr_bytes = qr_code_to_bytes(qr_base64)

    # Return as image
    return HttpResponse(qr_bytes, content_type='image/png')


def health_check(request):
    """
    Health check endpoint for load balancers.

    GET /healthz

    Returns:
        200 OK
    """
    return HttpResponse('OK', status=200)


@extend_schema(
    responses={200: StatsResponseSerializer},
    description="Get global statistics about the URL shortener service"
)
@api_view(['GET'])
def stats(request):
    """
    Return statistics about the service.

    GET /stats
    """
    total_urls = Url.objects.filter(is_active=True).count()
    buffered_clicks = get_buffered_click_count()

    serializer = StatsResponseSerializer({
        'total_urls': total_urls,
        'buffered_clicks': buffered_clicks
    })

    return Response(serializer.data)
