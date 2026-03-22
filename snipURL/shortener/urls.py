"""
URL patterns for the shortener app.
"""
from django.urls import path
from . import views
from . import url_management

app_name = 'shortener'

urlpatterns = [
    # API endpoints
    path('shorten', views.shorten_url, name='shorten'),
    path('healthz', views.health_check, name='health'),
    path('stats', views.stats, name='stats'),

    # URL management
    path('urls/bulk', url_management.bulk_operations, name='bulk_operations'),
    path('urls/export', url_management.export_urls, name='export_urls'),
    path('<str:code>/edit', url_management.update_url, name='update_url'),
    path('<str:code>/delete', url_management.delete_url, name='delete_url'),

    # Redirect endpoints (must be last to avoid conflicts)
    path('<str:code>/qr.png', views.qr_code_image, name='qr_code'),
    path('<str:code>', views.redirect_url, name='redirect'),
]
