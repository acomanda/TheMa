from django.core.mail import send_mail
from django.conf import settings
from .databaseHandler import *
import itertools

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
            constellation['chairman'] = designations['chairman']
            if len(supervisors) > 0:
                constellation['examiner'] = studentData['supervisor' + str(supervisors[0])]
            if len(supervisors) > 1:
                constellation['reporter2'] = studentData['supervisor' + str(supervisors[1])]
            else:
                constellationValues = getConstellationValues(constellation)
                reporter2 = list(itertools.chain(*getExaminers(None, studentData['subject'], studentData['topic'], None,
                                                               None, constellationValues)))
                constellation['reporter2'] = reporter2[0]
            if len(supervisors) > 2:
                constellation['reporter1'] = studentData['supervisor' + str(supervisors[2])]
            else:
                constellationValues = getConstellationValues(constellation)
                reporter1 = list(itertools.chain(*getExaminers(None, studentData['subject'], studentData['topic'], None,
                                                               None, constellationValues)))
                constellation['reporter1'] = reporter1[0]
            constellationValues = getConstellationValues(constellation)
            externalExaminers = list(itertools.chain(*getExaminers(None, None, None, None, studentData['topic'],
                                                                   constellationValues)))
            if len(externalExaminers) == 0:
                # Not enough examiners can be found
                return False
            constellation['externalExaminer'] = externalExaminers[0]
            constellationValues = getConstellationValues(constellation)
            examiners = list(itertools.chain(*getExaminers(None, studentData['subject'], studentData['topic'], None,
                                                           None, constellationValues)))
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
        inviteExaminer(student, constellation[key], key, 1)


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
