from django.contrib.auth.models import User

from rest_framework import serializers

from .models import Player, Game

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

class UserExSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'last_login', 'date_joined']

class FriendSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Player
        fields = ['user']

class PlayerSerializer(serializers.ModelSerializer):
    user = UserExSerializer(read_only=True)
    friends = FriendSerializer(many=True, read_only=True)

    class Meta:
        model = Player
        fields = ['user', 'friends']

class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ['game_id', 'name']

class GameExSerializer(serializers.ModelSerializer):
    num_players = serializers.SerializerMethodField() 

    class Meta:
        model = Game
        fields = ['name', 'admin', 'when', 'where', 'num_players', 'price', 'duration', 'private']

    def get_num_players(self, obj):
        return obj.players.count()