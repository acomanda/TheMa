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

    :param length: Integer that tells how long the result should be.
    :return: Random string that contains letters and digits and is of the given length.
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
    :param email: E-Mail of the user
    :param zdvId: ZDV Id of the user
    :param state: State that the ZDV server returns (randomString, User group)
    :param stateLength: Length of the randomString in state
    :param name: Name of the user
    :return: The right Django user object
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
    password = randomString()
    user = User.objects.create_user(username=email, email=email, password=password)
    examiner = InternExaminer.objects.create(name=name, email=email, user=user)
    with transaction.atomic():
        user.save()
        examiner.save()
    return examiner.id


def setZdvId(user, zdvId):
    examiner = InternExaminer.objects.filter(user=user)
    if examiner.count() == 0:
        return False
    examiner = examiner[0]
    examiner.zdvId = zdvId
    examiner.save()


def getUserGroup(user):
    """
    Receives a django user object and return the User Group of the user.
    :param user: Django user object
    :return: String that tells which to which group the user belongs.
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
    :param user: Django user object
    :return: A boolean that tells if the user is a student and have made or not a request
    """
    student = Student.objects.filter(user=user)
    if student.exists() and student[0].deadline is not None:
        return True
    return False


def makeRequest(user, deadline, subject, supervisor1, supervisor2, topic, type, title, isSupervisor1Intern,
                isSupervisor2Intern):
    """
    Function initiates a students request.
    :param user: Django user object
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
    Receives a django user object or an student id and returns a
    dictionary with the informations about the request.
    :param user: Django user object
    :param id: Id of the student
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
    return result

def updateRequest(variable, value, studentEmail):
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
    student.save()


def createExternalExaminer(name, email, password):
    """
    Function creates a new External Examiner
    :param name: Name of the new examiner (String)
    :param email: E-Mail of the new examiner (String)
    :param password: Password of the new examiner (String)
    :return:
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
    :param user: Django user object
    :return:
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
    checkStatus(student)


def getExaminer(user, examinerId = None, intern=None):
    """Receives a Django user object that should correspond to an examiner.
    The function returns a tuple that stores the examiner id and the boolean that says,
    if the examiner is intern or not."""
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
    else:
        if intern:
            examiner = InternExaminer.objects.filter(id=examinerId)
        else:
            examiner = ExternalExaminer.objects.filter(id=examinerId)
        if examiner.count() > 0:
            return examiner[0]
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
    """The function returns the requests of the user group 'Examiner'.
    If a status is passed, all requests that have this status are returned.
    The other parameters can be used to receive more specific requests."""
    if status is not None:
        examinerId, intern = getExaminer(user)
        if supervisor == False:
            requests = Student.objects.filter(status=status)
        else:
            requests = Student.objects.filter(
                (Q(isSupervisor1Intern=intern, supervisor1=examinerId) |
                 Q(isSupervisor2Intern=intern, supervisor2=examinerId) |
                 Q(isSupervisor3Intern=intern, supervisor3=examinerId)), status=status
            )
        if accepted is not None:
            if supervisor != False:
                requests = requests.filter(
                    Q(isSupervisor1Intern=intern, supervisor1=examinerId, supervisor1Confirmed__isnull=not accepted) |
                    Q(isSupervisor2Intern=intern, supervisor2=examinerId, supervisor2Confirmed__isnull=not accepted)
                )
        if rated is not None:
            if supervisor != False:
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
    """This function get a student object and checks if the status must be changed.
    If so, the status will be adjusted."""
    if student.status == "Anfrage wird bestätigt":
        if student.officeConfirmed and student.supervisor1Confirmed and student.supervisor2Confirmed:
            student.status = "Schreibphase"
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
            student.grade1 = note
            student.save()
        elif student.supervisor2 == examinerId and student.isSupervisor2Intern == intern:
            student.grade2 = note
            student.save()
        elif student.supervisor3 == examinerId and student.isSupervisor3Intern == intern:
            student.grade3 = note
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


def getExaminers(approvalToTest=None, subject=None, topic=None, title=None, excludedTopic=None, excludedExaminers=None,
                 maxInvitation=None):
    """Returns all examiners that correpsond to the given specifications"""
    # todo if a user doesnt have a qualification it should not be included in topic excluded
    qualifications = Qualification.objects.all()
    if approvalToTest is not None:
        qualifications = qualifications.filter(approvalToTest=approvalToTest)
    if subject is not None:
        qualifications = qualifications.filter(subject=subject)
    if topic is not None:
        qualifications = qualifications.filter(topic=topic)
    if title is not None:
        qualifications = qualifications.filter(title=title)
    if excludedTopic is not None:
        qualifications = qualifications.exclude(topic=excludedTopic)
    externalExaminers = ExternalExaminer.objects.none()
    internExaminers = InternExaminer.objects.none()
    for elem in qualifications:
        if elem.isExaminerIntern == False:
            externalExaminers = externalExaminers | ExternalExaminer.objects.filter(id=elem.examiner)
        if elem.isExaminerIntern == True:
            internExaminers = internExaminers | InternExaminer.objects.filter(id=elem.examiner)
    if excludedExaminers is not None:
        externalExaminers = externalExaminers and ExternalExaminer.objects.exclude(
            user_id__in=[o.user_id for o in excludedExaminers])
        internExaminers = internExaminers and InternExaminer.objects.exclude(
            user_id__in=[o.user_id for o in excludedExaminers])
    if maxInvitation is not None:
        invitationsExternal = Invitation.objects.filter(numberInvitations__gt=maxInvitation, isExaminerIntern=0)
        invitationsIntern = Invitation.objects.filter(numberInvitations__gt=maxInvitation, isExaminerIntern=1)
        externalExaminers = externalExaminers.exclude(id__in=[o.examiner for o in invitationsExternal])
        internExaminers = internExaminers.exclude(id__in=[o.examiner for o in invitationsIntern])
    return externalExaminers, internExaminers


def setSupervisor3(studentId, examiner, isExaminerIntern):
    """Receives a studentId and the data of an examiner.
    The function sets this examiner as the third supervisor of the student"""
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
    """Returns all functions of the database."""
    qualifications = Qualification.objects.all()
    subjects = qualifications.values_list('subject').distinct()
    result = []
    for elem in subjects:
        result.append(elem[0])
    return result


def getTopics(subject):
    """Returns all topics that correspond to the givenn subject"""
    qualifications = Qualification.objects.filter(subject=subject)
    topics = qualifications.values_list('topic').distinct()
    result = []
    for elem in topics:
        result.append(elem[0])
    return result


def inviteExaminer(student, examiner, role):
    """Creates the invitation for one examiner for one request"""
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
    """Receives a Django User object
    Returns the corresponding Student Object"""
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
    :param user: Django user object of the examiner
    :param studentId: Student id
    :param accept: Boolean that tells if the examiner accept or reject the invitation
    :return:
    """
    examinerId, intern = getExaminer(user)
    invitation = Invitation.objects.filter(student_id=studentId, examiner=examinerId, isExaminerIntern=intern)[0]
    invitation.accepted = accept
    invitation.save()


def addAvailabilityToInvitation(user, studentId, timeSlotId):
    """
    Function stores in the database the availability for the invitation
    :param user: Django user object of the examiner
    :param studentId: Student id
    :param timeSlotId: Id of the timeSlot that should be set as availability
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
    :param user: Django user object of the examiner
    :param studentId: Id of the student/request
    :param timeSlotId: Id of the timeSlot
    :return:
    """
    examinerId, intern = getExaminer(user)
    invitation = Invitation.objects.filter(student_id=studentId, examiner=examinerId, isExaminerIntern=intern)[0]
    availability = AvailabilityInvitation.objects.filter(invitation=invitation, timeSlot_id=timeSlotId)
    availability.delete()


def getRecentAvailabilities(user, studentId, start, end):
    """

    :param user: Django user object of the examiner
    :param studentId: Id of the student/request
    :param start: First day of the week as a date
    :param end: Last day of the week as a date
    :return: The timeSlots, that were added recently and have not yet been moved to AvailabilityRequest
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
    :param user: Django user objectof the examiner
    :param studentId: Id of the student/request
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
            invitationAvailabilities.update(deleted=False)
            for elem in rows:
                elem.save()
    else:
        AvailabilityRequest.objects.filter(student_id=studentId)\
            .exclude(timeSlot__in=invitationAvailabilities.values('timeSlot')).delete()


def generateTimeSlots(year):
    """
    Writes all possible time slots for the given year into the database
    :param year: Year as an Integer
    :return: Boolean that says whether the function was successful
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
    :param year: Year as an Integer
    :return: Boolean that says whether the function was successful
    """
    TimeSlot.objects.filter(start__year=year).delete()
    return True


def getTimeSlots(studentId, start, end):
    """
    Searches the available time slots for an invitation from one day to another day and returns them.
    :param studentId: Id of the request/student
    :param start: First day of the week as a date
    :param end: Last day of the week as a date
    :return: QuerySet with all availabilities
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

    :param timeSlots: A Query Set of Time Slots
    :return: A dictionary that divides the time slots into days and times of the week.
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
    :param year: Year as an Integer
    :return: Number of days in the year
    """
    if (year % 4 == 0) and (year % 100 != 0) or (year % 400 == 0):
        return 366
    return 365


def getRequestConstellation(studentId, accepted=None):
    """

    :param studentId:
    :return:
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
    student = Student.objects.filter(email=email)
    if student.count() > 0:
        return student[0].id


def setAppointmentEmerged(studentId):
    """

    :param studentId:
    :return:
    """
    student = Student.objects.filter(id=studentId)[0]
    student.appointmentEmerged = True
    student.status = "Termin entstanden"
    student.save()


def getRole(examinerId, isExaminerIntern, studentId):
    """

    :param examinerId:
    :param isExaminerIntern:
    :param studentId:
    :return:
    """
    invitation = Invitation.objects.filter(examiner=examinerId, isExaminerIntern=isExaminerIntern,
                                           student_id=studentId)[0]
    return invitation.role


def getStudentUser(studentId):
    """

    :param studentId:
    :return:
    """
    student = Student.objects.filter(id=studentId)[0]
    return student.user


def isSupervisor(studentId, examinerId, intern):
    """

    :param studentId:
    :param examinerId:
    :param intern:
    :return:
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
        return False


def getRequestsAppointments(studentId):
    slotsId = AvailabilityRequest.objects.filter(student_id=studentId)
    if slotsId.count() > 0:
        slots = TimeSlot.objects.filter(id__in=[o.timeSlot_id for o in slotsId])
        return slots
    else:
        return False


def endRequest(studentId, slotId):
    student = Student.objects.filter(id=studentId)
    if student.count() > 0:
        student = student[0]
        timeSlot = TimeSlot.objects.filter(id=slotId)[0]
        student.officeConfirmedAppointment = True
        student.appointment = timeSlot.start
        student.save()


def restartScheduling(studentId, maxInvitation):
    """
    The function deletes all availabilities of invitations and requests and re invite all examiners.
    :param studentId: Id of the request/student
    :return: An array that contains all examiners that must be removed of the request
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
    invitation = Invitation.objects.filter(student_id=studentId, examiner=examinerId, isExaminerIntern=intern)
    if invitation[0].numberInvitations >= maxInvitation:
        return False
    if invitation.count() == 0:
        inviteExaminer(getStudent(None, studentId), getExaminer(None, examinerId, intern), role)
        return True
    invitation.update(accepted=None, numberInvitations=F('numberInvitations')+1, role=role)
    updateAvailabilities(studentId)
    return True


def updateAvailabilities(studentId):
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
    qualification = Qualification(title=title, subject=subject, topic=topic, approvalToTest=approval,
                                  examiner=examinerId, isExaminerIntern=isExaminerIntern)
    qualification.save()


def setExam(studentId, timeSlot, constellation):
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
    result = {}
    if isinstance(examiner, ExternalExaminer):
        intern = 0
    elif isinstance(examiner, InternExaminer):
        intern = 1
    result['topic'] = []
    result['isIntern'] = intern
    result['id'] = examiner.id
    qualification = Qualification.objects.filter(isExaminerIntern=intern, examiner=examiner.id)
    for elem in qualification:
        result['topic'].append(elem.topic)
    return result