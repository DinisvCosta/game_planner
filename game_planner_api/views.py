import re

from rest_framework import generics
from rest_framework import permissions
from rest_framework import exceptions
from rest_framework import status
from rest_framework.response import Response

from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone

from game_planner_api.serializers import PlayerSerializer, GameSerializer, GameExSerializer, NotificationSerializer, FriendshipSerializer, GameParticipationRequestSerializer
from .models import Player, Game, NotificationType, Notification, Friendship, GameParticipationRequest

class IndirectModelMixin:

    # TODO: use GenericAPIView::super() instead of dupe code
    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}

        indirect_field = get_object_or_404(self.indirect_model, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, indirect_field)
        
        if indirect_field:
            indirect_lookup = {self.indirect_lookup_field: indirect_field}
            obj = get_object_or_404(queryset, **indirect_lookup)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

class PlayerList(generics.ListAPIView):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer

class PlayerDetail(IndirectModelMixin,
                   generics.RetrieveUpdateAPIView):
    lookup_field = 'username'
    indirect_lookup_field = 'user'
    indirect_model = User

    queryset = Player.objects.all()
    serializer_class = PlayerSerializer

    # override parent class put method so that HTTP PUT request returns 405 Method not allowed (only PATCH requests allowed)
    def put(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def perform_update(self, serializer):
        request_json = self.request.data

        user = self.request.user

        # Authenticated user removes {username} as friend
        if 'action' in request_json and request_json['action'] == "remove_friend":

            requester_player = Player.objects.get(user=user)
            user_to_remove = User.objects.get(username=self.kwargs['username'])

            player_to_remove = Player.objects.get(user=user_to_remove)

            are_friends = player_to_remove in requester_player.friends.all()

            if not are_friends:
                raise exceptions.NotFound(detail="You are not %s's friend." % self.kwargs['username'])

            requester_player.friends.remove(player_to_remove)

            # Remove "X accepted your friend request." notification from the requester if it hasn't been read yet
            notification = Notification.objects.filter(notification_type=NotificationType.ADDED_AS_FRIEND.value,
                                                        user=player_to_remove.user,
                                                        read=False)
            
            if notification:
                notification.delete()

            serializer.save()
        
        # Authenticated player updates his info
        if 'action' in request_json and request_json['action'] == "update_player":

            user_to_update = User.objects.get(username=self.kwargs['username'])

            if not user_to_update == user:
                raise exceptions.PermissionDenied()

            if 'first_name' in request_json and len(request_json['first_name']) > 30:
                raise exceptions.ParseError(detail="'first_name' must be a string with 30 characters or fewer.")
            
            if 'last_name' in request_json and len(request_json['last_name']) > 150:
                raise exceptions.ParseError(detail="'last_name' must be a string with 150 characters or fewer.")

            if 'email' in request_json and request_json['email'] and not re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", request_json['email']):
                raise exceptions.ParseError(detail="Invalid 'email' address.")
            
            if request_json['first_name']:
                user.first_name = request_json['first_name']

            if request_json['last_name']:
                user.last_name = request_json['last_name']

            if request_json['email']:
                user.email = request_json['email']

            user.save()

        else:
            raise exceptions.ParseError()

class GameList(generics.ListAPIView):
    queryset = Game.objects.all()
    serializer_class = GameSerializer

    def get_queryset(self):
        """
        Excludes games that user does not have permission to see.
        """
        qs = super().get_queryset()

        filter_q = Q(private=False)
        
        if self.request.user and self.request.user.is_authenticated:
            user = self.request.user

            # Get player's games list
            player = Player.objects.get(user=user)

            filter_q = filter_q | Q(admin=user) | Q(players=player)
        
        return qs.filter(filter_q).distinct()

class GameDetailPermission(permissions.BasePermission):
    
    """
    Public games can be seen by unauthenticated users
    Private games can only be seen by participating players or admin
    Games can be changed by game admin
    """
    def has_object_permission(self, request, view, obj):

        if request.method in permissions.SAFE_METHODS:

            authorized = not obj.private

            if request.user and request.user.is_authenticated:
                player = Player.objects.get(user=request.user)
                is_admin = (request.user == obj.admin)
                participating = (player in obj.players.all())

                authorized = authorized or is_admin or participating

            return authorized

        # admin user can use non safe methods
        return obj.admin == request.user

class GameDetail(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = 'game_id'

    queryset = Game.objects.all()
    serializer_class = GameExSerializer

    permission_classes = [GameDetailPermission]

    # override parent class put method so that HTTP PUT request returns 405 Method not allowed
    def put(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def perform_update(self, serializer):
        game = Game.objects.get(game_id=self.kwargs['game_id'])

        if 'action' in self.request.data and self.request.data['action'] == 'add_player' and 'username' in self.request.data:

            user_to_add = User.objects.filter(username=self.request.data['username'])

            if not user_to_add:
                raise exceptions.NotFound(detail="Player '%s' not found." % self.request.data['username'])

            player_to_add = Player.objects.get(user=user_to_add[0])

            if player_to_add in game.players.all():
                raise Conflict(detail="'%s' is already participating in '%s'." % (self.request.data['username'], game.name))

            game.players.add(player_to_add)
    
        elif 'action' in self.request.data and self.request.data['action'] == 'remove_player' and 'username' in self.request.data:

            user_to_remove = User.objects.filter(username=self.request.data['username'])

            if not user_to_remove:
                raise exceptions.NotFound(detail="Player '%s' not found." % self.request.data['username'])

            player_to_remove = Player.objects.get(user=user_to_remove[0])

            if not player_to_remove in game.players.all():
                raise Conflict(detail="'%s' is not participating in '%s'." % (self.request.data['username'], game.name))

            game.players.remove(player_to_remove)

        else:
            raise exceptions.ParseError()

class NotificationList(generics.ListAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    def get_queryset(self):
        """
        Only show notifications of authenticated user.
        """
        qs = super().get_queryset()
        
        if self.request.user and self.request.user.is_authenticated:
            user = self.request.user
        
            return qs.filter(user=user)

    permission_classes = [permissions.IsAuthenticated]

class NotificationDetailPermission(permissions.BasePermission):
    
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user

class NotificationDetail(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = 'id'

    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    permission_classes = [permissions.IsAuthenticated, NotificationDetailPermission]

    # override parent class put method so that HTTP PUT request returns 405 Method not allowed (only PATCH and DELETE requests allowed)
    def put(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def perform_update(self, serializer):
        notification = Notification.objects.get(id=self.kwargs['id'])

        if not self.request.user == notification.user:
            raise exceptions.PermissionDenied()

        if 'action' in self.request.data and self.request.data['action'] == 'mark_as_read':
            if not notification.read_datetime:
                serializer.save(read=True,
                                read_datetime=timezone.now())

        elif 'action' in self.request.data and self.request.data['action'] == 'mark_as_unread':
            serializer.save(read=False,
                            read_datetime=None)

        else:
            raise exceptions.ParseError()

class Conflict(exceptions.APIException):
    status_code = 409
    default_detail = 'Conflict'
    default_code = 'conflict'

class FriendshipList(generics.ListCreateAPIView):
    queryset = Friendship.objects.all()
    serializer_class = FriendshipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Only show friend requests of authenticated user.
        """
        qs = super().get_queryset()
        
        if self.request.user and self.request.user.is_authenticated:
            user = self.request.user
            player = Player.objects.get(user=user)

            friendship_type = self.request.query_params.get('type', None)

            if friendship_type is not None:
                if friendship_type == "incoming":
                    return qs.filter(Q(request_to=player) & Q(state__isnull=True))
                elif friendship_type == "outgoing":
                    return qs.filter(Q(request_from=player) & Q(state__isnull=True))
                elif friendship_type == "active":
                    return qs.filter(((Q(request_to=player) | Q(request_from=player)) & Q(state="ACTIVE")))
            
            return qs.filter(((Q(request_to=player) | Q(request_from=player)) & Q(state__isnull=True)) | ((Q(request_to=player) | Q(request_from=player)) & Q(state="ACTIVE")))

    def perform_create(self, serializer):
        request_json = self.request.data

        user = self.request.user

        if not 'username' in request_json:
            raise exceptions.ParseError(detail="\"username\" body parameter missing.")

        requester_player = Player.objects.get(user=user)
        requested_user = User.objects.filter(username=request_json['username'])

        if not requested_user:
            raise exceptions.NotFound(detail="Player %s not found." % request_json['username'])
        
        requested_player = Player.objects.get(user=requested_user[0])

        if requester_player == requested_player:
            raise exceptions.PermissionDenied(detail="A player cannot add himself as a friend.")

        outgoing_request = Friendship.objects.filter(request_from=requester_player, request_to=requested_player, state__isnull=True)
        incoming_request = Friendship.objects.filter(request_from=requested_player, request_to=requester_player, state__isnull=True)

        active_request = outgoing_request or incoming_request
    
        if active_request:
            raise Conflict(detail="An active friend request already exists between those users.")

        already_friends = requested_player in list(requester_player.friends.all())

        if already_friends:
            raise Conflict(detail="Players are already friends with eachother.")

        request_datetime = timezone.now()
    
        notification = Notification(notification_type=NotificationType.FRIEND_REQ.value,
                                    creation_datetime=request_datetime,
                                    sender=requester_player.user,
                                    user=requested_player.user)
                
        notification.save()

        serializer.save(request_from=requester_player,
                        request_to=requested_player,
                        request_datetime=request_datetime)
                        
class FriendshipDetailPermission(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):

        requester_user = User.objects.get(username=obj.request_from.user.username)
        requested_user = User.objects.get(username=obj.request_to.user.username)

        return (request.user == requested_user) | (request.user == requester_user)

class FriendshipDetail(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = 'id'

    queryset = Friendship.objects.all()
    serializer_class = FriendshipSerializer

    permission_classes = [permissions.IsAuthenticated, FriendshipDetailPermission]

    # override parent class put method so that HTTP PUT request returns 405 Method not allowed (only PATCH requests allowed)
    def put(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def perform_update(self, serializer):
        friend_request = Friendship.objects.get(id=self.kwargs['id'])

        if not ((self.request.user == friend_request.request_from.user or self.request.user == friend_request.request_to.user) and not friend_request.state):
            raise exceptions.PermissionDenied()
        
        if self.request.user == friend_request.request_from.user and 'action' in self.request.data and self.request.data['action'] == 'cancel':
            notification = Notification.objects.filter(notification_type=NotificationType.FRIEND_REQ.value,
                                                        creation_datetime=friend_request.request_datetime,
                                                        user=friend_request.request_to.user,
                                                        read=False)
            if notification:
                notification.delete()
            serializer.save(state="CANCELED",
                            action_taken_datetime=timezone.now())
        
        elif self.request.user == friend_request.request_to.user and 'action' in self.request.data and self.request.data['action'] == 'accept':
            request_datetime = timezone.now()

            # Add to player's friends list and send notification to new friend
            player = Player.objects.get(user=self.request.user)
            player.friends.add(friend_request.request_from)

            notification = Notification(notification_type=NotificationType.ADDED_AS_FRIEND.value,
                                        creation_datetime=request_datetime,
                                        sender=player.user,
                                        user=friend_request.request_from.user)
            notification.save()

            # Mark friend request notification as read if it still is unread
            friend_request_notification = Notification.objects.filter(notification_type=NotificationType.FRIEND_REQ.value,
                                                        creation_datetime=friend_request.request_datetime,
                                                        user=friend_request.request_to.user,
                                                        read=False)
            
            if friend_request_notification:
                friend_request_notification = Notification.objects.get(pk=friend_request_notification[0].pk)
                friend_request_notification.read = True
                friend_request_notification.read_datetime = request_datetime
                friend_request_notification.save()
            
            # Update friend_request state and save datetime of action_taken
            serializer.save(state="ACTIVE",
                            action_taken_datetime=request_datetime)

        elif self.request.user == friend_request.request_to.user and 'action' in self.request.data and self.request.data['action'] == 'decline':
            request_datetime = timezone.now()

            # Mark friend request notification as read if it still is unread
            friend_request_notification = Notification.objects.filter(notification_type=NotificationType.FRIEND_REQ.value,
                                                        creation_datetime=friend_request.request_datetime,
                                                        user=friend_request.request_to.user,
                                                        read=False)
            
            if friend_request_notification:
                friend_request_notification = Notification.objects.get(pk=friend_request_notification[0].pk)
                friend_request_notification.read = True
                friend_request_notification.read_datetime = request_datetime
                friend_request_notification.save()

            # Update friend_request state and save datetime of action_taken
            serializer.save(state="DECLINED",
                            action_taken_datetime=request_datetime)

        else:
            raise exceptions.ParseError()

    """
    TODO: let client DELETE friendships using /friendships/{username} instead of /friendships/{id}
    """
    def perform_destroy(self, instance):

        # Remove player from friends in the Player model
        user = self.request.user
        requester_player = Player.objects.get(user=user)

        friend_request = Friendship.objects.get(id=self.kwargs['id'])
        
        if not friend_request.state == "ACTIVE":
            raise exceptions.PermissionDenied()

        if friend_request.request_from == requester_player:
            player_to_remove = friend_request.request_to
        else:
            player_to_remove = friend_request.request_from

        requester_player.friends.remove(player_to_remove)

        # Remove "X accepted your friend request." notification from the requester if it hasn't been read yet
        notification = Notification.objects.filter(notification_type=NotificationType.ADDED_AS_FRIEND.value,
                                                user=player_to_remove.user,
                                                read=False)
        
        if notification:
            notification.delete()

        # Delete active Friendship instance
        instance.delete()

class GameParticipationRequestList(generics.ListCreateAPIView):
    queryset = GameParticipationRequest.objects.all()
    serializer_class = GameParticipationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Only show game participation requests of games that authenticated user is administering.
        """
        qs = super().get_queryset()
        
        if self.request.user and self.request.user.is_authenticated:
            user = self.request.user
            player = Player.objects.get(user=user)
        
            return qs.filter((Q(request_to_game__admin=user) | Q(request_from=player)) & Q(state__isnull=True))

    def perform_create(self, serializer):

        request_json = self.request.data

        user = self.request.user

        if not 'game_id' in request_json:
            raise exceptions.ParseError(detail="'game_id' body parameter missing.")

        player = Player.objects.get(user=user)
        game = get_object_or_404(Game, game_id=request_json['game_id'])

        if player.user == game.admin:
            raise exceptions.PermissionDenied(detail="A game admin cannot request participation to said game.")

        active_request = GameParticipationRequest.objects.filter(request_from=player, request_to_game=game, state__isnull=True)

        if active_request:
            raise Conflict(detail="An active request already exists from this user.")

        participating = player in game.players.all()
    
        if participating:
            raise Conflict(detail="Already participating.")

        request_datetime = timezone.now()
    
        notification = Notification(notification_type=NotificationType.PARTICIPATION_REQ.value,
                                    creation_datetime=request_datetime,
                                    sender=user,
                                    game=game,
                                    user=game.admin)
                
        notification.save()

        serializer.save(request_from=player,
                        request_to_game=game,
                        request_datetime=request_datetime)

class GamePaticipationRequestDetailPermission(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        return ((request.user == obj.request_from.user or request.user == obj.request_to_game.admin) and not obj.state)

class GameParticipationRequestDetail(generics.RetrieveUpdateAPIView):
    lookup_field = 'id'

    queryset = GameParticipationRequest.objects.all()
    serializer_class = GameParticipationRequestSerializer

    permission_classes = [permissions.IsAuthenticated, GamePaticipationRequestDetailPermission]

    # override parent class put method so that HTTP PUT request returns 405 Method not allowed (only PATCH requests allowed)
    def put(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def perform_update(self, serializer):
        participation_request = GameParticipationRequest.objects.get(id=self.kwargs['id'])

        if not ((self.request.user == participation_request.request_from.user or self.request.user == participation_request.request_to_game.admin) and not participation_request.state):
            raise exceptions.PermissionDenied()

        if self.request.user == participation_request.request_from.user and 'action' in self.request.data and self.request.data['action'] == 'cancel':

            # Remove notification from game admin if it still is unread
            notification = Notification.objects.filter(notification_type=NotificationType.PARTICIPATION_REQ.value,
                                                    creation_datetime=participation_request.request_datetime,
                                                    user=participation_request.request_to_game.admin,
                                                    read=False)
            if notification:
                notification.delete()

            serializer.save(state="CANCELED",
                            action_taken_datetime=timezone.now())
        
        elif self.request.user == participation_request.request_to_game.admin and 'action' in self.request.data and self.request.data['action'] == 'accept':

            request_datetime = timezone.now()

            # Add player to game players list and send notification to player
            participation_request.request_to_game.players.add(participation_request.request_from)

            notification = Notification(notification_type=NotificationType.ADDED_TO_GAME.value,
                                        creation_datetime=request_datetime,
                                        sender=participation_request.request_to_game.admin,
                                        game=participation_request.request_to_game,
                                        user=participation_request.request_from.user)
            notification.save()

            # Mark game participation request notification as read if it still is unread
            participation_request_notification = Notification.objects.filter(notification_type=NotificationType.PARTICIPATION_REQ.value,
                                                                            creation_datetime=participation_request.request_datetime,
                                                                            user=participation_request.request_to_game.admin,
                                                                            read=False)
            
            if participation_request_notification:
                participation_request_notification = Notification.objects.get(pk=participation_request_notification[0].pk)
                participation_request_notification.read = True
                participation_request_notification.read_datetime = request_datetime
                participation_request_notification.save()

            # Update participation_request state and save datetime of action_taken
            serializer.save(state="ACCEPTED",
                            action_taken_datetime=request_datetime)
            
        elif self.request.user == participation_request.request_to_game.admin and 'action' in self.request.data and self.request.data['action'] == 'decline':

            request_datetime = timezone.now()

            # Mark game participation request notification as read if it still is unread
            notification = Notification.objects.filter(notification_type=NotificationType.PARTICIPATION_REQ.value,
                                                    creation_datetime=participation_request.request_datetime,
                                                    user=participation_request.request_to_game.admin,
                                                    read=False)
                                                    
            if notification:
                notification = Notification.objects.get(pk=notification[0].pk)
                notification.read = True
                notification.read_datetime = request_datetime
                notification.save()

            # Update participation_request state and save datetime of action_taken
            serializer.save(state="DECLINED",
                            action_taken_datetime=request_datetime)

        else:
            raise exceptions.ParseError()
