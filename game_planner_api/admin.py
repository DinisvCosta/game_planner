from django.contrib import admin

from .models import Player, Game, Notification, Friendship, GameParticipationRequest

admin.site.register(Player)
admin.site.register(Game)
admin.site.register(Notification)
admin.site.register(Friendship)
admin.site.register(GameParticipationRequest)