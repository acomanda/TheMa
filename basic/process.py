from django.core.mail import send_mail
from django.conf import settings
from .databaseHandler import *
import itertools
import random

def createExaminerConstellation(user, designations):
    """
    At this moment this function allows only to designate a chairman.
    :param user: Django user object of the Student/Request
    :param designations: Dictionary that stores for the key 'chairman' an Examiner Object
    :return: Returns the generated constellation of examiners for the oral exam
    """
    studentData = getStudentRequest(user)
    if studentData['subject'] == 'Informatik':
        if studentData['type'] == 'dr.':
            # Check if chairman is a supervisor
            supervisors = [1, 2, 3]
            constellation = {
                'chairman': None,
                'examiner': None,
                'externalExaminer': None,
                'reporter1': None,
                'reporter2': None
            }
            for i in supervisors:
                for item in list(designations.values()):
                    if item == studentData['supervisor' + str(i)]:
                        if i in supervisors:
                            supervisors.remove(i)

            # Fill the constellation with the chairman and all supervisors
            constellation['chairman'] = designations['chairman']
            roles = ['examiner', 'reporter2', 'reporter1']
            if len(supervisors) > 0:
                if not studentData['topic'] in getExaminerInformations(studentData['supervisor'
                                                                               + str(supervisors[0])])['topic']:
                    constellation['externalExaminer'] = studentData['supervisor' + str(supervisors[0])]
                else:
                    for elem in roles:
                        if constellation[elem] is None:
                            constellation[elem] = studentData['supervisor' + str(supervisors[0])]
                            break
            if len(supervisors) > 1:
                if studentData['supervisor' + str(supervisors[1])] is not None \
                        and not studentData['topic'] in getExaminerInformations(
                        studentData['supervisor' + str(supervisors[1])])['topic'] and \
                        constellation['externalExaminer'] is None:
                    constellation['externalExaminer'] = studentData['supervisor' + str(supervisors[1])]
                else:
                    for elem in roles:
                        if constellation[elem] is None:
                            constellation[elem] = studentData['supervisor' + str(supervisors[1])]
                            break
            if len(supervisors) > 2:
                if studentData['supervisor' + str(supervisors[2])] is not None \
                        and not studentData['topic'] in getExaminerInformations(
                        studentData['supervisor' + str(supervisors[2])])['topic'] and \
                        constellation['externalExaminer'] is None:
                    constellation['externalExaminer'] = studentData['supervisor' + str(supervisors[2])]
                else:
                    for elem in roles:
                        if constellation[elem] is None:
                            constellation[elem] = studentData['supervisor' + str(supervisors[2])]
                            break
            # Fill the role of an external Examiner, if it is not yet set
            if constellation['externalExaminer'] is None:
                constellationValues = getConstellationValues(constellation)
                externalExaminers = list(itertools.chain(*getExaminers(None, None, None, None, studentData['topic'],
                                                                       constellationValues)))
                if len(externalExaminers) == 0:
                    # Not enough examiners can be found
                    return False
                constellation['externalExaminer'] = externalExaminers[0]

            # Fill the remaining roles
            constellationValues = getConstellationValues(constellation)
            examiners = list(itertools.chain(*getExaminers(None, studentData['subject'], studentData['topic'], None,
                                                           None, constellationValues, 3)))
            examiners.append(list(itertools.chain(*getExaminers(None, studentData['subject'], None, None,
                                                                studentData['topic'], constellationValues, 3))))
            for key in constellation:
                if constellation[key] is None:
                    if len(examiners) == 0:
                        # Not enough examiners can be found
                        return False
                    constellation[key] = examiners[0]
                    examiners = examiners[1:]
            inviteAllExaminers(getStudent(user), constellation)
            return constellation


def inviteAllExaminers(student, constellation):
    """
    Function invites all examiners of a constellation to the request.
    :param student: Student object
    :param constellation: Dictionary that contains the constellation of examiners for
    the oral exam
    :return:
    """
    for key in constellation:
        inviteExaminer(student, constellation[key], key)
        examinerSchedulingNotification(constellation[key], student)


def getConstellationValues(constellation):
    """

    :param constellation: Dictionary that contains the constellation of examiners for
    the oral exam
    :return: A None free list of all examiners of the constellation
    """
    constellationValues = list(constellation.values())
    if None in constellationValues:
        for i in range(constellationValues.count(None)):
            constellationValues.remove(None)
    return constellationValues

def invitationAnswered(studentId, examiner, answer):
    """
    The function is mainly divided into two parts.
    The first part is executed if answer is True otherwise part 2.
    The first part checks if an appointment is emerged and if it is, the status of the request
    is updated.
    The second part handles the rejections of examiners and invites new examiners.
    :param studentId: Id of the student/request
    :param examiner: A tuple of the form (examinerId, isExaminerInter): (Int, Bool)
    :param answer: Boolean that tells, if the examiner has accepted or not the request
    :return:
    """
    if answer:
        constellation = getRequestConstellation(studentId, True)
        if len(constellation) == 5:
            setAppointmentEmerged(studentId)
            officeWaitForConfirmation(getStudent(None, studentId), getOffice())
            for key in constellation:
                examinerAppointmentNotification(constellation[key], getStudent(None, studentId))
    else:
        examinerId = examiner[0]
        intern = examiner[1]
        role = getRole(examinerId, intern, studentId)
        constellation = getRequestConstellation(studentId)
        studentData = getStudentRequest(getStudentUser(studentId))
        if isSupervisorOrChairman(studentId, examinerId, intern):
            deleteExaminers = restartScheduling(studentId, 3)
            for elem in deleteExaminers:
                if isSupervisorOrChairman(studentId, elem[0], elem[1]):
                    # send email to office
                    officeNoExaminersNotification(getStudent(None, studentId), getOffice())
                    return False
                invitationAnswered(studentId, elem, 0)
            return
        if role == 'externalExaminer':
            newExaminers = list(itertools.chain(*getExaminers(None, studentData['subject'], None, None,
                                                              studentData['topic'],
                                                              getConstellationValues(constellation), 3)))
        else:
            newExaminers = list(itertools.chain(*getExaminers(None, studentData['subject'], studentData['topic'], None,
                                                              None,
                                                              getConstellationValues(constellation), 3)))
            newExaminers.append(list(itertools.chain(*getExaminers(None, studentData['subject'], None,
                                                                   None, studentData['topic'],
                                                                   getConstellationValues(constellation), 3))))
        examiners = list(constellation.values())
        random.shuffle(examiners)
        if len(newExaminers) == 0:
            # Not enough examiners can be found
            # send email to office
            officeNoExaminersNotification(getStudent(None, studentId), getOffice())
            return False
        elif len(newExaminers) > 1:
            newExaminers.remove(getExaminer(None, examinerId, intern))
            found = False
            for i in range(len(newExaminers)):
                if isinstance(newExaminers[i], ExternalExaminer):
                    intern2 = 0
                elif isinstance(newExaminers[i], InternExaminer):
                    intern2 = 1
                if reInviteExaminer(studentId, newExaminers[i].id, intern2, 3, role):
                    examinerSchedulingNotification(getExaminer(None, newExaminers[i].id, intern2),
                                                   getStudent(None, studentId))
                    found = True
                    break
            if not found:
                # Not enough examiners can be found
                # send email to office
                officeNoExaminersNotification(getStudent(None, studentId), getOffice())
                return False
        elif len(newExaminers) == 1:
            if not reInviteExaminer(studentId, examinerId, intern, 3, role):
                # Not enough examiners can be found
                # send email to office
                officeNoExaminersNotification(getStudent(None, studentId), getOffice())
                return False
            examinerSchedulingNotification(getExaminer(None, examinerId, intern),
                                           getStudent(None, studentId))
            found = False
            examiners = orderByAvailabilities(constellation)
            for elem in examiners:
                if isinstance(elem, ExternalExaminer):
                    intern2 = 0
                elif isinstance(elem, InternExaminer):
                    intern2 = 1
                if not isSupervisorOrChairman(studentId, elem.id, intern2):
                    if reInviteExaminer(studentId, elem.id, intern2, 3, role):
                        examinerDeletedInvitationNotification(getExaminer(None, elem.id, intern2),
                                                              getStudent(None, studentId))
                        examinerSchedulingNotification(getExaminer(None, elem.id, intern2),
                                                       getStudent(None, studentId))
                        found = True
                        break
            if not found:
                # Not enough examiners can be found
                # send email to office
                officeNoExaminersNotification(getStudent(None, studentId), getOffice())
                return False


def orderByAvailabilities(constellation):
    """
    This function orders the constellation by the amount of the chosen availabilities. From less
    to more.
    :param constellation: Dictionary that contains the constellation of examiners.
    :return: The sorted constellation as a dictionary
    """
    examiners = list(constellation.values())
    availabilities = {}
    for elem in examiners:
        if isinstance(elem, ExternalExaminer):
            intern = 0
        elif isinstance(elem, InternExaminer):
            intern = 1
        invitation = Invitation.objects.filter(isExaminerIntern=intern, examiner=elem.id)[0]
        availabilities[elem] = AvailabilityInvitation.objects.filter(invitation=invitation).count()
    a = sorted(availabilities.items(), key=lambda x: x[1])
    result = []
    for elem in a:
        result.append(elem[0])
    return result


systemEmail = 'placeholder@thema.de'


# Functions for sending E-Mails
# todo Implement the use of URL's to redirect the user to the right place by including some Id's in the URL
def examinerSupervisorNotification(examiner, student):
    subject = 'Betreueranfrage von ' + student.name
    to = examiner.email
    link = 'https://thema.uni-mainz.de/homeexaminer'
    message = 'Sehr geehrter Herr ' + examiner.name + ',\n' \
              + 'hiermit wird Ihnen mitgeteilt, dass der Student ' + student.name \
              + ' sie als Betreuer festgelegt hat.\n' \
              + 'Besuchen sie folgenden Link um die Anfrage einzusehen und zu beantowrten:\n' \
              + link
    return send_mail(subject, message, systemEmail, [to], fail_silently=True)


def examinerSchedulingNotification(examiner, student):
    subject = 'Verteidigungseinladung von ' + student.name
    to = examiner.user.email
    link = 'https://thema.uni-mainz.de/homeexaminer'
    message = 'Sehr geehrter Herr ' + examiner.name + ',\n' \
              + 'hiermit wird Ihnen mitgeteilt, dass Sie zur Verteidigung von ' + student.name \
              + ' eingeladen wurden.\n' \
              + 'Besuchen sie folgenden Link um die Einladung einzusehen und zu beantworten:\n' \
              + link
    return send_mail(subject, message, systemEmail, [to], fail_silently=True)


def examinerRatingNotification(examiner, student):
    subject = 'Gutachteneingabe von ' + student.name
    to = examiner.user.email
    link = 'https://thema.uni-mainz.de/homeexaminer'
    message = 'Sehr geehrter Herr ' + examiner.name + ',\n' \
              + 'hiermit wird Ihnen mitgeteilt, dass die Gutachteneingabefür die Thesis von ' + student.name \
              + ' freigegeben wurde.\n' \
              + 'Besuchen sie folgenden Link um die Arbeit zu benoten:\n' \
              + link
    return send_mail(subject, message, systemEmail, [to], fail_silently=True)


def examinerAppointmentNotification(examiner, student):
    subject = 'Verteidigunstermin von ' + student.name
    to = examiner.user.email
    link = 'https://thema.uni-mainz.de/homeexaminer'
    message = 'Sehr geehrter Herr ' + examiner.name + ',\n' \
              + 'hiermit wird Ihnen mitgeteilt, dass ein Termin für die Verteidigungvon ' + student.name \
              + ' gefunden wurde. Nun muss das Prüfungsamt dem noch zustimmen.\n' \
              + 'Besuchen sie folgenden Link um weitere Informationen einzusehen:\n' \
              + link
    return send_mail(subject, message, systemEmail, [to], fail_silently=True)


def examinerFinalAppointmentNotification(examiner, student):
    subject = 'Verteidigunstermin von ' + student.name
    to = examiner.user.email
    link = 'https://thema.uni-mainz.de/homeexaminer'
    message = 'Sehr geehrter Herr ' + examiner.name + ',\n' \
              + 'hiermit wird Ihnen mitgeteilt, dass der Termin für die Verteidigung von ' + student.name \
              + ' bestätigt wurde.\n' \
              + 'Besuchen sie folgenden Link um weitere Informationen einzusehen:\n' \
              + link
    return send_mail(subject, message, systemEmail, [to], fail_silently=True)

# Not used yet
def examinerDeletedInvitationNotification(examiner, student):
    subject = 'Verteidigungseinladung von ' + student.name + ' entfernt'
    to = examiner.user.email
    link = 'https://thema.uni-mainz.de/homeexaminer'
    message = 'Sehr geehrter Herr ' + examiner.name + ',\n' \
              + 'hiermit wird Ihnen mitgeteilt, dass die Einladung zur Verteidigung von ' + student.name \
              + ' entfernt wurde.\n' \
              + 'Besuchen sie folgenden Link um weitere Informationen einzusehen:\n' \
              + link
    return send_mail(subject, message, systemEmail, [to], fail_silently=True)


def studentStatusUpdateNotification(student):
    subject = 'Der Status ihrer Anfrage hat sich geändert'
    to = student.user.email
    link = 'https://thema.uni-mainz.de/homestudent'
    message = 'Sehr geehrter Herr ' + student.name + ',\n' \
              + 'hiermit wird Ihnen mitgeteilt, dass sich der Status ihrer Anfrage geändert hat.\n' \
              + 'Neuer Status: ' + student.status \
              + 'Besuchen sie folgenden Link um weitere Informationen einzusehen:\n' \
              + link
    return send_mail(subject, message, systemEmail, [to], fail_silently=True)


def officeRequestNotification(student, office):
    subject = 'Anfrage von ' + student.name
    to = office.user.email
    link = 'https://thema.uni-mainz.de/homeoffice'
    message = 'Sehr geehrtes Prüfungsamt' \
              + 'hiermit wird Ihnen mitgeteilt, dass der Student ' + student.name \
              + ' eine Anfrage eingesendet hat.\n' \
              + 'Besuchen sie folgenden Link um die Anfrage zu beantworten:\n' \
              + link
    return send_mail(subject, message, systemEmail, [to], fail_silently=True)


def officeWaitForRatingNotification(student, office):
    subject = 'Anfrage von ' + student.name
    to = office.user.email
    link = 'https://thema.uni-mainz.de/homeoffice'
    message = 'Sehr geehrtes Prüfungsamt' \
              + 'hiermit wird Ihnen mitgeteilt, dass die Anfrage von ' + student.name \
              + ' zur Gutachteneingabe freigegeben werden kann.\n' \
              + 'Besuchen sie folgenden Link um weitere Informationen einzusehen:\n' \
              + link
    return send_mail(subject, message, systemEmail, [to], fail_silently=True)


def officeWaitForSchedulingNotification(student, office):
    subject = 'Anfrage von ' + student.name
    to = office.user.email
    link = 'https://thema.uni-mainz.de/homeoffice'
    message = 'Sehr geehrtes Prüfungsamt' \
              + 'hiermit wird Ihnen mitgeteilt, dass die Anfrage von ' + student.name \
              + ' zur Terminfindung freigegeben werden kann.\n' \
              + 'Besuchen sie folgenden Link um weitere Informationen einzusehen:\n' \
              + link
    return send_mail(subject, message, systemEmail, [to], fail_silently=True)


def officeRequestRejectedNotification(student, office):
    subject = 'Anfrage von ' + student.name
    to = office.user.email
    link = 'https://thema.uni-mainz.de/management'
    message = 'Sehr geehrtes Prüfungsamt' \
              + 'hiermit wird Ihnen mitgeteilt, dass die Anfrage von ' + student.name \
              + ' seitens eines Betreuers abgelehnt wurde.\n' \
              + 'Besuchen sie folgenden Link um die Anfrage zu bearbeiten:\n' \
              + link
    return send_mail(subject, message, systemEmail, [to], fail_silently=True)


def officeWaitForConfirmation(student, office):
    subject = 'Anfrage von ' + student.name
    to = office.user.email
    link = 'https://thema.uni-mainz.de/management'
    message = 'Sehr geehrtes Prüfungsamt' \
              + 'hiermit wird Ihnen mitgeteilt, dass die Anfrage von ' + student.name \
              + ' nun mögliche Verteidigungstermine besitzt, aus denen eines gewählt werden muss.\n' \
              + 'Besuchen sie folgenden Link um dies zu tun:\n' \
              + link
    return send_mail(subject, message, systemEmail, [to], fail_silently=True)


def officeNoExaminersNotification(student, office):
    subject = 'Anfrage von ' + student.name
    to = office.user.email
    link = 'https://thema.uni-mainz.de/management'
    message = 'Sehr geehrtes Prüfungsamt' \
              + 'hiermit wird Ihnen mitgeteilt, dass die Anfrage von ' + student.name \
              + ' nicht zu einem Verteidigungstermin führen kann, da es nicht genügend Prüfer gibt.\n' \
              + 'Besuchen sie folgenden Link um die Verteidigung manuell einzutragen:\n' \
              + link
    return send_mail(subject, message, systemEmail, [to], fail_silently=True)