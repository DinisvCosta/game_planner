from datetime import date

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
    number_of_games_played = models.IntegerField(default=0)

    def __str__(self):
        string = self.user.username + ", user_id:" + str(self.user.id)
        return string

class Game(models.Model):
    game_id = models.CharField(primary_key=True, max_length=12, editable=False)
    name = models.CharField(max_length=30)
    admin = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='game_admin')
    when = models.DateField()
    where = models.CharField(max_length=60)
    players = models.ManyToManyField(Player)
    price = models.IntegerField()
    duration = models.DurationField()
    # TODO encrypt password: https://stackoverflow.com/questions/25098466/how-to-store-django-hashed-password-without-the-user-object
    password = models.CharField(max_length=30, blank=True, default='')

    def __str__(self):
        return self.name

    # Checks if Game is in the future to help only displaying relevant games to player in the games page.
    def is_in_the_future(self):
        # TODO get minute/hour accuracy
        return self.when > date.today()