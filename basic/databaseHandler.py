from .models import *
import random
import string
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q


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

def getStudentRequest(user, id=None):
    if user is not None:
        student = Student.objects.filter(user=user)[0]
    else:
        student = Student.objects.filter(id=id)[0]
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

def getRequest(id):
    student = Student.objects.filter(id=id).first()
    return student

def createExternPruefer(name, email, password):
    user = User.objects.create_user(username=email, email=email, password=password)
    pruefer = ExternerPruefer.objects.create(name=name, email=email, user=user)
    with transaction.atomic():
        user.save()
        pruefer.save()

def createPruefunsamt(email, password):
    user = User.objects.create_user(username=email, email=email, password=password)
    pruefungsamt = Pruefungsamt.objects.create(user=user)
    with transaction.atomic():
        user.save()
        pruefungsamt.save()

def approveRequest(request, group, user=None):
    student = Student.objects.filter(id=request)[0]
    if group == "Prüfungsamt":
        student.prüfungsamtBestaetigt = True
        student.save()
    else:
        intern = False
        if InternerPruefer.objects.filter(user=user).exists():
            intern = True
        if intern:
            pruefer = InternerPruefer.objects.filter(user=user)[0]
        else:
            pruefer = ExternerPruefer.objects.filter(user=user)[0]
        if (student.betreuer1 == pruefer.id and student.istBetreuer1Intern == intern):
            student.betreuer1Bestaetigt = True
            student.save()
        else:
            student.betreuer2Bestaetigt = True
            student.save()

def rejectRequest(request, group, user=None):
    student = Student.objects.filter(id=request)[0]
    if group == "Prüfungsamt":
        student.prüfungsamtBestaetigt = True
        student.save()
    else:
        intern = False
        if InternerPruefer.objects.filter(user=user).exists():
            intern = True
        if intern:
            pruefer = InternerPruefer.objects.filter(user=user)[0]
        else:
            pruefer = ExternerPruefer.objects.filter(user=user)[0]
        if (student.betreuer1 == pruefer.id and student.istBetreuer1Intern == intern):
            student.betreuer1Bestaetigt = False
            student.save()
        else:
            student.betreuer2Bestaetigt = False
            student.save()

def getNotAcceptedRequests(group, user=None):
    if group == "Prüfungsamt":
        requests = Student.objects.filter(prüfungsamtBestaetigt=None).order_by('abgabetermin')
    elif group == "Prüfer":
        intern = False
        if InternerPruefer.objects.filter(user=user).exists():
            intern = True
        if intern:
            pruefer = InternerPruefer.objects.filter(user=user)[0]
        else:
            pruefer = ExternerPruefer.objects.filter(user=user)[0]
        requests = Student.objects.filter(Q(istBetreuer1Intern=intern,  betreuer1=pruefer.id) |
                                          Q(istBetreuer2Intern=intern,  betreuer2=pruefer.id))
        for elem in requests:
            if elem.istBetreuer1Intern == intern and elem.betreuer1 == pruefer.id:
                if elem.betreuer1Bestaetigt:
                    requests = requests.exclude(id=elem.id)
            elif elem.istBetreuer2Intern == intern and elem.betreuer2 == pruefer.id:
                if elem.betreuer2Bestaetigt:
                    requests = requests.exclude(id=elem.id)
    return requests

def getRequestsOfPrüfer(user, status):
    intern = False
    if InternerPruefer.objects.filter(user=user).exists():
        intern = True
    if intern:
        pruefer = InternerPruefer.objects.filter(user=user)[0]
    else:
        pruefer = ExternerPruefer.objects.filter(user=user)[0]

    if status == "Schreibphase":
        requests = Student.objects.filter((Q(istBetreuer1Intern=intern,  betreuer1=pruefer.id) |
                                          Q(istBetreuer2Intern=intern,  betreuer2=pruefer.id)), status=status)
    return requests

def getNotRatedRequests(user):
    intern = False
    if InternerPruefer.objects.filter(user=user).exists():
        intern = True
    if intern:
        pruefer = InternerPruefer.objects.filter(user=user)[0]
    else:
        pruefer = ExternerPruefer.objects.filter(user=user)[0]
    requests = Student.objects.filter(Q(istBetreuer1Intern=intern, betreuer1=pruefer.id) |
                                      Q(istBetreuer2Intern=intern, betreuer2=pruefer.id) |
                                      Q(istDrittgutachterIntern=intern, drittgutachter=pruefer.id))
    for elem in requests:
        if elem.istBetreuer1Intern == intern and elem.betreuer1 == pruefer.id:
            if elem.note1 is not None:
                requests = requests.exclude(id=elem.id)
        elif elem.istBetreuer2Intern == intern and elem.betreuer2 == pruefer.id:
            if elem.note2 is not None:
                requests = requests.exclude(id=elem.id)
        elif elem.istDrittgutachterIntern == intern and elem.drittgutachter == pruefer.id:
            if elem.note3 is not None:
                requests = requests.exclude(id=elem.id)
    return requests

def getRatedRequests(user):
    intern = False
    if InternerPruefer.objects.filter(user=user).exists():
        intern = True
    if intern:
        pruefer = InternerPruefer.objects.filter(user=user)[0]
    else:
        pruefer = ExternerPruefer.objects.filter(user=user)[0]
    requests = Student.objects.filter(Q(istBetreuer1Intern=intern, betreuer1=pruefer.id) |
                                      Q(istBetreuer2Intern=intern, betreuer2=pruefer.id) |
                                      Q(istDrittgutachterIntern=intern, drittgutachter=pruefer.id))
    for elem in requests:
        if elem.istBetreuer1Intern == intern and elem.betreuer1 == pruefer.id:
            if elem.note1 is None:
                requests = requests.exclude(id=elem.id)
        elif elem.istBetreuer2Intern == intern and elem.betreuer2 == pruefer.id:
            if elem.note2 is None:
                requests = requests.exclude(id=elem.id)
        elif elem.istDrittgutachterIntern == intern and elem.drittgutachter == pruefer.id:
            if elem.note3 is None:
                requests = requests.exclude(id=elem.id)
    return requests

def getNotAnsweredInvitations(user):
    intern = False
    if InternerPruefer.objects.filter(user=user).exists():
        intern = True
    if intern:
        pruefer = InternerPruefer.objects.filter(user=user)[0]
    else:
        pruefer = ExternerPruefer.objects.filter(user=user)[0]
    invitations = Einladung.objects.filter(pruefer=pruefer.id, istPrueferIntern=intern, angenommen__isnull=True)
    return invitations

def getAnsweredInvitations(user):
    intern = False
    if InternerPruefer.objects.filter(user=user).exists():
        intern = True
    if intern:
        pruefer = InternerPruefer.objects.filter(user=user)[0]
    else:
        pruefer = ExternerPruefer.objects.filter(user=user)[0]
    invitations = Einladung.objects.filter(pruefer=pruefer.id, istPrueferIntern=intern, angenommen__isnull=False)
    return invitations

def getStudentName(student):
    return student.name

def getFinalDates(user):
    intern = False
    if InternerPruefer.objects.filter(user=user).exists():
        intern = True
    if intern:
        pruefer = InternerPruefer.objects.filter(user=user)[0]
    else:
        pruefer = ExternerPruefer.objects.filter(user=user)[0]
    studentId = Einladung.objects.filter(pruefer=pruefer.id, istPrueferIntern=intern, angenommen=True)
    studentIdList = studentId.values('student').distinct()
    students = Student.objects.filter(id__in=studentIdList).distinct()
    return students

def checkStatus(student):
    if student.status == "Anfrage wird bestätigt":
        if student.prüfungsamtBestaetigt and student.betreuer1Bestaetigt and student.betreuer2Bestaetigt:
            student.status = "Schreibphase"
            student.save()
    if student.status == "Gutachteneingabe":
        if student.note1 is not None and student.note2 is not None:
            if student.note1 == 1 and student.note2 == 1:
                if student.note3 is not None:
                    student.status = "Terminfindung"
                    student.save()
            else:
                student.status = "Terminfindung"
                student.save()
    if student.status == "Terminfindung":
        if student.terminEntstanden is not None and student.pruefungsamtBestaetigtTermin is not None:
            student.status = "Termin entstanden"
            student.save()