
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('add/', views.add_habit, name='add_habit'),
    path('api/habits/', views.get_habits, name='get_habits'),
    path('api/habits/<int:id>/', views.update_habit, name='update_habit'),
    path('api/dashboard/', views.dashboard_data, name='dashboard'),
]
