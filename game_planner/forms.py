import datetime
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import Player, Game, pkgen

class SignUpForm(forms.Form):
    username = forms.CharField(label='Username', max_length=30)
    password1 = forms.CharField(label='Password', min_length=6, max_length=30, widget=forms.PasswordInput())
    password2 = forms.CharField(label='Password Confirmation', min_length=6, max_length=30, widget=forms.PasswordInput())
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional')
    email = forms.EmailField(max_length=254, required=False, help_text='Optional')

    def clean(self):
        clean_data = self.cleaned_data

        # Display error if chosen username is already registered
        if User.objects.filter(username=self.cleaned_data['username']).exists():
            self.add_error('username', "Username already registered, please try another.")
        
        # Display error if email is already registered
        if User.objects.filter(email=self.cleaned_data['email']).exists():
            self.add_error('email', "Email already registered, please try another.")
        

        # Display error if password confirmation field doesn't match with password field
        if clean_data.get('password1') != clean_data.get('password2'):
            self.add_error('password2', "Passwords do not match.")
        
        return clean_data

    def save(self):
        user = User.objects.create_user(username=self.cleaned_data['username'],
                                        email=self.cleaned_data['email'],
                                        password=self.cleaned_data['password1'],
                                        first_name=self.cleaned_data['first_name'],
                                        last_name=self.cleaned_data['last_name'])
        player = Player(user=user)
        player.save()
        return True

class LoginForm(forms.Form):
    username = forms.CharField(label='Username or Email', max_length=50)
    password = forms.CharField(label='Password', min_length=6, max_length=30, widget=forms.PasswordInput())

    def clean(self):
        username = self.cleaned_data['username']
        password = self.cleaned_data['password']

        if not User.objects.filter(username=username).exists():
            self.add_error('username', "Invalid username or email.")
        # TODO
        # Deal with username field being the email,
        # get username for the user with that email
        if authenticate(username=username, password=password) == None:
            self.add_error('password', "Invalid password.")            

class PlayerModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.user.username

class CreateGameForm(forms.Form):
    name = forms.CharField(label="Game Name", min_length=1, max_length=30)
    when = forms.DateTimeField(label="Date", initial=datetime.datetime.now())
    where = forms.CharField(max_length=60)
    players = PlayerModelMultipleChoiceField(queryset=Player.objects.all())
    price = forms.IntegerField(widget=forms.NumberInput())
    duration = forms.DurationField(widget=forms.TimeInput())
    private = forms.BooleanField(required=False)

    pk = None

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(CreateGameForm, self).__init__(*args, **kwargs)

    def clean(self):
        # Confirm that new game name doesn't already exist for logged in user
        #  Get player
        player = Player.objects.get(user_id=self.user.id)
        #  Get player's games list
        user_games = Game.objects.filter(admin=player.id)
        #  Iterate over games to check that none have the same name
        for game in user_games:
            if game.name == self.cleaned_data['name']:
                self.add_error('name', "You already have a game with this name. Please choose a different one.")
                break

    def save(self):
        player = Player.objects.get(user_id=self.user.id)

        success = False

        while not success:
            self.pk = pkgen()
            success = not Game.objects.filter(game_id=self.pk).exists()

        game = Game(game_id=self.pk,
                    name=self.cleaned_data['name'],
                    admin=player,
                    when=self.cleaned_data['when'],
                    where=self.cleaned_data['where'],
                    #players=self.cleaned_data['players'],
                    price=self.cleaned_data['price'],
                    duration=self.cleaned_data['duration'],
                    private=self.cleaned_data['private'])
                    
        game.save()
        game.players.set(self.cleaned_data['players'])
        
        return True

class ManageProfileForm(forms.Form):
    old_password = forms.CharField(label='Old password', min_length=6, max_length=30, widget=forms.PasswordInput(), required=False, help_text='Change password')
    new_password1 = forms.CharField(label='New password', min_length=6, max_length=30, widget=forms.PasswordInput(), required=False)
    new_password2 = forms.CharField(label='New password Confirmation', min_length=6, max_length=30, widget=forms.PasswordInput(), required=False)
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional')
    email = forms.EmailField(max_length=254, required=False, help_text='Optional')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(ManageProfileForm, self).__init__(*args, **kwargs)

    def clean(self):
        user = self.user
        old_password = self.cleaned_data['old_password']
        new_password1 = self.cleaned_data['new_password1']
        new_password2 = self.cleaned_data['new_password2']
        first_name = self.cleaned_data['first_name']
        last_name = self.cleaned_data['last_name']
        email = self.cleaned_data['email']

        # Update password
        if old_password != '' or new_password1 != '' or new_password2 != '':
            # old_password is not filled
            if old_password == '':
                self.add_error('old_password', "Old password required to change password.")
            # old_password is incorrect error
            elif not user.check_password(old_password):
                self.add_error('old_password', "Invalid password. Please try again.")
            # new_password1 field is empty error
            elif new_password1 == '':
                self.add_error('new_password1', "Please enter the new password.")
            # new_password2 field is empty error
            elif new_password2 == '':
                self.add_error('new_password2', "Please enter the new password confirmation.")
            # new passwords don't match error
            elif new_password1 != new_password2:
                self.add_error('new_password2', "Passwords don't match. Please try again.")
            # new passwords are the same as old password
            elif old_password == new_password1 == new_password2:
                self.add_error('new_password2', "New password can't be the same as old password.")
            # all password changing fields are correct
            else:
                user.set_password(new_password1)
        
        # Update first_name field
        if first_name != '':
            user.first_name = first_name
        
        # Update last_name field
        if last_name != '':
            user.last_name = last_name
        
        # Check email is not used in any user already and update
        if email != '':
            if User.objects.filter(email=email).exists():
                self.add_error('email', "E-mail already registered, please try another.")
            else:
                user.email = email
                
        user.save()
        # TODO display message notifying that no changes were applied and redirect to profile.
        if old_password == '' and new_password1 == '' and new_password2 == '' and first_name == '' and last_name == '' and email == '':
            print("DEBUG: (ManageProfileForm)(clean): No changes applied.")

class ManageGameForm(forms.Form):
    name = forms.CharField(max_length=30, required=False)
    when = forms.DateTimeField(required=False, help_text="format: " + "2019-07-08 14:31:56")
    where = forms.CharField(max_length=60, required=False)
    players = PlayerModelMultipleChoiceField(queryset=Player.objects.all(), required=False)
    price = forms.IntegerField(widget=forms.NumberInput(), required=False)
    duration = forms.DurationField(widget=forms.TimeInput(), required=False)
    private = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        self.game = kwargs.pop('game', None)
        super(ManageGameForm, self).__init__(*args, **kwargs)

    def clean(self):
        game = self.game
        name = self.cleaned_data['name']
        when = self.cleaned_data['when']
        where = self.cleaned_data['where']
        players = self.cleaned_data['players']
        price = self.cleaned_data['price']
        duration = self.cleaned_data['duration']
        private = self.cleaned_data['private']

        if name:
            game.name = name
        
        if when:
            game.when = when
        
        if where:
            game.where = where

        if players:
            game.players.set(players)
        
        if price:
            game.price = price
        
        if duration:
            game.duration = duration

        #TODO find new way to change privacy setting    
        game.private = private
        
        game.save()
