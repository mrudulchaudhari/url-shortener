"""
URL configuration for snipURL project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from shortener.frontend_views import index, api_welcome

urlpatterns = [
    path("admin/", admin.site.urls),

    # Frontend
    path("", index, name="home"),  # Root path - Beautiful frontend
    path("app/", index, name="frontend"),
    path("api/", api_welcome, name="api_welcome"),  # API info

    # API endpoints
    path("auth/", include("accounts.urls")),
    path("analytics/", include("analytics.urls")),
    path("", include("shortener.urls")),
]

# Add API documentation if drf_spectacular is available
try:
    from drf_spectacular.views import (
        SpectacularAPIView,
        SpectacularSwaggerView,
        SpectacularRedocView
    )
    urlpatterns.insert(2, path("api/schema/", SpectacularAPIView.as_view(), name="schema"))
    urlpatterns.insert(3, path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"))
    urlpatterns.insert(4, path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"))
except ImportError:
    pass
