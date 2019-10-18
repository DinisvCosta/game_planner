from django.contrib.auth.models import User

from rest_framework import serializers

from .models import Player, Game, Notification

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
    admin = serializers.ReadOnlyField(source='admin.username')

    class Meta:
        model = Game
        fields = ['name', 'admin', 'when', 'where', 'num_players', 'price', 'duration', 'private']

    def get_num_players(self, obj):
        return obj.players.count()

class NotificationSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='pk')
    sender = serializers.ReadOnlyField(source='sender.username')
    user_href = serializers.ReadOnlyField(source='sender.get_absolute_url')
    game_name = serializers.ReadOnlyField(source='game.name')
    game_href = serializers.ReadOnlyField(source='game.get_absolute_url')
    #game_href = serializers.HyperlinkedRelatedField(source='game', read_only=True, view_name='game-detail', lookup_field='game_id')

    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'creation_datetime', 'read_datetime', 'read', 'sender', 'user_href', 'game_name', 'game_href']
        read_only_fields = ['id', 'notification_type', 'creation_datetime', 'sender', 'user_href', 'game_name', 'game_href']

