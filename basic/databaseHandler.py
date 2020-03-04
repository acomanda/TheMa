from .models import *
import random
import string
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.db.models import F
from datetime import timedelta, datetime


def randomString(length=20):
    """
    This function returns a random string of the given length that contains letters and digits
    :param length: Integer that tells how long the result should be. (int)
    :return: Random string that contains letters and digits and is of the given length. (str)
    """
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
    """
    Checks if user is already registered and if it is, it returns the user,
    otherwise it creates the user and return it.
    :param email: E-Mail of the user (str)
    :param zdvId: ZDV Id of the user (int)
    :param state: State that the ZDV server returns (randomString, User group)
    :param stateLength: Length of the randomString in state (int)
    :param name: Name of the user (str)
    :return: The right Django user object (User)
    """
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
            with transaction.atomic():
                user.save()
                student.save()
            return user
        user = User.objects.filter(email=email)
        return user[0]

    if group == "pruefer":
        results = InternExaminer.objects.filter(email=email, zdvId__isnull=True)
        if results.exists():
            user = results[0].user
            setZdvId(user, zdvId)
            return user
        results = InternExaminer.objects.filter(email=email)
        if results.exists():
            user = results[0].user
            return user
        return False


def createInternExaminer(email, name):
    """
    Function is used to create a new account for an intern examiner
    :param email: ZDV E-Mail of the examiner (str)
    :param name: Name of the examiner (str)
    :return: Id of the new added account (int)
    """
    password = randomString()
    user = User.objects.create_user(username=email, email=email, password=password)
    examiner = InternExaminer.objects.create(name=name, email=email, user=user)
    with transaction.atomic():
        user.save()
        examiner.save()
    return examiner.id


def setZdvId(user, zdvId):
    """
    This function writes the given ZDV Id in the row of the examiner that is connected to the given user
    :param user: User Object of the examiner (User)
    :param zdvId: ZDV Id (int)
    :return:
    """
    examiner = InternExaminer.objects.filter(user=user)
    if examiner.count() == 0:
        return False
    examiner = examiner[0]
    examiner.zdvId = zdvId
    examiner.save()


def getUserGroup(user):
    """
    Receives a django user object and return the User Group of the user.
    :param user: User object (User)
    :return: String that tells which to which group the user belongs. (str)
    """
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
    """
    Receives a django user object and returns True,
    if the user is a student and the user has already make a request.
    :param user: User Object (User)
    :return: A boolean that tells if the user is a student and have made or not a request (bool)
    """
    student = Student.objects.filter(user=user)
    if student.exists() and student[0].deadline is not None:
        return True
    return False


def makeRequest(user, deadline, subject, supervisor1, supervisor2, topic, type, title, isSupervisor1Intern,
                isSupervisor2Intern):
    """
    Function initiates a students request.
    :param user: Django user object (User)
    :param deadline: Deadline date of submission of the thesis (Date)
    :param subject: Subject of the thesis (String)
    :param supervisor1: Id of the first supervisor of the request (Integer)
    :param supervisor2: Id of the second supervisor of the request (Integer)
    :param topic: Topic of the thesis (String)
    :param type: One String of ('b.sc.', 'm.sc.', 'dr.')
    :param title: Title opf the thesis (String)
    :param isSupervisor1Intern: bool that tells if the first supervisor is an intern one (Boolean)
    :param isSupervisor2Intern:bool that tells if the second supervisor is an intern one (Boolean)
    :return:
    """
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


def getStudentRequest(user, id=None, email=None):
    """
    Receives a django user object, studentId or email and returns the informations about the request of the student
    :param user: Django user object (User)
    :param id: Id of the student (int)
    :param email: E-Mail of the student (str)
    :return: Dictionary with the informations about the request
    """
    if user is not None:
        student = Student.objects.filter(user=user)[0]
    elif id is not None:
        student = Student.objects.filter(id=id)[0]
    elif email is not None:
        student = Student.objects.filter(email=email)
        if student.count() > 0:
            student = student[0]
        else:
            return None
    if student is None:
        return None
    result = {}
    result['title'] = student.title
    if student.isSupervisor1Intern:
        betreuer1 = InternExaminer.objects.filter(id=student.supervisor1)[0]
    else:
        betreuer1 = ExternalExaminer.objects.filter(id=student.supervisor1)[0]
    result['supervisor1'] = betreuer1
    if student.isSupervisor2Intern:
        betreuer2 = InternExaminer.objects.filter(id=student.supervisor2)[0]
    else:
        betreuer2 = ExternalExaminer.objects.filter(id=student.supervisor2)[0]
    if student.isSupervisor3Intern is not None:
        if student.isSupervisor3Intern:
            betreuer3 = InternExaminer.objects.filter(id=student.supervisor3)[0]
        else:
            betreuer3 = ExternalExaminer.objects.filter(id=student.supervisor3)[0]
        grade3 = student.grade3
    else:
        betreuer3 = None
        grade3 = None
    if student.appointment is not None:
        appointment = student.appointment.strftime("%m/%d/%Y %H/%M")
    else:
        appointment = None
    result['grade3'] = grade3
    result['supervisor3'] = betreuer3
    result['supervisor2'] = betreuer2
    result['deadline'] = student.deadline
    result['type'] = student.type
    result['status'] = student.status
    result['grade1'] = student.grade1
    result['grade2'] = student.grade2
    result['topic'] = student.topic
    result['subject'] = student.subject
    result['student'] = student.name
    result['appointment'] = appointment

    # Check if there are invited examiners
    if student.status == "Terminfindung" or "Termin entstanden":
        result.update(getRequestConstellation(student.id))
    return result


def updateRequest(variable, value, studentEmail):
    """
    This function writes the value in the column of variable in the row of the student that has the given E-Mail
    :param variable: Name of the column that should be updated (str)
    :param value: Value that will be written in the given column (/)
    :param studentEmail: E-Mail of the student (str)
    :return:
    """
    student = getStudent(None, None, studentEmail)
    if student is None:
        return False
    if variable == 'deadline':
        student.deadline = value
    elif variable == 'title':
        student.title = value
    elif variable == 'subject':
        student.subject = value
    elif variable == 'topic':
        student.topic = value
    elif variable == 'type':
        student.type = value
    elif variable == 'supervisor1':
        student.isSupervisor1Intern = value[0]
        student.supervisor1 = value[1:]
        student.grade1 = None
    elif variable == 'supervisor2':
        student.isSupervisor2Intern = value[0]
        student.supervisor2 = value[1:]
        student.grade2 = None
    elif variable == 'supervisor3':
        student.isSupervisor3Intern = value[0]
        student.supervisor3 = value[1:]
        student.grade3 = None
    elif variable == 'grade1':
        student.grade1 = value
    elif variable == 'grade2':
        student.grade2 = value
    elif variable == 'grade3':
        student.grade3 = value
    elif variable == 'appointment':
        student.appointment = value
    elif variable == 'supervisor1Confirmed':
        student.supervisor1Confirmed = value
    elif variable == 'supervisor2Confirmed':
        student.supervisor2Confirmed = value
    elif variable == 'officeConfirmed':
        student.officeConfirmed = value
    student.save()


def createExternalExaminer(name, email, password):
    """
    Function creates a new External Examiner
    :param name: Name of the new examiner (String)
    :param email: E-Mail of the new examiner (String)
    :param password: Password of the new examiner (String)
    :return: Id of the newly added examiner (int)
    """
    user = User.objects.create_user(username=email, email=email, password=password)
    examiner = ExternalExaminer.objects.create(name=name, email=email, user=user)
    with transaction.atomic():
        user.save()
        examiner.save()
    return examiner.id


def createOfficeAccount(email, password):
    """
    Function creates a new Office Account.
    :param email: E-Mail of the new office account (String)
    :param password: Password of the new office account (String)
    :return:
    """
    user = User.objects.create_user(username=email, email=email, password=password)
    office = Office.objects.create(user=user)
    with transaction.atomic():
        user.save()
        office.save()


def confirmOrNotRequest(requestId, confirm, group, user=None):
    """
    Receives a student object, the user Group and the bool, that tells if the request should be confirmed.
    If the user is an Examiner, the user object is also needed.
    The function saves the confirmation in the database.
    :param requestId: Id of the student/request (Integer)
    :param confirm: Tells, if the Request must be confirmed or not (Boolean)
    :param group: Group of the user that is calling the function (String)
    :param user: Django user object (User)
    :return: Tells if the status of the request was adjusted (bool)
    """
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
    return checkStatus(student)


def getExaminer(user, examinerId = None, intern=None, email=None):
    """
    If the user is given, the function returns the examiner Object.
    If user is None and the other two parameters are not None, then the function returns
    a tuple that contains the examiner Id and a bool that tells if it is an intern or external examiner
    :param user: Django User Object (User)
    :param examinerId: Id of the examiner (int)
    :param intern:
    :return: Examiner Object or (examinerId, isIntern)
    """
    if user is not None:
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
    elif examinerId:
        if intern:
            examiner = InternExaminer.objects.filter(id=examinerId)
        else:
            examiner = ExternalExaminer.objects.filter(id=examinerId)
    elif email:
        if intern:
            examiner = InternExaminer.objects.filter(email=email)
        else:
            examiner = ExternalExaminer.objects.filter(email=email)
    if examiner.count() > 0:
        return examiner[0]
    else:
        return False


def getRequestsOfOffice(status, accepted=None, allAccepted=None, allRated=None, supervisor3Needed=None,
                        appointmentEmerged=None, final=None):
    """
    The function returns the requests of the user group 'Office'.
    If a status is passed, all requests that have this status are returned.
    The other parameters can be used to receive more specific requests.
    :param status: Status of the requested requests
    :param accepted: Bool that tells if the requests should be already accepted by the office
    :param allAccepted: Bool that tells if the requests should be already accepted by all supervisors and office
    :param allRated: Bool that tells if the requests should be already rated by all supervisors
    :param supervisor3Needed: Bool that tells if the requests should need a third supervisor
    :param appointmentEmerged: Bool that tells if the requests should have an emerged appointment
    :param final: Bool that tells if the request should be already processed
    :return: QuerySet with all resulting requests Objects
    """
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
                    Q(grade1__isnull=False, grade2__isnull=False, grade3__isnull=False) |
                    (Q(grade1__isnull=False, grade2__isnull=False) and Q(grade1__gt=1) | Q(grade2__gt=1))
                )
            else:
                requests = requests.exclude(
                    Q(grade1__isnull=False, grade2__isnull=False, grade3__isnull=False) |
                    Q(grade1__isnull=False, grade2__isnull=False, grade1__gt=1, grade2__gt=1)
                )
        if supervisor3Needed is not None:
            if supervisor3Needed:
                requests = requests.filter(grade1__isnull=False, grade2__isnull=False, grade1=1, grade2=1,
                                           supervisor3__isnull=True)
            else:
                requests = requests.exclude(grade1__isnull=False, grade2__isnull=False, grade1=1, grade2=1)
        if appointmentEmerged is not None:
            requests = requests.filter(appointmentEmerged__isnull=not appointmentEmerged)
        if final is not None:
            requests = requests.filter(officeConfirmedAppointment__isnull=not final)
        return requests
    else:
        return False


def getRequestsOfExaminer(user, status, accepted=None, rated=None, answered=None, final=None, supervisor=None):
    """
    The function returns the requests of the examiner that is connected to the user Object.
    If a status is passed, all requests that have this status are returned.
    The other parameters can be used to receive more specific requests.
    :param user: Django User Object of the examiner (User)
    :param status: Status of the requested requests
    :param accepted: Bool that tells if the requests should be already accepted by the given examiner
    :param rated: Bool that tells if the requests should be already rated by the given examiner
    :param answered: Bool that tells if the requests should be already answered by the given examiner
    :param final: Bool that tells if the requests should be already processed
    :param supervisor: Bool that tells if the requests should have the examiner as a supervisor
    :return: QuerySet with all resulting requests Objects
    """
    if status is not None and user is not None:
        examinerId, intern = getExaminer(user)
        if not supervisor:
            requests = Student.objects.filter(status=status)
            invitations = Invitation.objects.filter(
                examiner=examinerId, isExaminerIntern=intern
            )
            requests = requests.filter(id__in=invitations.values('student'))
        else:
            requests = Student.objects.filter(
                (Q(isSupervisor1Intern=intern, supervisor1=examinerId) |
                 Q(isSupervisor2Intern=intern, supervisor2=examinerId) |
                 Q(isSupervisor3Intern=intern, supervisor3=examinerId)), status=status
            )
        if accepted is not None:
            if supervisor:
                requests = requests.filter(
                    Q(isSupervisor1Intern=intern, supervisor1=examinerId, supervisor1Confirmed__isnull=not accepted) |
                    Q(isSupervisor2Intern=intern, supervisor2=examinerId, supervisor2Confirmed__isnull=not accepted)
                )
        if rated is not None:
            if supervisor:
                requests = requests.filter(
                    Q(isSupervisor1Intern=intern, supervisor1=examinerId, grade1__isnull=not rated) |
                    Q(isSupervisor2Intern=intern, supervisor2=examinerId, grade2__isnull=not rated) |
                    Q(isSupervisor3Intern=intern, supervisor3=examinerId, grade3__isnull=not rated)
                )
        if answered is not None:
            invitations = Invitation.objects.filter(
                examiner=examinerId, isExaminerIntern=intern, accepted__isnull=answered
            )
            requests = requests.exclude(id__in=invitations.values('student'))
        if final is not None:
            requests = requests.filter(
                officeConfirmedAppointment__isnull=not final
            )
        return requests
    else:
        return False


def checkStatus(student):
    """
    This function get a student object and checks if the status must be changed.
    If so, the status will be adjusted
    :param student: Student Object (Student)
    :return: Bool that tells if the status have been changed
    """
    if student.status == "Anfrage wird bestätigt":
        if student.officeConfirmed and student.supervisor1Confirmed and student.supervisor2Confirmed:
            student.status = "Schreibphase"
            student.save()
            return True
    if student.status == "Terminfindung":
        if student.appointmentEmerged is not None and student.officeConfirmedAppointment is not None:
            student.status = "Termin entstanden"
            student.save()
            return True
    return False


def changeStatus(studentId, status):
    """
    This function is used to change the status of a request
    :param studentId: Id of the Student (int)
    :param status: New value for status (str)
    :return: Bool that tells if the student Id corresponds to a student in the database
    """
    student = Student.objects.filter(id=studentId)
    if student.exists():
        student = student.first()
        student.status = status
        student.save()
    else:
        return False


def confirmAppointment(studentId):
    """
    The function sets the value officeConfirmedAppointment of the request to True
    :param studentId: Id of the student (int)
    :return: Bool that tells if the student Id corresponds to a student in the database
    """
    student = Student.objects.filter(id=studentId)
    if student.exists():
        student = student.first()
        student.officeConfirmedAppointment = True
        student.save()
    else:
        return False


def gradeRequest(user, studentId, note):
    """
    The function sets the grade of the examiner(user) for the student
    :param user: Django user object of the examiner (User)
    :param studentId: Id of the student (int)
    :param note: Grade between 1 and 5 (float)
    :return: Bool that tells if the id corresponds to a student and if the status of the student have been adjusted
    """
    student = Student.objects.filter(id=studentId)
    if student.exists():
        student = student.first()
        examinerId, intern = getExaminer(user)
        if student.supervisor1 == examinerId and student.isSupervisor1Intern == intern:
            student.grade1 = note
            student.save()
        elif student.supervisor2 == examinerId and student.isSupervisor2Intern == intern:
            student.grade2 = note
            student.save()
        elif student.supervisor3 == examinerId and student.isSupervisor3Intern == intern:
            student.grade3 = note
            student.save()
        return checkStatus(student)
    else:
        return False


def getOpenAvailabilities(studentId):
    """
    Returns the time slots that are available for the request
    :param studentId: Id of the student (int)
    :return: If no availabilities are set: 'all' (str)
             otherwise: QuerySet that contains all available timeSlots (QuerySet)
    """
    availabilities = AvailabilityRequest.objects.filter(student=studentId)
    if availabilities.exists():
        timeSlots = TimeSlot.objects.filter(id__in=availabilities.values('timeSlot'))
        return timeSlots
    else:
        return "all"


def acceptOrNotInvitation(user, studentId, confirm):
    """
    The Function saves the confirmation of the examiner inside the invitation row of the database
    :param user: Django User Object of the examiner (User)
    :param studentId: Id of the student (int)
    :param confirm: Bool that tells if the user want to accept or decline the invitation of the student (bool)
    :return:
    """
    examinerId, intern = getExaminer(user)
    invitation = Invitation.objects.filter(
        examiner=examinerId, isExaminerIntern=intern, student=studentId
    ).last()
    invitation.accepted = confirm
    invitation.save()


def answerInvitation(user, studentId, timeSlotIdsList):
    """
    Saves the chosen timeSlots for the invitation inside of the database
    :param user: Django User Object of the examiner (User)
    :param studentId: Id of the student (int)
    :param timeSlotIdsList: List of all Ids of the chosen timeSlots
    :return:
    """
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


def getExaminers(approvalToTest=None, subject=None, topic=None, title=None, excludedTopic=None, excludedExaminers=None,
                 maxInvitation=None):
    """
    Returns all examiners that correspond to the given specification
    :param approvalToTest: Bool that tells if the examiner should have an approval to be in an oral exam (bool)
    :param subject: The examiners should have this subject (str)
    :param topic: The examiners should have this topic (str)
    :param title: The examiners should have this title (str)
    :param excludedTopic: All examiners that have one of this topics are excluded ([str])
    :param excludedExaminers: All examiners in this list should be excluded ([Examiner objects])
    :param maxInvitation: Exclude all examiners that have a higher value in numberInvitations than maxInvitation (int)
    :return:(QuerySet filled with all resulting external Examiners, QuerySet filled with all resulting intern examiners)
    """
    # todo if a user doesnt have a qualification it should not be included in topic excluded
    qualifications = Qualification.objects.all()
    if approvalToTest is not None:
        qualifications = qualifications.intersection(Qualification.objects.filter(approvalToTest=approvalToTest))
    if subject is not None:
        qualifications = qualifications.intersection(Qualification.objects.filter(subject=subject))
    if topic is not None:
        qualifications = qualifications.intersection(Qualification.objects.filter(topic=topic))
    if title is not None:
        qualifications = qualifications.intersection(Qualification.objects.filter(title=title))
    if excludedTopic is not None:
        qualifications = qualifications.intersection(Qualification.objects.exclude(topic=excludedTopic))
    externalExaminers = ExternalExaminer.objects.all()
    internExaminers = InternExaminer.objects.all()
    externalQualifications = qualifications.intersection(Qualification.objects.filter(isExaminerIntern=False))
    internalQualifications = qualifications.intersection(Qualification.objects.filter(isExaminerIntern=True))
    externalExaminers = externalExaminers and ExternalExaminer.objects.filter(
        id__in=[o.examiner for o in externalQualifications])
    internExaminers = internExaminers and InternExaminer.objects.filter(
        id__in=[o.examiner for o in internalQualifications])
    if excludedExaminers is not None:
        externalExaminers = externalExaminers.intersection(ExternalExaminer.objects.filter(
            ~Q(user_id__in=[o.user_id for o in excludedExaminers])))
        internExaminers = internExaminers.intersection(InternExaminer.objects.exclude(
            ~Q(user_id__in=[o.user_id for o in excludedExaminers])))
    if maxInvitation is not None:
        invitationsExternal = Invitation.objects.filter(numberInvitations__gt=maxInvitation, isExaminerIntern=0)
        invitationsIntern = Invitation.objects.filter(numberInvitations__gt=maxInvitation, isExaminerIntern=1)
        externalExaminers = externalExaminers.intersection(ExternalExaminer.objects.exclude(id__in=[o.examiner for o in invitationsExternal]))
        internExaminers = internExaminers.intersection(InternExaminer.objects.exclude(id__in=[o.examiner for o in invitationsIntern]))
    return externalExaminers, internExaminers


def setSupervisor3(studentId, examiner, isExaminerIntern):
    """
    The function sets this examiner as the third supervisor of the student
    :param studentId: Id of the student (int)
    :param examiner: Examiner Id that is set as the third supervisor (int)
    :param isExaminerIntern: Bool that tells if the examiner is intern or external (bool)
    :return: Bool that tells if a student exists that has the given Id
    """
    student = Student.objects.filter(id=studentId)
    if student.exists():
        student = student.first()
        if (student.isSupervisor1Intern == isExaminerIntern and student.supervisor1 == examiner) | \
                (student.isSupervisor2Intern == isExaminerIntern and student.supervisor2 == examiner):
            return False
        student.isSupervisor3Intern = isExaminerIntern
        student.supervisor3 = examiner
        student.save()
        return True
    else:
        return False


def getSubjects():
    """
    Returns all subjects of the database
    :return: [str]
    """
    """Returns all functions of the database."""
    qualifications = Qualification.objects.all()
    subjects = qualifications.values_list('subject').distinct()
    result = []
    for elem in subjects:
        result.append(elem[0])
    return result


def getTopics(subject):
    """
    Returns all topics that correpsonds to the given subject
    :param subject: Name of the subject (str)
    :return: [str]
    """
    """Returns all topics that correspond to the givenn subject"""
    qualifications = Qualification.objects.filter(subject=subject)
    topics = qualifications.values_list('topic').distinct()
    result = []
    for elem in topics:
        result.append(elem[0])
    return result


def inviteExaminer(student, examiner, role):
    """
    Creates the invitation for one examiner for one request
    :param student: Student Object (Student)
    :param examiner: Examiner Object
    :param role: Role that the invited examiner should take (str)
    :return:
    """
    if isinstance(examiner, ExternalExaminer):
        intern = 0
    elif isinstance(examiner, InternExaminer):
        intern = 1
    invitation = Invitation.objects.filter(examiner=examiner.id, isExaminerIntern=intern, student=student)
    if invitation.count() == 1:
        invitation = invitation[0]
        invitation.accepted = None
        invitation.numberInvitations += 1
        invitation.role = role
        invitation.save()
    else:
        invitation = Invitation(examiner=examiner.id, isExaminerIntern=intern, student=student, role=role,
                                numberInvitations=1)
        invitation.save()


def getStudent(user, studentId=None, email=None):
    """
    This function is used to receive a student object.
    The student can be specificated by using the Django User Object, Id, or E-Mail of the student.
    One should be not None and the other set to None.
    :param user: Django User Object of the student (User)
    :param studentId: Id of the student (int)
    :param email: E-Mail of the student (str)
    :return: Student object of the requested student (Student)
    """
    if user is not None:
        student = Student.objects.filter(user=user)
    elif studentId is not None:
        student = Student.objects.filter(id=studentId)
    elif email is not None:
        student = Student.objects.filter(email=email)
    if student.exists():
        return student[0]


def acceptOrRejectingInvitation(user, studentId, accept):
    """
    Function store in the database if an examiner accept or reject an invitation
    :param user: Django user object of the examiner (User)
    :param studentId: Student id (int)
    :param accept: Boolean that tells if the examiner accept or reject the invitation (bool)
    :return:
    """
    examinerId, intern = getExaminer(user)
    invitation = Invitation.objects.filter(student_id=studentId, examiner=examinerId, isExaminerIntern=intern)[0]
    invitation.accepted = accept
    invitation.save()


def addAvailabilityToInvitation(user, studentId, timeSlotId):
    """
    Function stores in the database the availability for the invitation
    :param user: Django user object of the examiner (User)
    :param studentId: Student id (int)
    :param timeSlotId: Id of the timeSlot that should be set as availability (int)
    :return:
    """
    examinerId, intern = getExaminer(user)
    invitation = Invitation.objects.filter(student_id=studentId, examiner=examinerId, isExaminerIntern=intern)[0]
    timeSlot = TimeSlot.objects.filter(id=timeSlotId)[0]
    if AvailabilityInvitation.objects.filter(invitation=invitation, timeSlot=timeSlot).count() == 0:
        availability = AvailabilityInvitation(invitation=invitation, timeSlot=timeSlot)
        availability.save()


def deleteAvailabilityOfInvitation(user, studentId, timeSlotId):
    """
    Deletes the row of AvailabilityInvitation that correspond to the examiner, request and timeSlot
    :param user: Django user object of the examiner (User)
    :param studentId: Id of the student/request (int)
    :param timeSlotId: Id of the timeSlot (int)
    :return:
    """
    examinerId, intern = getExaminer(user)
    invitation = Invitation.objects.filter(student_id=studentId, examiner=examinerId, isExaminerIntern=intern)[0]
    availability = AvailabilityInvitation.objects.filter(invitation=invitation, timeSlot_id=timeSlotId)
    availability.delete()


def getRecentAvailabilities(user, studentId, start, end):
    """

    :param user: Django user object of the examiner (User)
    :param studentId: Id of the student/request (int)
    :param start: First day of the week as a date (date)
    :param end: Last day of the week as a date (date)
    :return: The timeSlots, that were added recently and have not yet been moved to AvailabilityRequest (QuerySet)
    """
    examinerId, intern = getExaminer(user)
    invitation = Invitation.objects.filter(student_id=studentId, examiner=examinerId, isExaminerIntern=intern)[0]
    if start is not None and end is not None:
        start = datetime.strptime(start, "%m/%d/%Y")
        end = datetime.strptime(end, "%m/%d/%Y") + timedelta(days=1)
        availabilities = AvailabilityInvitation.objects.filter(timeSlot__start__gte=start, timeSlot__start__lte=end,
                                                               invitation=invitation)
    else:
        availabilities = AvailabilityInvitation.objects.filter(invitation=invitation)

    slots = TimeSlot.objects.filter(id__in=[o.timeSlot_id for o in availabilities],
                                    availabilityinvitation__deleted__isnull=True)
    return slots


def moveAvailabilitiesToRequest(user, studentId):
    """
    Updates the time slots in AvailabilityRequest of the given examiner and request
    :param user: Django user objectof the examiner (User)
    :param studentId: Id of the student/request (int)
    :return:
    """
    examinerId, intern = getExaminer(user)
    invitation = Invitation.objects.filter(student_id=studentId, examiner=examinerId, isExaminerIntern=intern)[0]
    invitationAvailabilities = AvailabilityInvitation.objects.filter(invitation=invitation)
    requestAvailabilities = AvailabilityRequest.objects.filter(student_id=studentId)
    if requestAvailabilities.count() == 0:
        rows = []
        for elem in invitationAvailabilities:
            rows.append(AvailabilityRequest(student_id=studentId, timeSlot=elem.timeSlot))
        with transaction.atomic():
            for elem in rows:
                elem.save()
    else:
        AvailabilityRequest.objects.filter(student_id=studentId)\
            .exclude(timeSlot__in=invitationAvailabilities.values('timeSlot')).delete()
        remainingAvailabilities = AvailabilityRequest.objects.filter(student_id=studentId)
        invitations = Invitation.objects.filter(student_id=studentId)
        AvailabilityInvitation.objects.filter(invitation_id__in=[o.id for o in invitations]).exclude(
            timeSlot_id__in=[o.timeSlot_id for o in remainingAvailabilities]).update(
                deleted=False
            )


def generateTimeSlots(year):
    """
    Writes all possible time slots for the given year into the database
    :param year: Year as an Integer (int)
    :return: Boolean that says whether the function was successful (bool)
    """
    daysPerYear = getDaysPerYear(year)
    startDate = datetime(year, 1, 1, 8, 0)
    for td in (startDate + timedelta(days=it + 1) for it in range(daysPerYear-1)):
        if td.weekday() < 5:
            for td2 in (td + timedelta(hours=2*it2) for it2 in range(5)):
                TimeSlot(start=td2).save()
    return True


def deleteTimeSlots(year):
    """
    Deletes all time slots of the given year
    :param year: Year as an Integer (int)
    :return: Boolean that says whether the function was successful (bool)
    """
    TimeSlot.objects.filter(start__year=year).delete()
    return True


def getTimeSlots(studentId, start, end):
    """
    Searches the available time slots for an invitation from one day to another day and returns them.
    :param studentId: Id of the request/student (int)
    :param start: First day of the week as a date (date)
    :param end: Last day of the week as a date (date)
    :return: QuerySet with all availabilities (QuerySet)
    """
    start = datetime.strptime(start, "%m/%d/%Y")
    end = datetime.strptime(end, "%m/%d/%Y") + timedelta(days=1)
    availabilities = AvailabilityRequest.objects.filter(student_id=studentId, timeSlot__start__gte=start,
                                                        timeSlot__start__lte=end)
    if AvailabilityRequest.objects.filter(student_id=studentId).count() == 0:
        invitations = Invitation.objects.filter(student_id=studentId)
        new = True
        for invitation in invitations:
            if invitation.accepted:
                new = False
        if new:
            slots = TimeSlot.objects.filter(start__gte=start, start__lte=end)
            return slots
        else:
            return TimeSlot.objects.none()
    slots = TimeSlot.objects.filter(id__in=[o.timeSlot_id for o in availabilities])
    return slots

def getWeekSlots(timeSlots, start):
    """
    This function is used to order a set of timeSlots into a week format
    :param timeSlots: A Query Set of Time Slots (QuerySet)
    :return: A dictionary that divides the time slots into days and times of the week. (dict)
    """
    dict = {'1': {'8': None, '10': None, '12': None, '14': None, '16': None},
            '2': {'8': None, '10': None, '12': None, '14': None, '16': None},
            '3': {'8': None, '10': None, '12': None, '14': None, '16': None},
            '4': {'8': None, '10': None, '12': None, '14': None, '16': None},
            '5': {'8': None, '10': None, '12': None, '14': None, '16': None}}
    for i in range(1, 6):
        for j in range(8, 17, 2):
            date = (datetime.strptime(start, "%m/%d/%Y") + timedelta(days=i-1))
            slots = timeSlots.filter(start__day=date.day, start__month=date.month, start__year=date.year, start__hour=j)
            if slots.count() > 0:
                dict[str(i)][str(j)] = slots.first()
    return dict


def getDaysPerYear(year):
    """
    Is used to get te number of das in a certain year
    :param year: Year as an Integer (int)
    :return: Number of days in the year (int)
    """
    if (year % 4 == 0) and (year % 100 != 0) or (year % 400 == 0):
        return 366
    return 365


def getRequestConstellation(studentId, accepted=None):
    """
    This function is used to receive the current constellation of examiners for the oral exam
    :param studentId: Id of the student (int)
    :param accepted: Bool that tells if only the examiners should be returned, that have already accepted the invitation
    :return: Dictionary that contains the specified constellation of examiners (dict)
    """
    if accepted:
        invitations = Invitation.objects.filter(student_id=studentId, accepted=True)
    else:
        invitations = Invitation.objects.filter(Q(student_id=studentId, accepted=True) |
                                                Q(student_id=studentId, accepted__isnull=True))
    constellation = {}
    for elem in invitations:
        constellation[elem.role] = getExaminer(None, elem.examiner, elem.isExaminerIntern)
    return constellation


def getStudentId(email):
    """
    This function is used to receive the Id of the student that has the given email
    :param email: E-mail of the student (str)
    :return: Id of the specified student (int)
    """
    student = Student.objects.filter(email=email)
    if student.count() > 0:
        return student[0].id


def setAppointmentEmerged(studentId):
    """
    This function sets the column appointmentEmerged of a student to True
    :param studentId: Id of the student (int)
    :return:
    """
    student = Student.objects.filter(id=studentId)[0]
    student.appointmentEmerged = True
    student.status = "Termin entstanden"
    student.save()


def getRole(examinerId, isExaminerIntern, studentId):
    """
    This function is used to receive the role that was assigned to the given examiner for the given student oral exam
    :param examinerId: Id of the examiner (int)
    :param isExaminerIntern: Bool that tells if the examiner is intern or external (bool)
    :param studentId: Id of the student (int)
    :return: Role of the examiner for the students oral exam (str)
    """
    invitation = Invitation.objects.filter(examiner=examinerId, isExaminerIntern=isExaminerIntern,
                                           student_id=studentId)[0]
    return invitation.role


def getStudentUser(studentId):
    """
    This function is used to receive the student object of the student that has the given Id
    :param studentId: Id of the student (int)
    :return: student object (Student)
    """
    student = Student.objects.filter(id=studentId)[0]
    return student.user


def isSupervisorOrChairman(studentId, examinerId, intern):
    """
    This function is used to know if the given examiner is a supervisor or a chairman of the given student
    :param studentId: Id of the student (int)
    :param examinerId: Id of the examiner (int)
    :param intern: Bool that tells if the examiner is intern or external (bool)
    :return: Bool that tells if the examiner is a supervisor or chairman of the student (bool)
    """
    student = Student.objects.filter(id=studentId)
    if student.count() == 1:
        student = student[0]
        if student.supervisor1 == examinerId and student.isSupervisor1Intern == intern:
            return True
        if student.supervisor2 == examinerId and student.isSupervisor2Intern == intern:
            return True
        if student.supervisor3 == examinerId and student.isSupervisor3Intern == intern:
            return True
        invitation = Invitation.objects.filter(student_id=studentId, examiner=examinerId, isExaminerIntern=intern)
        if invitation.count() > 0:
            invitation = invitation[0]
            if invitation.role == "chairman":
                return True
        return False


def getRequestsAppointments(studentId):
    """
    This function is used to receive all timeSlots that are currently possible for the students oral exam.
    It doesn't mean that all examiners have already accepted the invitation.
    :param studentId: Id of the student (int)
    :return: List of all the time slots objects ([TimeSlot])
    """
    slotsId = AvailabilityRequest.objects.filter(student_id=studentId)
    if slotsId.count() > 0:
        slots = TimeSlot.objects.filter(id__in=[o.timeSlot_id for o in slotsId])
        return slots
    else:
        return False


def endRequest(studentId, slotId):
    """
    This function is used to choose a final timeSlot for the appointment of the given student
    :param studentId: Id of the student (int)
    :param slotId: Id of the time slot (int)
    :return:
    """
    student = Student.objects.filter(id=studentId)
    if student.count() > 0:
        student = student[0]
        timeSlot = TimeSlot.objects.filter(id=slotId)[0]
        student.officeConfirmedAppointment = True
        student.appointment = timeSlot.start
        student.save()


def restartScheduling(studentId, maxInvitation):
    """
    The function deletes all availabilities for the oral exam of the given student and re invites all examiners.
    :param studentId: Id of the student (int)
    :return: An array that contains all examiners that must be removed of the request [(examiner Id, isExaminerIntern)]
    """
    result = []
    invitations = Invitation.objects.filter(student_id=studentId)
    with transaction.atomic():
        invitations.filter(accepted__isnull=False).update(accepted=None, numberInvitations=F('numberInvitations')+1)
        AvailabilityRequest.objects.filter(student_id=studentId).delete()
        AvailabilityInvitation.objects.filter(invitation__in=[o for o in invitations]).delete()
    for elem in invitations:
        if elem.numberInvitations > maxInvitation:
            elem.accepted = 0
            elem.save()
            result.append((elem.examiner, elem.isExaminerIntern))
    return result


def reInviteExaminer(studentId, examinerId, intern, maxInvitation, role):
    """
    This function is used to invite or reinvite an examiner for the oral exam of the given student
    :param studentId: Id of the student (int)
    :param examinerId: Id of the examiner (int)
    :param intern: Bool that tells if the examiner is intern or external (bool)
    :param maxInvitation: Maximum number of invitations that can be send to an examiner (int)
    :param role: Role that should be assigned to the examiner for this invitation (str)
    :return: True if the examiner have been invited, otherwise False (bool)
    """
    invitation = Invitation.objects.filter(student_id=studentId, examiner=examinerId, isExaminerIntern=intern)
    if invitation.count() == 0:
        inviteExaminer(getStudent(None, studentId), getExaminer(None, examinerId, intern), role)
        return True
    if invitation[0].numberInvitations >= maxInvitation or invitation[0].accepted is None or \
            invitation[0].accepted == True:
        return False
    invitation.update(accepted=None, numberInvitations=F('numberInvitations')+1, role=role)
    updateAvailabilities(studentId)
    return True


def updateAvailabilities(studentId):
    """
    This function updates the available time Slots for a students oral exam.
    Should be called when an examiner has answered the invitation
    :param studentId: Id of the student
    :return:
    """
    invitations = Invitation.objects.filter(student_id=studentId, accepted=True)
    timeSlots = []
    for elem in invitations:
        availabilities = AvailabilityInvitation.objects.filter(invitation=elem, deleted__isnull=True)
        for elem in availabilities:
            if elem.timeSlot not in timeSlots:
                timeSlots.append(elem.timeSlot)
    for elem in timeSlots:
        if AvailabilityRequest.objects.filter(student_id=studentId, timeSlot=elem).count() == 0:
            AvailabilityRequest(student_id=studentId, timeSlot=elem).save()


def addQualification(examinerId, isExaminerIntern, title, subject, topic, approval):
    """
    This function adds a new qualification to an existing examiner
    :param examinerId: Id of the examiner (int)
    :param isExaminerIntern: Bool that tells if the examiner is intern or external (bool)
    :param title: Title of the examiner for this qualification ('dr.', 'b.sc.', 'm.sc.')(str)
    :param subject: Subject of the qualification (str)
    :param topic: Topic of the qualification (str)
    :param approval: Bool that tells if the examiner has the approval to be an examiner for this subject (bool)
    :return:
    """
    qualification = Qualification(title=title, subject=subject, topic=topic, approvalToTest=approval,
                                  examiner=examinerId, isExaminerIntern=isExaminerIntern)
    qualification.save()


def setExam(studentId, timeSlot, constellation):
    """
    This function sets all invitations for the students oral exam to rejected and
    defines a new constellation and appointment
    :param studentId: Id of the student
    :param timeSlot: Id of the time slot in which the oral exam takes place
    :param constellation: Dictionary of the form role: examiner ({str:Examiner})
    :return: True if no errors occured (bool)
    """
    # set all invitations to rejected
    Invitation.objects.filter(student_id=studentId).update(accepted=False)
    for role, examiner in constellation.items():
        examinerData = getExaminerInformations(examiner)
        invitation = Invitation.objects.filter(examiner=examinerData['id'], isExaminerIntern=examinerData['isIntern'],
                                  student_id=studentId)
        if invitation.count() > 0:
            invitation.update(accepted=True)
        else:
            Invitation(accepted=True, numberInvitations=1, examiner=examinerData['id'],
                       isExaminerIntern=examinerData['isIntern'], student_id=studentId, role=role).save()
    Student.objects.filter(id=studentId).update(officeConfirmedAppointment=True, appointmentEmerged=True,
                                                appointment=timeSlot)
    return True



def checkConstellation(studentId, constellation):
    """
    This function checks if the constellation is allowed
    :param studentId: Id of the student (int)
    :param constellation: Constellation of examiners for the oral exam of the student (dict)
    :return: True if it is allowed, otherwise False (bool)
    """
    result = True
    # check that there are not the same examiner twice in the constellation
    if not len(list(constellation.values())) == len(set(list(constellation.values()))):
        result = False
    requestData = getStudentRequest(None, studentId)
    # Check that the supervisors are in the constellation
    if requestData['supervisor1'] not in list(constellation.values()):
        result = False
    if requestData['supervisor2'] not in list(constellation.values()):
        result = False
    # check that the external examiner is external
    externalExaminerData = getExaminerInformations(constellation['externalExaminer'])
    if requestData['topic'] in externalExaminerData['topic']:
        result = False
    # check if every examiner has the approval to test in this topic
    return result


def getExaminerInformations(examiner):
    """
    This function is used to receive a dictionary with some informations about the given examiner
    :param examiner: Examiner object (InternExaminer or ExternalExaminer)
    :return: Dictionary that contains informations about the examiner such as topic isIntern id... (dict)
    """
    result = {}
    if isinstance(examiner, ExternalExaminer):
        intern = 0
    elif isinstance(examiner, InternExaminer):
        intern = 1
    result['topic'] = []
    result['subject'] = []
    result['title'] = []
    result['approval'] = []
    result['qualId'] = []
    result['isIntern'] = intern
    result['id'] = examiner.id
    qualification = Qualification.objects.filter(isExaminerIntern=intern, examiner=examiner.id)
    for elem in qualification:
        result['topic'].append(elem.topic)
        result['subject'].append(elem.subject)
        result['title'].append(elem.title)
        result['approval'].append(elem.approvalToTest)
        result['qualId'].append(elem.id)
    return result


def deleteQualification(id):
    """
    This function deletes the qualification with the given id
    :param id: Id of the qualification (int)
    :return: True if the id corresponds to a qualification, otherwise False (Bool)
    """
    objects = Qualification.objects.filter(id=id)
    if objects.count() > 0:
        objects[0].delete()
    else:
        return False


def getOffice():
    """
    This function is used to receive an office object
    :return: The first Office object of the database (Office)
    """
    return Office.objects.filter(id=1)[0]


def isRequestRejected(student):
    """
    This function is used to check if a students request was declined by a supervisor or the office
    :param student: Student object (Student)
    :return: True if someone declined the request, otherwise False (bool)
    """
    if student.supervisor1Confirmed is not None and not student.supervisor1Confirmed:
        return True
    if student.supervisor2Confirmed is not None and not student.supervisor2Confirmed:
        return True
    if student.officeConfirmed is not None and not student.officeConfirmed:
        return True
    return False


def noPossibleConstellation(student):
    """
    This function is used to check if a request doesnt't have a constellation of examiners for the oral exam
    because there are no more possible constellations
    :param student: Student object (Student)
    :return: True if there are no more constellations, otherwise False (bool)
    """
    accepted = Invitation.objects.filter(student=student, accepted=True).count()
    notAnswered = Invitation.objects.filter(student=student, accepted=None).count()
    if accepted + notAnswered < 5:
        return True
    return False