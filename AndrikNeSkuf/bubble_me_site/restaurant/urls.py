from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('news/<int:pk>/', views.news_detail, name='news_detail'),
    path('order/', views.create_order, name='create_order'),
    path('order/status/', views.order_status, name='order_status'),
    path('confirm/<str:token>/', views.confirm_email, name='confirm_email'),
]
