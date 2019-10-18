from rest_framework import generics
from rest_framework import permissions
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q

from game_planner_api.serializers import PlayerSerializer, GameSerializer, GameExSerializer
from .models import Player, Game

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
                   generics.RetrieveAPIView):
    lookup_field = 'username'
    indirect_lookup_field = 'user'
    indirect_model = User

    queryset = Player.objects.all()
    serializer_class = PlayerSerializer

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