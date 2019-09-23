from datetime import date, datetime
from enum import Enum

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

def pkgen(stringLength=12):
    import random
    import string

    lettersAndDigits = string.ascii_lowercase + string.digits
    return ''.join(random.choice(lettersAndDigits) for i in range(stringLength))

class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    friends = models.ManyToManyField("self")
    number_of_games_played = models.IntegerField(default=0)

    def __str__(self):
        string = self.user.username
        return string

    def get_absolute_url(self):
        return "/profile/%i" % self.user.id

class Game(models.Model):
    game_id = models.CharField(primary_key=True, max_length=12, editable=False)
    name = models.CharField(max_length=30)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='game_admin')
    when = models.DateTimeField()
    where = models.CharField(max_length=60)
    players = models.ManyToManyField(Player)
    price = models.IntegerField()
    duration = models.DurationField()
    private = models.BooleanField(default=False)

    def __str__(self):
        return str(self.when) + " - " + self.name

    def get_absolute_url(self):
        return "/games/%s/" % self.game_id
    
    def get_manage_url(self):
        return "/manage_game/%s/" % self.game_id

    def is_in_the_future(self):
        return self.when.replace(tzinfo=None) > datetime.now()

class NotificationType(Enum):
    FRIEND_REQ = 0
    PARTICIPATION_REQ = 1
    ADDED_AS_FRIEND = 2
    ADDED_TO_GAME = 3

class Notification(models.Model):
    notification_type = models.IntegerField()
    creation_datetime = models.DateTimeField()
    read_datetime = models.DateTimeField(null=True, blank=True)
    read = models.BooleanField(default=False)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='sender')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user')

    def get_absolute_url(self):
        if self.target_url and self.url_arg:
            return "/{0}/{1}/?notif_id={2}".format(self.target_url, self.url_arg, self.id)
        elif self.target_url:
            return "/{0}/?notif_id={1}".format(self.target_url, self.id)

class FriendRequest(models.Model):
    request_from = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='friend_request_from')
    request_to = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='friend_request_to')
    request_datetime = models.DateTimeField()
    action_taken_datetime = models.DateTimeField(null=True, blank=True)
    state = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        ordering = ['-request_datetime']

    def __str__(self):
        return "Friend request from " + self.request_from.user.username + " to " + self.request_to.user.username

class GameParticipationRequest(models.Model):
    request_from = models.ForeignKey(Player, on_delete=models.CASCADE)
    request_to_game = models.ForeignKey(Game, on_delete=models.CASCADE)
    request_datetime = models.DateTimeField()
    action_taken_datetime = models.DateTimeField(null=True, blank=True)
    state = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        ordering = ['-request_datetime']

    def __str__(self):
        return "Game participation request from " + self.request_from.user.username + " to " + self.request_to_game.name