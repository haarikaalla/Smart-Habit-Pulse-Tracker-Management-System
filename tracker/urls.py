
from django.urls import path
from . import secure_views

urlpatterns = [
    path('', secure_views.dashboard, name='home'),
    path('api/v1/habits/', secure_views.habits, name='habits'),
    path('api/v1/habits/<int:habit_id>/', secure_views.habit_detail, name='habit_detail'),
    path('api/v1/summary/', secure_views.summary, name='summary'),
]
