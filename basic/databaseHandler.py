from .models import *
import random
import string
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db import transaction


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
def getUser(email, zdvId, state, stateLength,  name):
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
        with transaction.atomic():
            user.save()
            student.save()
        return user

def getUserGroup(user):
    results = Pruefungsamt.objects.filter(user=user)
    if results.exists():
        return "Prüfungsamt"
    results = InternerPruefer.objects.filter(user=user)
    if results.exists():
        return "Prüfer"
    results = ExternerPruefer.objects.filter(user=user)
    if results.exists():
        return "Prüfer"
    results = Student.objects.filter(user=user)
    if results.exists():
        return "Student"
    else:
        return "No Group"

def haveRequest(user):
    student = Student.objects.filter(user=user)
    if student.exists() and student[0].abgabetermin is not None:
        return True
    return False

def makeRequest(user, abgabetermin, fach, betreuer1, betreuer2, themengebiet, art, titel, betreuer1Intern, betreuer2Intern):
    student = Student.objects.filter(user=user)[0]
    student.abgabetermin = abgabetermin
    student.fach = fach
    student.betreuer1 = betreuer1
    student.betreuer2 = betreuer2
    student.themengebiet = themengebiet
    student.artDerArbeit = art
    student.titel = titel
    student.istBetreuer1Intern = betreuer1Intern
    student.istBetreuer2Intern = betreuer2Intern
    student.status = "Anfrage wird bestätigt"
    student.save()

def getRequest(user):
    student = Student.objects.filter(user=user)[0]
    result = {}
    result['titel'] = student.titel
    if student.istBetreuer1Intern:
        betreuer1 = InternerPruefer.objects.filter(id=student.betreuer1)[0]
    else:
        betreuer1 = ExternerPruefer.objects.filter(id=student.betreuer1)[0]
    result['betreuer1'] = betreuer1.name
    if student.istBetreuer2Intern:
        betreuer2 = InternerPruefer.objects.filter(id=student.betreuer2)[0]
    else:
        betreuer2 = ExternerPruefer.objects.filter(id=student.betreuer2)[0]
    result['betreuer2'] = betreuer2.name
    result['abgabetermin'] = student.abgabetermin
    result['art'] = student.artDerArbeit
    result['status'] = student.status
    result['note1'] = student.note1
    result['note2'] = student.note2
    result['themengebiet'] = student.themengebiet
    return result

def createExternPruefer(name, email, password):
    user = User.objects.create_user(username=email, email=email, password=password)
    pruefer = ExternerPruefer.objects.create(name=name, email=email, user=user)
    with transaction.atomic():
        user.save()
        pruefer.save()

def approveRequest(request, group, pruefer=None):
    student = Student.objects.filter(id=request)[0]
    if group == "Prüfungsamt":
        student.prüfungsamtBestaetigt = True
        student.save()
    else:
        intern = False
        if InternerPruefer.objects.filter(user=pruefer).exists():
            intern = True
        if (student.betreuer1 == pruefer.id and student.istBetreuer1Intern == intern):
            student.betreuer1Bestaetigt = True
            student.save()
        else:
            student.betreuer2Bestaetigt = True
            student.save()
