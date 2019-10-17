from django.contrib.auth.models import User

from rest_framework import serializers

from .models import Player, Game

class UserSerializer(serializers.HyperlinkedModelSerializer):
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