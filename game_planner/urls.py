from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views

app_name = 'game_planner'
urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup, name='signup'),
    path('players/', views.PlayersListView.as_view(), name='players'),
    path('profile/<str:pk>', login_required(views.ProfileView.as_view()), name='profile'),
    path('manage_profile/', views.manage_profile, name='manage_profile'),
    path('create_game/', views.create_game, name='create_game'),
    path('games/', login_required(views.GamesListView.as_view()), name='games'),
    path('games/<str:pk>/', views.game_detail, name='game_detail'),
    path('friends/', views.friends, name='friends'),
]