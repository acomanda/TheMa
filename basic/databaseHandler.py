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
        results = InternExaminer.objects.filter(email=email)
        if results.exists():
            user = User.objects.filter(email=email)
            return user[0]
        temp = User.objects.filter(email=email)
        if temp.exists():
            user = temp[0]
        else:
            user = User.objects.create_user(username=email, email=email, password=randomString)
        student = InternExaminer.objects.create(zdvId=zdvId, name=name, email=email, user=user)
        with transaction.atomic():
            user.save()
            student.save()
        return user

def getUserGroup(user):
    results = Office.objects.filter(user=user)
    if results.exists():
        return "Prüfungsamt"
    results = InternExaminer.objects.filter(user=user)
    if results.exists():
        return "Prüfer"
    results = ExternalExaminer.objects.filter(user=user)
    if results.exists():
        return "Prüfer"
    results = Student.objects.filter(user=user)
    if results.exists():
        return "Student"
    else:
        return "No Group"

def haveRequest(user):
    student = Student.objects.filter(user=user)
    if student.exists() and student[0].deadline is not None:
        return True
    return False

def makeRequest(user, abgabetermin, fach, betreuer1, betreuer2, themengebiet, art, titel, betreuer1Intern, betreuer2Intern):
    student = Student.objects.filter(user=user)[0]
    student.deadline = abgabetermin
    student.subject = fach
    student.supervisor1 = betreuer1
    student.supervisor2 = betreuer2
    student.topic = themengebiet
    student.type = art
    student.title = titel
    student.isSupervisor1Intern = betreuer1Intern
    student.isSupervisor2Intern = betreuer2Intern
    student.status = "Anfrage wird bestätigt"
    student.save()

def getStudentRequest(user, id=None):
    if user is not None:
        student = Student.objects.filter(user=user)[0]
    else:
        student = Student.objects.filter(id=id)[0]
    result = {}
    result['titel'] = student.title
    if student.isSupervisor1Intern:
        betreuer1 = InternExaminer.objects.filter(id=student.supervisor1)[0]
    else:
        betreuer1 = ExternalExaminer.objects.filter(id=student.supervisor1)[0]
    result['betreuer1'] = betreuer1.name
    if student.isSupervisor2Intern:
        betreuer2 = InternExaminer.objects.filter(id=student.supervisor2)[0]
    else:
        betreuer2 = ExternalExaminer.objects.filter(id=student.supervisor2)[0]
    result['betreuer2'] = betreuer2.name
    result['abgabetermin'] = student.deadline
    result['art'] = student.type
    result['status'] = student.status
    result['note1'] = student.note1
    result['note2'] = student.note2
    result['themengebiet'] = student.topic
    return result

def getRequest(id):
    student = Student.objects.filter(id=id).first()
    return student

def createExternPruefer(name, email, password):
    user = User.objects.create_user(username=email, email=email, password=password)
    pruefer = ExternalExaminer.objects.create(name=name, email=email, user=user)
    with transaction.atomic():
        user.save()
        pruefer.save()

def createPruefunsamt(email, password):
    user = User.objects.create_user(username=email, email=email, password=password)
    pruefungsamt = Office.objects.create(user=user)
    with transaction.atomic():
        user.save()
        pruefungsamt.save()

def approveRequest(request, group, user=None):
    student = Student.objects.filter(id=request)[0]
    if group == "Prüfungsamt":
        student.officeConfirmed = True
        student.save()
    else:
        intern = False
        if InternExaminer.objects.filter(user=user).exists():
            intern = True
        if intern:
            pruefer = InternExaminer.objects.filter(user=user)[0]
        else:
            pruefer = ExternalExaminer.objects.filter(user=user)[0]
        if (student.supervisor1 == pruefer.id and student.isSupervisor1Intern == intern):
            student.supervisor1Confirmed = True
            student.save()
        else:
            student.supervisor2Confirmed = True
            student.save()

def rejectRequest(request, group, user=None):
    student = Student.objects.filter(id=request)[0]
    if group == "Prüfungsamt":
        student.officeConfirmed = True
        student.save()
    else:
        intern = False
        if InternExaminer.objects.filter(user=user).exists():
            intern = True
        if intern:
            pruefer = InternExaminer.objects.filter(user=user)[0]
        else:
            pruefer = ExternalExaminer.objects.filter(user=user)[0]
        if (student.supervisor1 == pruefer.id and student.isSupervisor1Intern == intern):
            student.supervisor1Confirmed = False
            student.save()
        else:
            student.supervisor2Confirmed = False
            student.save()

def getNotAcceptedRequests(group, user=None):
    if group == "Prüfungsamt":
        requests = Student.objects.filter(prüfungsamtBestaetigt=None).order_by('deadline')
    elif group == "Prüfer":
        intern = False
        if InternExaminer.objects.filter(user=user).exists():
            intern = True
        if intern:
            pruefer = InternExaminer.objects.filter(user=user)[0]
        else:
            pruefer = ExternalExaminer.objects.filter(user=user)[0]
        requests = Student.objects.filter(Q(isSupervisor1Intern=intern,  supervisor1=pruefer.id) |
                                          Q(isSupervisor2Intern=intern,  supervisor2=pruefer.id))
        for elem in requests:
            if elem.isSupervisor1Intern == intern and elem.supervisor1 == pruefer.id:
                if elem.supervisor1Confirmed:
                    requests = requests.exclude(id=elem.id)
            elif elem.isSupervisor2Intern == intern and elem.supervisor2 == pruefer.id:
                if elem.supervisor2Confirmed:
                    requests = requests.exclude(id=elem.id)
    return requests

def getRequestsOfPrüfer(user, status):
    intern = False
    if InternExaminer.objects.filter(user=user).exists():
        intern = True
    if intern:
        pruefer = InternExaminer.objects.filter(user=user)[0]
    else:
        pruefer = ExternalExaminer.objects.filter(user=user)[0]

    if status == "Schreibphase":
        requests = Student.objects.filter((Q(isSupervisor1Intern=intern,  supervisor1=pruefer.id) |
                                          Q(isSupervisor2Intern=intern,  supervisor2=pruefer.id)), status=status)
    return requests

def getNotRatedRequests(user):
    intern = False
    if InternExaminer.objects.filter(user=user).exists():
        intern = True
    if intern:
        pruefer = InternExaminer.objects.filter(user=user)[0]
    else:
        pruefer = ExternalExaminer.objects.filter(user=user)[0]
    requests = Student.objects.filter(Q(isSupervisor1Intern=intern, supervisor1=pruefer.id) |
                                      Q(isSupervisor2Intern=intern, supervisor2=pruefer.id) |
                                      Q(isSupervisor3Intern=intern, supervisor3=pruefer.id))
    for elem in requests:
        if elem.isSupervisor1Intern == intern and elem.supervisor1 == pruefer.id:
            if elem.note1 is not None:
                requests = requests.exclude(id=elem.id)
        elif elem.isSupervisor2Intern == intern and elem.betreuer2 == pruefer.id:
            if elem.note2 is not None:
                requests = requests.exclude(id=elem.id)
        elif elem.istDrittgutachterIntern == intern and elem.drittgutachter == pruefer.id:
            if elem.note3 is not None:
                requests = requests.exclude(id=elem.id)
    return requests

def getRatedRequests(user):
    intern = False
    if InternExaminer.objects.filter(user=user).exists():
        intern = True
    if intern:
        pruefer = InternExaminer.objects.filter(user=user)[0]
    else:
        pruefer = ExternalExaminer.objects.filter(user=user)[0]
    requests = Student.objects.filter(Q(isSupervisor1Intern=intern, supervisor1=pruefer.id) |
                                      Q(isSupervisor2Intern=intern, supervisor2=pruefer.id) |
                                      Q(isSupervisor3Intern=intern, supervisor2=pruefer.id))
    for elem in requests:
        if elem.isSupervisor1Intern == intern and elem.supervisor1 == pruefer.id:
            if elem.note1 is None:
                requests = requests.exclude(id=elem.id)
        elif elem.isSupervisor2Intern == intern and elem.supervisor2 == pruefer.id:
            if elem.note2 is None:
                requests = requests.exclude(id=elem.id)
        elif elem.isSupervisor3Intern == intern and elem.supervisor3 == pruefer.id:
            if elem.note3 is None:
                requests = requests.exclude(id=elem.id)
    return requests

def getNotAnsweredInvitations(user):
    intern = False
    if InternExaminer.objects.filter(user=user).exists():
        intern = True
    if intern:
        pruefer = InternExaminer.objects.filter(user=user)[0]
    else:
        pruefer = ExternalExaminer.objects.filter(user=user)[0]
    invitations = Invitation.objects.filter(examiner=pruefer.id, isExaminerIntern=intern, accepted__isnull=True)
    return invitations

def getAnsweredInvitations(user):
    intern = False
    if InternExaminer.objects.filter(user=user).exists():
        intern = True
    if intern:
        pruefer = InternExaminer.objects.filter(user=user)[0]
    else:
        pruefer = ExternalExaminer.objects.filter(user=user)[0]
    invitations = Invitation.objects.filter(examiner=pruefer.id, isExaminerIntern=intern, accepted__isnull=False)
    return invitations

def getStudentName(student):
    return student.name

def getFinalDates(user):
    intern = False
    if InternExaminer.objects.filter(user=user).exists():
        intern = True
    if intern:
        pruefer = InternExaminer.objects.filter(user=user)[0]
    else:
        pruefer = ExternalExaminer.objects.filter(user=user)[0]
    studentId = Invitation.objects.filter(examiner=pruefer.id, isExaminerIntern=intern, accepted=True)
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