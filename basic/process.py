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
                        not constellation['externalExaminer'] is None:
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
                        not constellation['externalExaminer'] is None:
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
    else:
        examinerId = examiner[0]
        intern = examiner[1]
        role = getRole(examinerId, intern, studentId)
        constellation = getRequestConstellation(studentId)
        studentData = getStudentRequest(getStudentUser(studentId))
        if isSupervisor(studentId, examinerId, intern):
            deleteExaminers = restartScheduling(studentId, 3)
            for elem in deleteExaminers:
                if isSupervisor(studentId, elem[0], elem[1]):
                    # send email to office
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
                    found = True
                    break
            if not found:
                # Not enough examiners can be found
                # send email to office
                return False
        elif len(newExaminers) == 1:
            if not reInviteExaminer(studentId, examinerId, intern, 3, role):
                # Not enough examiners can be found
                # todo send email to office
                return False
            found = False
            examiners = orderByAvailabilities(constellation)
            for elem in examiners:
                if isinstance(elem, ExternalExaminer):
                    intern2 = 0
                elif isinstance(elem, InternExaminer):
                    intern2 = 1
                if not isSupervisor(studentId, elem.id, intern2):
                    if not reInviteExaminer(studentId, elem.id, intern2, 3, role):
                        found = True
                        break
            if not found:
                # Not enough examiners can be found
                # send email to office
                return False


def orderByAvailabilities(constellation):
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
