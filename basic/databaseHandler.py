from .models import *
import random
import string
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


def randomString(length=20):
    symbols = string.ascii_letters + string.digits
    result = ""
    for i in range(length):
        result += random.choice(symbols)




class PasswordlessAuthBackend(ModelBackend):
    """Log in to Django without providing a password.

    """
    def authenticate(self, username=None):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

#todo add name when i get the right claim from the zdv
def getUser(email, zdvId, state, stateLength,  name="testname"):
    """Checks if user is already registered and if it is, it returns the user,
    otherwise it creates the user and return it."""
    group = state[stateLength:]
    if group == "student":
        results = Student.objects.filter(email=email)
        # todo in future use a custom user model instead of adding a random password
        if not results.exists():
            temp = User.objects.filter(email=email)
            if temp.exists():
                user = temp[0]
            else:
                user = User.objects.create_user(username=email, email=email, password=randomString)
            student = Student.objects.create(zdvId=zdvId, name=name, email=email, user=user)
            user.save()
            student.save()
            return user
        user = User.objects.filter(email=email)
        return user[0]

    if group == "pruefer":
        results = InternerPruefer.objects.filter(email=email)
        if results.exists():
            user = User.objects.filter(email=email)
            return user[0]
        temp = User.objects.filter(email=email)
        if temp.exists():
            user = temp[0]
        else:
            user = User.objects.create_user(username=email, email=email, password=randomString)
        student = InternerPruefer.objects.create(zdvId=zdvId, name=name, email=email, user=user)
        user.save()
        student.save()
        return user[0]