from rest_framework import generics
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

from game_planner_api.serializers import PlayerSerializer
from .models import Player

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