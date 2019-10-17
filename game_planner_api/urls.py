from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from game_planner_api import views

urlpatterns = [
    path('players/', views.PlayerList.as_view()),
    path('players/<str:username>/', views.PlayerDetail.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)