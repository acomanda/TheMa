from .models import *
import random
import string
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q


def randomString(length=20):
    """Function generates a random string of numbers and letters that is 'length' long."""
    symbols = string.ascii_letters + string.digits
    result = ""
    for i in range(length):
        result += random.choice(symbols)


class PasswordlessAuthBackend(ModelBackend):
    """Log in to Django without providing a password."""
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


def getUser(email, zdvId, state, stateLength, name):
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
    """Receives a django user object and return the User Group of the user."""
    results = Office.objects.filter(user=user)
    if results.exists():
        return "Office"
    results = InternExaminer.objects.filter(user=user)
    if results.exists():
        return "Examiner"
    results = ExternalExaminer.objects.filter(user=user)
    if results.exists():
        return "Examiner"
    results = Student.objects.filter(user=user)
    if results.exists():
        return "Student"
    else:
        return "No Group"


def haveRequest(user):
    """Receives a django user object and returns True,
    if the user is a student and the user has already make a request."""
    student = Student.objects.filter(user=user)
    if student.exists() and student[0].deadline is not None:
        return True
    return False


def makeRequest(user, deadline, subject, supervisor1, supervisor2, topic, type, title, isSupervisor1Intern,
    isSupervisor2Intern):
    """Function initiates a students request."""
    student = Student.objects.filter(user=user)[0]
    student.deadline = deadline
    student.subject = subject
    student.supervisor1 = supervisor1
    student.supervisor2 = supervisor2
    student.topic = topic
    student.type = type
    student.title = title
    student.isSupervisor1Intern = isSupervisor1Intern
    student.isSupervisor2Intern = isSupervisor2Intern
    student.status = "Anfrage wird bestätigt"
    student.save()


def getStudentRequest(user, id=None):
    """Receives a django user object or an student id and returns a
    dictionary with the informations about the request."""
    if user is not None:
        student = Student.objects.filter(user=user)[0]
    else:
        student = Student.objects.filter(id=id)[0]
    result = {}
    result['title'] = student.title
    if student.isSupervisor1Intern:
        betreuer1 = InternExaminer.objects.filter(id=student.supervisor1)[0]
    else:
        betreuer1 = ExternalExaminer.objects.filter(id=student.supervisor1)[0]
    result['supervisor1'] = betreuer1.name
    if student.isSupervisor2Intern:
        betreuer2 = InternExaminer.objects.filter(id=student.supervisor2)[0]
    else:
        betreuer2 = ExternalExaminer.objects.filter(id=student.supervisor2)[0]
    result['supervisor2'] = betreuer2.name
    result['deadline'] = student.deadline
    result['type'] = student.type
    result['status'] = student.status
    result['note1'] = student.note1
    result['note2'] = student.note2
    result['topic'] = student.topic
    result['subject'] = student.subject
    return result


def createExternalExaminer(name, email, password):
    """Function creates a new External Examiner"""
    user = User.objects.create_user(username=email, email=email, password=password)
    examiner = ExternalExaminer.objects.create(name=name, email=email, user=user)
    with transaction.atomic():
        user.save()
        examiner.save()


def createOfficeAccount(email, password):
    """Function creates a new Office Account."""
    user = User.objects.create_user(username=email, email=email, password=password)
    office = Office.objects.create(user=user)
    with transaction.atomic():
        user.save()
        office.save()


def confirmOrNotRequest(requestId, confirm, group, user=None):
    """Receives a student object, the user Group and the bool, that tells if the request should be confirmed.
    If the user is an Examiner, the user object is also needed.
    The function saves the confirmation in the database."""
    student = Student.objects.filter(id=requestId)[0]
    if group == "Office":
        student.officeConfirmed = confirm
        student.save()
    else:
        examinerId, intern = getExaminer(user)
        if student.supervisor1 == examinerId and student.isSupervisor1Intern == intern:
            student.supervisor1Confirmed = confirm
            student.save()
        elif student.supervisor2 == examinerId and student.isSupervisor2Intern == intern:
            student.supervisor2Confirmed = confirm
            student.save()
    checkStatus(student)


def getExaminer(user):
    """Receives a Django user object that should correspond to an examiner.
    The function returns a tuple that stores the examiner id and the boolean that says,
    if the examiner is intern or not."""
    if getUserGroup(user) == "Examiner":
        intern = False
        if InternExaminer.objects.filter(user=user).exists():
            intern = True
        if intern:
            examiner = InternExaminer.objects.filter(user=user)[0]
        else:
            examiner = ExternalExaminer.objects.filter(user=user)[0]
        return examiner.id, intern
    else:
        return False


def getRequestsOfOffice(status, accepted=None, allAccepted=None, allRated=None, supervisor3Needed=None,
                        appointmentEmerged=None, final=None):
    """The function returns the requests of the user group 'Office'.
        If a status is passed, all requests that have this status are returned.
        The other parameters can be used to receive more specific requests."""
    if status is not None:
        requests = Student.objects.filter(status=status).order_by('deadline')
        if accepted is not None:
            requests = requests.filter(officeConfirmed__isnull=not accepted)
        if allAccepted is not None:
            if allAccepted:
                requests = requests.filter(
                    officeConfirmed__isnull=False, supervisor1Confirmed__isnull=False,
                    supervisor2Confirmed__isnull=False
                )
            else:
                requests = requests.exclude(
                    officeConfirmed__isnull=False, supervisor1Confirmed__isnull=False,
                    supervisor2Confirmed__isnull=False
                )
        if allRated is not None:
            if allRated:
                requests = requests.filter(
                    Q(note1__isnull=False, note2__isnull=False, note3__isnull=False) |
                    Q(note1__isnull=False, note2__isnull=False, note1__gt=1, note2__gt=1)
                )
            else:
                requests = requests.exclude(
                    Q(note1__isnull=False, note2__isnull=False, note3__isnull=False) |
                    Q(note1__isnull=False, note2__isnull=False, note1__gt=1, note2__gt=1)
                )
        if supervisor3Needed is not None:
            if supervisor3Needed:
                requests = requests.filter(note1__isnull=False, note2__isnull=False, note1=1, note2=1)
            else:
                requests = requests.exclude(note1__isnull=False, note2__isnull=False, note1=1, note2=1)
        if appointmentEmerged is not None:
            requests = requests.filter(appointmentEmerged__isnull=not appointmentEmerged)
        if final is not None:
            requests = requests.filter(officeConfirmedAppointment__isnull=not final)
        return requests
    else:
        return False


def getRequestsOfExaminer(user, status, accepted=None, rated=None, answered=None, final=None):
    """The function returns the requests of the user group 'Examiner'.
    If a status is passed, all requests that have this status are returned.
    The other parameters can be used to receive more specific requests."""
    if status is not None:
        examinerId, intern = getExaminer(user)
        requests = Student.objects.filter(
            (Q(isSupervisor1Intern=intern, supervisor1=examinerId) |
             Q(isSupervisor2Intern=intern, supervisor2=examinerId) |
             Q(isSupervisor3Intern=intern, supervisor3=examinerId)), status=status
        )
        if accepted is not None:
            requests = requests.filter(
                Q(isSupervisor1Intern=intern, supervisor1=examinerId, supervisor1Confirmed__isnull=not accepted) |
                Q(isSupervisor2Intern=intern, supervisor2=examinerId, supervisor2Confirmed__isnull=not accepted)
            )
        if rated is not None:
            requests = requests.filter(
                Q(isSupervisor1Intern=intern, supervisor1=examinerId, note1__isnull=not rated) |
                Q(isSupervisor2Intern=intern, supervisor2=examinerId, note2__isnull=not rated) |
                Q(isSupervisor3Intern=intern, supervisor3=examinerId, note3__isnull=not rated)
            )
        if answered is not None:
            invitations = Invitation.objects.filter(
                examiner=examinerId, isExaminerIntern=intern, accepted__isnull=not answered
            )
            requests = requests.exclude(id__in=invitations.values('student'))
        if final is not None:
            requests = requests.filter(
                appointment__isnull=not final
            )
        return requests
    else:
        return False


def checkStatus(student):
    """This function get a student object and checks if the status must be changed.
    If so, the status will be adjusted."""
    if student.status == "Anfrage wird bestätigt":
        if student.officeConfirmed and student.supervisor1Confirmed and student.supervisor2Confirmed:
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
        if student.appointmentEmerged is not None and student.officeConfirmedAppointment is not None:
            student.status = "Termin entstanden"
            student.save()


def changeStatus(studentId, status):
    """Receives the Id of the Student/Request row and a status String.
    The function sets the status value of the request to the new status."""
    student = Student.objects.filter(id=studentId)
    if student.exists():
        student = student.first()
        student.status = status
        student.save()
    else:
        return False


def confirmAppointment(studentId):
    """Receives the Id of the Student/Request row.
    The function sets the value officeConfirmedAppointment of the request to True."""
    student = Student.objects.filter(id=studentId)
    if student.exists():
        student = student.first()
        student.officeConfirmedAppointment = True
        student.save()
    else:
        return False


def gradeRequest(user, studentId, note):
    """Receives a django user object, the id of the Student/Request and the note.
    The function sets the users note for the request."""
    student = Student.objects.filter(id=studentId)
    if student.exists():
        student = student.first()
        examinerId, intern = getExaminer(user)
        if student.supervisor1 == examinerId and student.isSupervisor1Intern == intern:
            student.note1 = note
            student.save()
        elif student.supervisor2 == examinerId and student.isSupervisor2Intern == intern:
            student.note2 = note
            student.save()
        elif student.supervisor3 == examinerId and student.isSupervisor3Intern == intern:
            student.note3 = note
            student.save()
        checkStatus(student)
    else:
        return False


def getOpenAvailabilities(studentId):
    """Receives the id of the Student/Request.
    Returns the time slots that are available for the request."""
    availabilities = AvailabilityRequest.objects.filter(student=studentId)
    if availabilities.exists():
        timeSlots = TimeSlot.objects.filter(id__in=availabilities.values('timeSlot'))
        return timeSlots
    else:
        return "all"


def acceptOrNotInvitation(user, studentId, confirm):
    """"Receives the django user object of an examiner and the id of the Student/Request.
    The Function saves the confirmation of the examiner inside the invitation row of the database."""
    examinerId, intern = getExaminer(user)
    invitation = Invitation.objects.filter(
        examiner=examinerId, isExaminerIntern=intern, student=studentId
    ).last()
    invitation.accepted = confirm
    invitation.save()


def answerInvitation(user, studentId, timeSlotIdsList):
    """Receives the django user object of an examiner and the id of the Student/Request.
    Another parameter is filled with the ids of the selected slots.
    Saves the chosen timeSlots for the invitation inside of the database."""
    examinerId, intern = getExaminer(user)
    invitation = Invitation.objects.filter(
        examiner=examinerId, isExaminerIntern=intern, student=studentId
    ).last()
    availabilities = []
    for id in timeSlotIdsList:
        timeSlot = TimeSlot.objects.filter(id=id).first()
        availabilities.append(AvailabilityInvitation(invitation=invitation, timeSlot=timeSlot))
    with transaction.atomic():
        for elem in availabilities:
            elem.save()
