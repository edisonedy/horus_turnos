from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('panel/', views.dashboard, name='dashboard'),
    path('panel/reportes/', views.reportes, name='reportes'),
]
