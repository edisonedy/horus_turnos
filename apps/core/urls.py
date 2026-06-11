from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('demo/', views.demo, name='demo'),
    path('panel/', views.dashboard, name='dashboard'),
]
