from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('', views.placeholder_view, name='placeholder'),
]
