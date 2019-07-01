from datetime import date, datetime

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

class Game(models.Model):
    game_id = models.CharField(primary_key=True, max_length=12, editable=False)
    name = models.CharField(max_length=30)
    admin = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='game_admin')
    when = models.DateTimeField()
    where = models.CharField(max_length=60)
    players = models.ManyToManyField(Player)
    price = models.IntegerField()
    duration = models.DurationField()
    private = models.BooleanField(default=False)

    def __str__(self):
        return str(self.when) + " - " + self.name

    def is_in_the_future(self):
        return self.when > datetime.now()

class Notification(models.Model):
    notification_type = models.CharField(max_length=20)
    text = models.CharField(max_length=100)
    creation_datetime = models.DateTimeField()
    read_datetime = models.DateTimeField(null=True, blank=True)
    read = models.BooleanField(default=False)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)

    def __str__(self):
        return self.text

class FriendRequest(models.Model):
    request_from = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='friend_request_from')
    request_to = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='friend_request_to')
    request_datetime = models.DateTimeField()
    action_taken_datetime = models.DateTimeField(null=True, blank=True)
    accepted = models.BooleanField(null=True, blank=True)

    class Meta:
        ordering = ['-request_datetime']

    def __str__(self):
        return "Friend request from " + self.request_from.user.username + " to " + self.request_to.user.username