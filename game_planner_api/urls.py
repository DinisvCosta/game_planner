from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from game_planner_api import views

urlpatterns = [
    path('players/', views.PlayerList.as_view()),
    path('players/<str:username>/', views.PlayerDetail.as_view(), name='player-detail'),

    path('games/', views.GameList.as_view()),
    path('games/<str:game_id>/', views.GameDetail.as_view(), name='game-detail'),

    path('notifications/', views.NotificationList.as_view()),
    path('notifications/<int:id>', views.NotificationDetail.as_view()),

]

urlpatterns = format_suffix_patterns(urlpatterns)