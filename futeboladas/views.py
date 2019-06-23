from django.conf import settings
from django.shortcuts import redirect, render, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views import generic
from .models import Player, Game
from .forms import SignUpForm, LoginForm, CreateGameForm, ManageProfileForm

def index(request):
    return HttpResponse("Hello, world. You're at the futeboladas app index page.")

def login_view(request):
    next = ""
    # TODO Support @login_required's "next" parameter for redirect 
    # when trying to access login_required view.
    if request.GET:  
        next = request.GET['next']

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            login(request, user)
            if next == "":
                return redirect('index')
            else:
                return redirect(next)
    else:
        form = LoginForm()
    return render(request, 'futeboladas/login.html', {'form': form})

def logout_view(request):
    # TODO if no user is currently logged in, display message saying that
    logout(request)
    return redirect('index')

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            return redirect('index')
    else:
        form = SignUpForm()
    return render(request, 'futeboladas/signup.html', {'form': form})

@login_required
def manage_profile(request):
    if request.method == 'POST':
        form = ManageProfileForm(request.POST, user=request.user)
        if form.is_valid():
            update_session_auth_hash(request, form.user)
            return redirect('profile')
    else:
        form = ManageProfileForm()
    return render(request, 'futeboladas/manage_profile.html', {'form': form})

@login_required
def create_game(request):
    if request.method == 'POST':
        form = CreateGameForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            # TODO redirect to created game page "futeboladas.com/games/new_game_name"
            return redirect('games')
    else:
        form = CreateGameForm()
    return render(request, 'futeboladas/create_game.html', {'form': form})

# TODO games view displays logged in players games, button to create new game and
#  if player clicks on a game he is redirected to futeboladas.com/games/game_name
#  where he can edit the games details
@login_required
def games(request):
    user = request.user
    #  Get player
    player = Player.objects.get(user_id=user.id)
    #  Get player's games list
    user_games = Game.objects.filter(admin=player.id)
    output = ', '.join([game.name for game in user_games])
    return HttpResponse(output)

@login_required
def game_detail(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    #return render(request, 'futeboladas/game_detail.html', {'game': game})
    return HttpResponse("You're looking at game %s." % game.name)

def friends(request):
    return HttpResponse("Friends Info Page")

def profile(request):
    return HttpResponse("Profile Info Page")