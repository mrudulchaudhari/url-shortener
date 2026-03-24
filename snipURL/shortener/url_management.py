"""
URL management views for editing, deleting, and bulk operations.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

# Optional drf_spectacular support
try:
    from drf_spectacular.utils import extend_schema
except ImportError:
    def extend_schema(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from .models import ShortenedURL
from .serializers import UrlSerializer
from .cache import invalidate_cache


@extend_schema(
    request=UrlSerializer,
    responses={200: UrlSerializer},
    description="Update a URL's destination or settings"
)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_url(request, code):
    """
    Update a URL (owner only).

    PUT/PATCH /<code>/edit
    """
    url_obj = get_object_or_404(Url, code=code)

    # Check ownership
    if url_obj.user != request.user:
        return Response(
            {'error': 'You do not have permission to edit this URL'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Update fields
    if 'original_url' in request.data:
        url_obj.original_url = request.data['original_url']

    if 'expires_at' in request.data:
        url_obj.expires_at = request.data.get('expires_at')

    if 'is_public' in request.data:
        url_obj.is_public = request.data['is_public']

    if 'is_active' in request.data:
        url_obj.is_active = request.data['is_active']

    url_obj.save()

    # Invalidate cache
    invalidate_cache(code)

    return Response(UrlSerializer(url_obj).data)


@extend_schema(
    responses={204: None},
    description="Delete a URL (soft delete)"
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_url(request, code):
    """
    Delete a URL (owner only).

    DELETE /<code>
    """
    url_obj = get_object_or_404(Url, code=code)

    # Check ownership
    if url_obj.user != request.user:
        return Response(
            {'error': 'You do not have permission to delete this URL'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Soft delete
    url_obj.is_active = False
    url_obj.save()

    # Invalidate cache
    invalidate_cache(code)

    return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'codes': {
                    'type': 'array',
                    'items': {'type': 'string'}
                },
                'action': {
                    'type': 'string',
                    'enum': ['delete', 'activate', 'deactivate']
                }
            }
        }
    },
    responses={200: {'description': 'Bulk operation completed'}},
    description="Bulk operations on multiple URLs"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_operations(request):
    """
    Perform bulk operations on URLs.

    POST /urls/bulk
    Body: {
        "codes": ["code1", "code2", ...],
        "action": "delete" | "activate" | "deactivate"
    }
    """
    codes = request.data.get('codes', [])
    action = request.data.get('action')

    if not codes or not action:
        return Response(
            {'error': 'codes and action are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get URLs owned by user
    urls = Url.objects.filter(
        code__in=codes,
        user=request.user
    )

    count = urls.count()

    if action == 'delete' or action == 'deactivate':
        urls.update(is_active=False)
    elif action == 'activate':
        urls.update(is_active=True)
    else:
        return Response(
            {'error': 'Invalid action'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Invalidate cache for all affected URLs
    for code in codes:
        invalidate_cache(code)

    return Response({
        'message': f'{action.capitalize()}d {count} URLs',
        'count': count
    })


@extend_schema(
    responses={200: {'description': 'Export data'}},
    description="Export user's URLs to JSON/CSV"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_urls(request):
    """
    Export all user's URLs.

    GET /urls/export?format=json|csv
    """
    export_format = request.query_params.get('format', 'json')

    urls = request.user.urls.filter(is_active=True)

    if export_format == 'csv':
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="urls.csv"'

        writer = csv.writer(response)
        writer.writerow(['Code', 'Original URL', 'Created At', 'Expires At', 'Total Clicks'])

        for url in urls:
            try:
                clicks = url.stats.total_clicks
            except:
                clicks = 0

            writer.writerow([
                url.code,
                url.original_url,
                url.created_at,
                url.expires_at or '',
                clicks
            ])

        return response
    else:
        # JSON export
        return Response({
            'urls': UrlSerializer(urls, many=True).data
        })
