import json

from django.conf import settings
from django.core.serializers import serialize
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import redirect, render, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotFound, JsonResponse
from django.views import generic
from django.forms.models import model_to_dict
from django.utils import timezone

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from datetime import date, datetime

from game_planner_api.models import Player, Game, Notification, FriendRequest, GameParticipationRequest, NotificationType
from .forms import SignUpForm, LoginForm, CreateGameForm, ManageProfileForm, ManageGameForm

def index(request):
    params = {'user': request.user}

    if request.user.is_authenticated:
        notifications = Notification.objects.filter(user=request.user, read=False)
        params['notifications'] = notifications

    return render(request, 'game_planner_app/index.html', params)

def login_view(request):
    if request.user.is_authenticated:
        return redirect('game_planner_app:index')

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
                return redirect('game_planner_app:index')
            else:
                return redirect(next)
    else:
        form = LoginForm()
    return render(request, 'game_planner_app/login.html', {'form': form})

def logout_view(request):
    # TODO if no user is currently logged in, display message saying that
    logout(request)
    return redirect('game_planner_app:index')

def signup(request):
    if request.user.is_authenticated:
        return redirect('game_planner_app:index')
        
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            return redirect('game_planner_app:index')
    else:
        form = SignUpForm()
    return render(request, 'game_planner_app/signup.html', {'form': form})

@login_required
def manage_profile(request):
    if request.method == 'POST':
        form = ManageProfileForm(request.POST, user=request.user)
        if form.is_valid():
            update_session_auth_hash(request, form.user)
            return redirect('game_planner_app:profile', pk=request.user.id)
    else:
        form = ManageProfileForm()
    return render(request, 'game_planner_app/manage_profile.html', {'form': form})

@login_required
def create_game(request):
    if request.method == 'POST':
        form = CreateGameForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('game_planner_app:game_detail', pk=form.pk)
    else:
        form = CreateGameForm()
    return render(request, 'game_planner_app/create_game.html', {'form': form})

@login_required
def manage_game(request, pk):

    if request.GET and request.GET['notif_id']:
        notification_read_common(request.user, request.GET['notif_id'])

    game = get_object_or_404(Game, pk=pk)
    is_admin = (request.user == game.admin)

    participation_requests = GameParticipationRequest.objects.filter(request_to_game=game, state__isnull=True)
    
    if is_admin:

        if request.method == 'POST':
            form = ManageGameForm(request.POST, game=game)
            if form.is_valid():
                return redirect('game_planner_app:game_detail', pk=pk)
        else:
            form = ManageGameForm()
        
        return render(request, 'game_planner_app/manage_game.html', {'form': form, 'participation_requests': participation_requests})

    else:
        return HttpResponseForbidden()
        
class GamesListView(generic.ListView):
    model = Game
    template_name = "game_planner_app/games.html"
    context_object_name = 'games'

    def get_queryset(self):
        """
        Excludes any games that aren't administered by the logged in user.
        """
        qs = super().get_queryset()

        user = self.request.user
        # Get player's games list
        player = Player.objects.get(user=user)

        games_dictionary = {}

        games_dictionary['administered'] = qs.filter(admin=user)
        games_dictionary['invited'] = qs.filter(players=player)
        games_dictionary['public'] = qs.filter(private=False)

        return games_dictionary
    
class PlayersListView(generic.ListView):
    model = Player
    template_name = "game_planner_app/players.html"
    context_object_name = 'players'

    def get_queryset(self):
        qs = super().get_queryset()
        players = qs

        # Excludes logged in user from player list
        user = self.request.user
        if self.request.user and self.request.user.is_authenticated:
            players = qs.exclude(user=user)
        
        return players

def game_detail(request, pk):
    game = get_object_or_404(Game, pk=pk)

    if request.user and request.user.is_authenticated:
        player = Player.objects.get(user=request.user)
        is_admin = (request.user == game.admin)
        authorized = (player in game.players.all()) or is_admin or not game.private

        participating = (player in game.players.all()) or is_admin

        active_participation_request = GameParticipationRequest.objects.filter(request_from=player, request_to_game=game, state__isnull=True)

        return render(request, 'game_planner_app/game_detail.html', {'game': game,
                                                                 'authorized': authorized,
                                                                 'is_admin': is_admin,
                                                                 'participating': participating,
                                                                 'active_participation_request': active_participation_request})
    
    else:
        return render(request, 'game_planner_app/game_detail.html', {'game': game})

class ProfileView(generic.DetailView):
    model = User
    template_name = 'game_planner_app/profile.html'
    context_object_name = 'profile_user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get Player object
        player = Player.objects.get(user=self.object)

        if self.request.user.is_authenticated:
            # Add authenticated user to context if user is currently logged in
            context['request_user'] = self.request.user

            # Add players friends list to context if user is currently logged in
            request_player = Player.objects.get(user=self.request.user)

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
                                    | Game.objects.filter(players=player, admin=self.request.user)
            games = games.distinct()

        else:
            # Add public games
            games = Game.objects.filter(players=player, private=False)

        context['past_games'] = games.filter(when__lte=timezone.now())
        context['upcoming_games'] = games.filter(when__gt=timezone.now())
        
        # Add profile player to context
        context['player'] = player

        # Add profile player friends list to context
        context['friends_list'] = list(player.friends.all()) 
        
        return context

def notification_read_common(user, notification_id):
    notification = Notification.objects.get(pk=notification_id)

    if notification.user == user and notification.read == False:
        notification.read = True
        notification.read_datetime = timezone.now()
        notification.save()
        
        return True
    else:
        return False

@login_required
def notification_read(request):
    request_json = json.loads(request.body)
    notification_id = request_json['notification_id']

    result = notification_read_common(request.user, notification_id)

    if(result):
        return HttpResponse("OK")
    else:
        return HttpResponseNotFound()

@login_required
def mark_all_as_read(request):
    unread_notifications = Notification.objects.filter(user=request.user,
                                                    read=False)
    
    success = True

    for notif in unread_notifications:
        success = notification_read_common(request.user, notif.id)

    if(success):
        return HttpResponse("OK")
    else:
        return HttpResponseNotFound()

@login_required
def friend_requests(request):

    if request.GET and request.GET['notif_id']:
        notification_read_common(request.user, request.GET['notif_id'])

    # Deal with friend request "Add Friend", "Remove Friend", "Confirm", "Delete", "Cancel friend request" button press
    if request.method == 'POST':
        request_json = json.loads(request.body)
        
        if 'state' in request_json:
            friend_request = FriendRequest.objects.get(pk=request_json['pk'])

            # Receiving player confirms or deletes friend request
            if request.user == friend_request.request_to.user:
                if request_json['state'] == "accepted":
                    request_datetime = timezone.now()

                    # Add to player's friends list and send notification to new friend
                    player = Player.objects.get(user=request.user)
                    player.friends.add(friend_request.request_from)

                    notification = Notification(notification_type=NotificationType.ADDED_AS_FRIEND.value,
                                                creation_datetime=request_datetime,
                                                sender=player.user,
                                                user=friend_request.request_from.user)
                    notification.save()

                    # Update friend_request state and save datetime of action_taken
                    friend_request.state = "ACCEPTED"
                    friend_request.action_taken_datetime = request_datetime
                    friend_request.save()

                    # Mark friend request notification as read if it still is unread
                    friend_request_notification = Notification.objects.filter(notification_type=NotificationType.FRIEND_REQ.value,
                                                                creation_datetime=friend_request.request_datetime,
                                                                user=friend_request.request_to.user,
                                                                read=False)
                    if friend_request_notification:
                        notification_read_common(request.user, friend_request_notification[0].pk)

                    return HttpResponse("OK")

                elif request_json['state'] == "declined":
                    # Update friend_request state and save datetime of action_taken
                    friend_request.state = "DECLINED"
                    friend_request.action_taken_datetime = timezone.now()
                    friend_request.save()

                    # Mark friend request notification as read if it still is unread
                    notification = Notification.objects.filter(notification_type=NotificationType.FRIEND_REQ.value,
                                                                creation_datetime=friend_request.request_datetime,
                                                                user=friend_request.request_to.user,
                                                                read=False)
                    if notification:
                        notification_read_common(request.user, notification[0].pk)

                    return HttpResponse("OK")
            
            # Sender cancels friend request
            elif request.user == friend_request.request_from.user:
                # Update friend_request state and save datetime of action_taken
                if request_json['state'] == 'cancel':
                    friend_request.state = 'CANCELED'
                    friend_request.action_taken_datetime = timezone.now()
                    friend_request.save()
                    
                    # Remove notification from requested player
                    notification = Notification.objects.filter(notification_type=NotificationType.FRIEND_REQ.value,
                                                                creation_datetime=friend_request.request_datetime,
                                                                user=friend_request.request_to.user,
                                                                read=False)
                    if notification:
                        notification.delete()
                    
                    return HttpResponse("OK")
                    
            else:
                return HttpResponseForbidden()
        
        elif 'action' in request_json:
            # request.user removes friend
            if request_json['action'] == 'remove_friend':
                player = Player.objects.get(user=request.user)
                player_to_remove = Player.objects.get(user_id=request_json['pk'])
                player.friends.remove(player_to_remove)

                # Remove "X accepted your friend request." notification from the requester if it hasn't been read yet
                notification = Notification.objects.filter(notification_type=NotificationType.ADDED_AS_FRIEND.value,
                                                            user=player_to_remove.user,
                                                            read=False)
                
                if notification:
                    notification.delete()

                return redirect('game_planner_app:profile', pk=player_to_remove.user_id)
            
    # Display Friend Requests page
    else:
        request_player = Player.objects.get(user=request.user)

        # friend requests list only shows requests that are still pending received by authenticated user
        friend_requests = FriendRequest.objects.filter(request_to=request_player, state__isnull=True)

        params = {}
        params['friend_requests'] = friend_requests

        return render(request, 'game_planner_app/friend_requests.html', params)

@login_required
def manage_participation(request):
    # Deal with participation request "Add to Game, "Delete", "Cancel participation request" button press
    if request.method == 'POST':
        request_json = json.loads(request.body)

        if 'state' in request_json:
            participation_request = GameParticipationRequest.objects.get(pk=request_json['pk'])

            # Game admin confirms or deletes game participation request
            if request.user == participation_request.request_to_game.admin:
                if request_json['state'] == "accepted":
                    request_datetime = timezone.now()

                    # Add player to game players list and send notification to player
                    participation_request.request_to_game.players.add(participation_request.request_from)

                    notification = Notification(notification_type=NotificationType.ADDED_TO_GAME.value,
                                                creation_datetime=request_datetime,
                                                game=participation_request.request_to_game,
                                                user=participation_request.request_from.user)
                    notification.save()

                    # Update participation_request state and save datetime of action_taken
                    participation_request.state = "ACCEPTED"
                    participation_request.action_taken_datetime = request_datetime
                    participation_request.save()

                    # Mark game participation request notification as read if it still is unread
                    notification = Notification.objects.filter(notification_type=NotificationType.PARTICIPATION_REQ.value,
                                                            creation_datetime=participation_request.request_datetime,
                                                            user=participation_request.request_to_game.admin,
                                                            read=False)
                    if notification:
                        notification_read_common(request.user, notification[0].pk)

                    return HttpResponse("OK")
                
                elif request_json['state'] == "declined":
                    # Update participation_request state and save datetime of action_taken
                    participation_request.state = "DECLINED"
                    participation_request.action_taken_datetime = timezone.now()
                    participation_request.save()

                    # Mark game participation request notification as read if it still is unread
                    notification = Notification.objects.filter(notification_type=NotificationType.PARTICIPATION_REQ.value,
                                                            creation_datetime=participation_request.request_datetime,
                                                            user=participation_request.request_to_game.admin,
                                                            read=False)
                    if notification:
                        notification_read_common(request.user, notification[0].pk)

                    return HttpResponse("OK")
            
            # Requester cancels game participation request
            elif request.user == participation_request.request_from.user:

                # Update participation_request state and save datetime of action_taken
                if request_json['state'] == "cancel":
                    participation_request.state = "CANCELED"
                    participation_request.action_taken_datetime = timezone.now()
                    participation_request.save()

                    # Remove notification from game admin if it still is unread
                    notification = Notification.objects.filter(notification_type=NotificationType.PARTICIPATION_REQ.value,
                                                            creation_datetime=participation_request.request_datetime,
                                                            user=participation_request.request_to_game.admin,
                                                            read=False)
                    if notification:
                        notification.delete()

                    return HttpResponse("OK")
                    
            else:
                return HttpResponseForbidden()
        
        elif 'action' in request_json:
            if request_json['action'] == 'request_participation':
                # Check if there's already a request
                player = Player.objects.get(user=request.user)
                game = Game.objects.get(game_id=request_json['pk'])

                active_request = GameParticipationRequest.objects.filter(request_from=player, request_to_game=game, state__isnull=True)
                
                if active_request:
                    return HttpResponseForbidden()
                else:
                    request_datetime = timezone.now()

                    # Create game participation request and send notification to game admin
                    participation_request = GameParticipationRequest(request_from=player,
                                                                        request_to_game=game,
                                                                        request_datetime=request_datetime)
                    participation_request.save()
                
                    notification = Notification(notification_type=NotificationType.PARTICIPATION_REQ.value,
                                                creation_datetime=request_datetime,
                                                sender=request.user,
                                                game=game,
                                                user=game.admin)
                    notification.save()
                    return redirect('game_planner_app:game_detail', pk=request_json['pk'])