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
    return render(request, 'game_planner/index.html', {'user': request.user})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('game_planner:index')

    next = ""
    if request.GET:
        next = request.GET['next']

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            login(request, user)

            # redirect to correct page if there is a next arg
            if next == "":
                return redirect('game_planner:index')
            else:
                return redirect(next)
    else:
        form = LoginForm()
    return render(request, 'game_planner/login.html', {'form': form})

def logout_view(request):
    # TODO if no user is currently logged in, display message saying that
    logout(request)
    return redirect('game_planner:index')

def signup(request):
    if request.user.is_authenticated:
        return redirect('game_planner:index')
        
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            return redirect('game_planner:index')
    else:
        form = SignUpForm()
    return render(request, 'game_planner/signup.html', {'form': form})

@login_required
def manage_profile(request):
    if request.method == 'POST':
        form = ManageProfileForm(request.POST, user=request.user)
        if form.is_valid():
            update_session_auth_hash(request, form.user)
            return redirect('game_planner:profile')
    else:
        form = ManageProfileForm()
    return render(request, 'game_planner/manage_profile.html', {'form': form})

@login_required
def create_game(request):
    if request.method == 'POST':
        form = CreateGameForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('game_planner:game_detail', pk=form.pk)
    else:
        form = CreateGameForm()
    return render(request, 'game_planner/create_game.html', {'form': form})

class GamesListView(generic.ListView):
    model = Game
    template_name = "game_planner/games.html"
    context_object_name = 'games'

    def get_queryset(self):
        """
        Excludes any games that aren't administered by the logged in user.
        """
        user = self.request.user
        # Get player's games list
        player = Player.objects.get(user_id=user.id)

        games_dictionary = {}

        games_dictionary['administered'] = Game.objects.filter(admin=player.id)
        games_dictionary['invited'] = Game.objects.filter(players=player)
        games_dictionary['public'] = Game.objects.filter(private=False)

        return games_dictionary
    
class PlayersListView(generic.ListView):
    model = User
    template_name = "game_planner/players.html"
    context_object_name = 'players'

    def get_queryset(self):
        # Excludes logged in user from player list
        user = self.request.user
        # Get player's games list
        players = Player.objects.exclude(user_id=user.id)
        
        return players

@login_required
def game_detail(request, pk):
    game = get_object_or_404(Game, pk=pk)
    player = Player.objects.get(user_id=request.user.id)
    authorized = (player in game.players.all()) or (player == game.admin) or not game.private

    return render(request, 'game_planner/game_detail.html', {'game': game, 'authorized': authorized})

class ProfileView(generic.DetailView):
    model = User
    template_name = 'game_planner/profile.html'
    context_object_name = 'profile_user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add request user to context if user is currently logged in
        context['request_user'] = self.request.user

        # Add profile player friends list to context
        player = Player.objects.get(user_id=self.object.id)
        context['friends_list'] = list(player.friends.all())

        # Add profile player to context
        context['player'] = player
        
        # Add players friends list to context if user is currently logged in
        request_player = Player.objects.get(user_id=self.request.user.id)
        context['request_user_friends_list'] = list(request_player.friends.all())
        
        return context

@login_required
def add_friend(request, pk):
    player = Player.objects.get(user_id=request.user.id)
    player.friends.add(pk)
    return redirect('game_planner:profile', pk=pk)

@login_required
def remove_friend(request, pk):
    player = Player.objects.get(user_id=request.user.id)
    player.friends.remove(pk)
    return redirect('game_planner:profile', pk=pk)
