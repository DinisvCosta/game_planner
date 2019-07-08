import json

from django.conf import settings
from django.shortcuts import redirect, render, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotFound
from django.views import generic

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from datetime import date, datetime

from .models import Player, Game, Notification, FriendRequest
from .forms import SignUpForm, LoginForm, CreateGameForm, ManageProfileForm, ManageGameForm

def index(request):
    params = {'user': request.user}

    if request.user.is_authenticated:
        player = Player.objects.get(user_id=request.user.id)
        notifications = Notification.objects.filter(player=player.id, read=False)
        params['notifications'] = notifications

    return render(request, 'game_planner/index.html', params)

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
            return redirect('game_planner:profile', pk=request.user.id)
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

@login_required
def manage_game(request, pk):
    game = get_object_or_404(Game, pk=pk)
    player = Player.objects.get(user_id=request.user.id)
    is_admin = (player == game.admin)

    if is_admin:

        if request.method == 'POST':
            form = ManageGameForm(request.POST, game=game)
            if form.is_valid():
                return redirect('game_planner:game_detail', pk=pk)
        else:
            form = ManageGameForm()
        
        return render(request, 'game_planner/manage_game.html', {'form': form})

    else:
        return HttpResponseForbidden()
        
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
    is_admin = (player == game.admin)

    return render(request, 'game_planner/game_detail.html', {'game': game, 'authorized': authorized, 'is_admin': is_admin})

class ProfileView(generic.DetailView):
    model = User
    template_name = 'game_planner/profile.html'
    context_object_name = 'profile_user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get Player object
        player = Player.objects.get(user_id=self.object.id)

        if self.request.user.is_authenticated:
            # Add authenticated user to context if user is currently logged in
            context['request_user'] = self.request.user

            # Add players friends list to context if user is currently logged in
            request_player = Player.objects.get(user_id=self.request.user.id)

            # Add are_friends flag to context
            context['are_friends'] = player in list(request_player.friends.all())

            # Check if there's an existing active outgoing request
            outgoing_request = FriendRequest.objects.filter(request_from=request_player, request_to=player, state__isnull=True)
            context['outgoing_request'] = outgoing_request

            # Check if there's an existing active incoming request
            incoming_request = FriendRequest.objects.filter(request_from=player, request_to=request_player, state__isnull=True)
            context['incoming_request'] = incoming_request

            # Add games list containing: public games, games authenticated user is also invited to, games authenticated user is admin
            games = Game.objects.filter(players=player, private=False) \
                                    | Game.objects.filter(players=player).filter(players=request_player) \
                                    | Game.objects.filter(players=player, admin=request_player)
            games = games.distinct()

        else:
            # Add public games
            games = Game.objects.filter(players=player, private=False)

        context['past_games'] = games.filter(when__lte=datetime.now())
        context['upcoming_games'] = games.filter(when__gt=datetime.now())
        
        # Add profile player to context
        context['player'] = player

        # Add profile player friends list to context
        context['friends_list'] = list(player.friends.all()) 
        
        return context

@login_required
def add_friend(request, pk):
    # Check if there's already a request
    requester_player = Player.objects.get(user_id=request.user.id)
    requested_player = Player.objects.get(user_id=pk)

    active_request = FriendRequest.objects.filter(request_from=requester_player, request_to=requested_player, state__isnull=True)
    
    if active_request:
        return HttpResponseForbidden()
    else:
        request_datetime = datetime.now()

        # Create friend request and send notification to user
        friend_request = FriendRequest(request_from=requester_player,
                                        request_to=requested_player,
                                        request_datetime=request_datetime)
        friend_request.save()
    
        notification = Notification(notification_type="SENT_FRIEND_REQUEST",
                                    text=requester_player.user.username + " wants to be your friend.",
                                    creation_datetime=request_datetime,
                                    target_url='game_planner:friend_requests',
                                    player_id=requested_player.id)
        notification.save()
        return redirect('game_planner:profile', pk=pk)

@login_required
def remove_friend(request, pk):
    player = Player.objects.get(user_id=request.user.id)
    player_to_remove = Player.objects.get(user_id=pk)
    player.friends.remove(player_to_remove.pk)

    # Remove "X accepted your friend request." notification from the requester if it hasn't been read yet
    notification = Notification.objects.filter(notification_type="ADDED_AS_FRIEND",
                                                text=player.user.username + " accepted your friend request.",
                                                player_id=player_to_remove,
                                                read=False)
    
    if notification:
        notification.delete()

    return redirect('game_planner:profile', pk=player_to_remove.pk)

def notification_read_common(user_id, notification_id):
    request_player = Player.objects.get(user_id=user_id)
    notification = Notification.objects.get(pk=notification_id)

    if notification.player_id == request_player.id:
        notification.read = True
        notification.read_datetime = datetime.now()
        notification.save()
        
        return True
    else:
        return False

@login_required
def notification_read(request):
    request_json = json.loads(request.body)
    notification_id = request_json['notification_id']

    result = notification_read_common(request.user.id, notification_id)

    if(result):
        return HttpResponse("OK")
    else:
        return HttpResponseNotFound()

@login_required
def friend_requests(request):

    if request.GET and request.GET['notif_id']:
        notification_read_common(request.user.id, request.GET['notif_id'])

    # Deal with friend request "Confirm", "Delete", "Cancel friend request" button press
    if request.method == 'POST':
        request_json = json.loads(request.body)

        friend_request = FriendRequest.objects.get(pk=request_json['friend_request'])

        # Receiving player confirms or deletes friend request
        if request.user.id == friend_request.request_to.user.id:
            if(request_json['state'] == "accepted"):
                request_datetime = datetime.now()

                # Add to player's friends list and send notification to new friend
                player = Player.objects.get(user_id=request.user.id)
                player.friends.add(friend_request.request_from.user.id)

                notification = Notification(notification_type="ADDED_AS_FRIEND",
                                            text=player.user.username + " accepted your friend request.",
                                            creation_datetime=request_datetime,
                                            player_id=friend_request.request_from.user.id)
                notification.save()

                # Update friend_request state and save datetime of action_taken
                friend_request.state = "ACCEPTED"
                friend_request.action_taken_datetime = request_datetime
                friend_request.save()

                # Remove notification from requested player if it still is unread
                notification = Notification.objects.filter(notification_type="SENT_FRIEND_REQUEST",
                                                            creation_datetime=friend_request.request_datetime,
                                                            player_id=friend_request.request_to,
                                                            read=False)
                if notification:
                    notification.delete()

                return HttpResponse("OK")

            elif(request_json['state'] == "declined"):
                # Update friend_request state and save datetime of action_taken
                friend_request.state = "DECLINED"
                friend_request.action_taken_datetime = datetime.now()
                friend_request.save()

                # Remove notification from requested player if it still is unread
                notification = Notification.objects.filter(notification_type="SENT_FRIEND_REQUEST",
                                                            creation_datetime=friend_request.request_datetime,
                                                            player_id=friend_request.request_to,
                                                            read=False)
                if notification:
                    notification.delete()

                return HttpResponse("OK")
        
        # Sender cancels friend request
        elif request.user.id == friend_request.request_from.user.id:
            # Update friend_request state and save datetime of action_taken
            if(request_json['state'] == 'cancel'):
                friend_request.state = 'CANCELED'
                friend_request.action_taken_datetime = datetime.now()
                friend_request.save()
                
                # Remove notification from requested player
                notification = Notification.objects.filter(notification_type="SENT_FRIEND_REQUEST",
                                                            creation_datetime=friend_request.request_datetime,
                                                            player_id=friend_request.request_to,
                                                            read=False)
                if notification:
                    notification.delete()
                
                return HttpResponse("OK")
                
        else:
            return HttpResponseForbidden()
    
    # Display Friend Requests page
    else:
        request_player = Player.objects.get(user_id=request.user.id)

        # friend requests list only shows requests that are still pending received by authenticated user
        friend_requests = FriendRequest.objects.filter(request_to=request_player, state__isnull=True)

        params = {}
        params['friend_requests'] = friend_requests

        return render(request, 'game_planner/friend_requests.html', params)