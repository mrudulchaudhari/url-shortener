"""
URL patterns for accounts app.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register', views.register, name='register'),
    path('login', views.login, name='login'),
    path('profile', views.profile, name='profile'),
    path('change-password', views.change_password, name='change_password'),
    path('regenerate-api-key', views.regenerate_api_key, name='regenerate_api_key'),
    path('my-urls', views.my_urls, name='my_urls'),
    path('token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
]
