from django.contrib import admin

from .models import Player, Game, Notification, FriendRequest, GameParticipationRequest

admin.site.register(Player)
admin.site.register(Game)
admin.site.register(Notification)
admin.site.register(FriendRequest)
admin.site.register(GameParticipationRequest)