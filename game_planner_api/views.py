from rest_framework import generics
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

from game_planner_api.serializers import PlayerSerializer
from .models import Player

class PlayerList(generics.ListAPIView):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer

class PlayerDetail(generics.RetrieveAPIView):
    lookup_field = 'username'

    queryset = Player.objects.all()
    serializer_class = PlayerSerializer

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

        user = User.objects.get(**filter_kwargs)

        if user:
            obj = get_object_or_404(Player, user=user)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj
