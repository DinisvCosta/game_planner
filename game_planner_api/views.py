from rest_framework import generics
from rest_framework import permissions
from rest_framework import exceptions
from rest_framework import status
from rest_framework.response import Response

from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone

from game_planner_api.serializers import PlayerSerializer, GameSerializer, GameExSerializer, NotificationSerializer, FriendRequestSerializer
from .models import Player, Game, Notification, FriendRequest, NotificationType

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

            if not user_to_remove:
                raise exceptions.NotFound(detail="Player %s not found." % self.kwargs['username'])

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

class GameDetail(generics.RetrieveAPIView):
    lookup_field = 'game_id'

    queryset = Game.objects.all()
    serializer_class = GameExSerializer

    permission_classes = [GameDetailPermission]

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

class NotificationUpdate(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = 'id'

    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    permission_classes = [permissions.IsAuthenticated, NotificationDetailPermission]

    # override parent class put method so that HTTP GET request returns 405 Method not allowed (only PATCH and DELETE requests allowed)
    def get(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

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

class FriendRequestList(generics.ListCreateAPIView):
    queryset = FriendRequest.objects.all()
    serializer_class = FriendRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    # TODO deal with GET /friend_requests?filter=incoming or outgoing
    # use request.query_params to filter friend requests as incoming or outgoing 
    # more info at: https://www.django-rest-framework.org/api-guide/requests/#query_params

    def get_queryset(self):
        """
        Only show friend requests of authenticated user.
        """
        qs = super().get_queryset()
        
        if self.request.user and self.request.user.is_authenticated:
            user = self.request.user
            player = Player.objects.get(user=user)
        
            return qs.filter((Q(request_to=player) | Q(request_from=player)) & Q(state__isnull=True))

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

        outgoing_request = FriendRequest.objects.filter(request_from=requester_player, request_to=requested_player, state__isnull=True)
        incoming_request = FriendRequest.objects.filter(request_from=requested_player, request_to=requester_player, state__isnull=True)

        active_request = outgoing_request or incoming_request
    
        if active_request:
            raise Conflict(detail="An active friend request alredy exists between those users.")

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
                        
class FriendRequestDetailPermission(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):

        requester_user = User.objects.get(username=obj.request_from.user.username)
        requested_user = User.objects.get(username=obj.request_to.user.username)

        if request.method in permissions.SAFE_METHODS:
            return ((request.user == requested_user) | (request.user == requester_user)) and obj.state == None
        
        # requested and requester can use non safe methods 
        return (request.user == requested_user) | (request.user == requester_user)

class FriendRequestDetail(generics.RetrieveUpdateAPIView):
    lookup_field = 'id'

    queryset = FriendRequest.objects.all()
    serializer_class = FriendRequestSerializer

    permission_classes = [permissions.IsAuthenticated, FriendRequestDetailPermission]

    # override parent class put method so that HTTP PUT request returns 405 Method not allowed (only PATCH requests allowed)
    def put(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def perform_update(self, serializer):
        friend_request = FriendRequest.objects.get(id=self.kwargs['id'])

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
            serializer.save(state="ACCEPTED",
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
