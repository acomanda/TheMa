from django.shortcuts import render, HttpResponse, redirect
from .authorization import *
from .databaseHandler import *
from django.contrib.auth import authenticate, login, logout as django_logout
from .forms import *
from .process import *

stateLength = 30


def index(request):
    """This function controls the behavior of the start page."""
    # If user is already authenticated redirect him to the right home page
    if request.user.is_authenticated:
        if getUserGroup(request.user) == "Office":
            return redirect('/homeoffice')
        elif getUserGroup(request.user) == "Examiner":
            return redirect('/homeexaminer')
        elif getUserGroup(request.user) == "Student":
            return redirect('/homestudent')
    # This part handles the response of the ZDV user
    if request.method == 'GET' and 'state' in request.GET:
        if request.session['state'] == request.GET['state']:
            claims = getClaims(request.GET['code'])
            user = getUser(claims['email'], claims['sub'], request.GET['state'], stateLength, claims['name'])
            if not user:
                return render(request, 'index.html', {'error2': "Bitte melden Sie sich beim Prüfungsamt <br> "})
            user.backend = 'basic.auth_backend.PasswordlessAuthBackend'
            authenticate(username=claims['email'])
            login(request, user)
            group = getUserGroup(user)
            if group == "Examiner":
                return redirect('/homeexaminer')
            if group == "Student":
                return redirect('/homestudent')
    # This part handles the login of a student user
    if request.POST.get('loginAs') == "student":
        url, state = getAuthorizationURL("student", stateLength)
        request.session['state'] = state
        request.POST
        return redirect(url)
    # This part handles the login of an intern examiner
    if request.POST.get('loginAs') == "pruefer":
        url, state = getAuthorizationURL("pruefer", stateLength)
        request.session['state'] = state
        return redirect(url)
    # This part handles the login of an external examiner or Office Account
    if request.POST.get('loginAs') == "extern":
        user = authenticate(username=request.POST['email'], password=request.POST['password'])
        if user is not None:
            login(request, user)
            if getUserGroup(user) == "Office":
                return redirect('/homeoffice')
            elif getUserGroup(user) == "Examiner":
                return redirect('/homeexaminer')
        else:
            return render(request, 'index.html', {'error': "Falsche Anmeldedaten <br> "})
    return render(request, 'index.html')


def homeOffice(request):
    """This function controls the behavior of the home page of the user group 'Office'"""
    if request.user.is_authenticated:
        context = {}
        group = getUserGroup(request.user)
        context['group'] = group
        if request.POST.get('details'):
            request.session['requestId'] = request.POST.get('details')
            return redirect('/confirmrequest')
        if request.POST.get('rating'):
            student = getStudent(None, request.POST.get('rating'))
            examinerRatingNotification(getExaminer(None, student.supervisor1, student.isSupervisor1Intern), student)
            examinerRatingNotification(getExaminer(None, student.supervisor2, student.isSupervisor2Intern), student)
            changeStatus(request.POST.get('rating'), "Gutachteneingabe")
        if request.POST.get('scheduling'):
            request.session['requestId'] = request.POST.get('scheduling')
            return redirect('/chairman')
        if request.POST.get('supervisor3'):
            request.session['requestId'] = request.POST.get('supervisor3')
            return redirect('/supervisor3')
        if request.POST.get('appointment'):
            request.session['requestId'] = request.POST.get('appointment')
            return redirect('/confirmAppointment')
        # Container 1
        container1Request = getRequestsOfOffice("Anfrage wird bestätigt", False)
        container1 = ""
        for elem in container1Request:
            container1 += '<p class="alignleft">' + elem.name + ' </p> \n'
            if isRequestRejected(elem):
                container1 += '<p class="alignright">Abgelehnt</p><br/><br/>'
            else:
                container1 += '<p class="alignright"><button type="submit" name="details" value="' + str(elem.id) \
                              + '">Details</button></p><br/><br/>'
        container1Request = getRequestsOfOffice("Anfrage wird bestätigt", True)
        for elem in container1Request:
            container1 += '<p class="alignleft">' + elem.name + ' </p> \n'
            if isRequestRejected(elem):
                container1 += '<p class="alignright">Abgelehnt</p><br/><br/>'
            else:
                container1 += '<p class="alignright">Bestätigt</p><br/><br/>'
        container1Request = getRequestsOfOffice("Schreibphase", None, True)
        for elem in container1Request:
            container1 += '<p class="alignleft">' + elem.name + ' </p> \n'
            container1 += '<p class="alignright"><button type="submit" name="rating" value="' + str(elem.id) \
                          + '" onclick="return confirm(\'Sind sie sicher?\');">Gutachteneingabe frei geben</button></p><br/><br/>'
        container1Request = getRequestsOfOffice("Schreibphase").exclude(id__in=container1Request.values('id'))
        for elem in container1Request:
            container1 += '<p class="alignleft">' + elem.name + ' </p> \n'
            container1 += '<p class="alignright">In Schreibphase</p><br/><br/>'
        context['container1'] = container1

        # Container 2
        container2 = ""
        container2Request1 = getRequestsOfOffice("Gutachteneingabe", None, None, None, True)
        for elem in container2Request1:
            container2 += '<p class="alignleft">' + elem.name + ' </p> \n'
            container2 += '<p class="alignright"><button type="submit" name="supervisor3" value="' + str(elem.id) \
                          + '">Drittgutachter wählen</button></p><br/><br/>'
        container2Request2 = getRequestsOfOffice("Gutachteneingabe", None, None, True, None)
        for elem in container2Request2:
            container2 += '<p class="alignleft">' + elem.name + ' </p> \n'
            container2 += '<p class="alignright"><button type="submit" name="scheduling" value="' + str(elem.id) \
                          + '" onclick="return confirm(\'Sind sie sicher?\');">Terminfindung starten</button></p><br/><br/>'
        container2Request = getRequestsOfOffice("Gutachteneingabe").exclude(Q(id__in=container2Request1.values('id')) |
                                                                            Q(id__in=container2Request2.values('id')))
        for elem in container2Request:
            container2 += '<p class="alignleft">' + elem.name + ' </p> \n'
            container2 += '<p class="alignright">Wartet auf Noten</p><br/><br/>'
        context['container2'] = container2

        # Container 3
        container3Request = getRequestsOfOffice("Terminfindung", None, None, None, None, False)
        container3 = ""
        for elem in container3Request:
            container3 += '<p class="alignleft">' + elem.name + ' </p> \n'
            container3 += '<p class="alignright">In Terminfindung</p><br/><br/>'
        context['container3'] = container3

        # Container 4
        container4 = ''
        container4Request = getRequestsOfOffice("Termin entstanden", None, None, None, None, None, False)
        for elem in container4Request:
            container4 += '<p class="alignleft">' + elem.name + ' </p> \n'
            container4 += '<p class="alignright"><button type="submit" name="appointment" value="' + str(elem.id) \
                          + '">Details</button></p><br/><br/>'
        context['container4'] = container4

        # Container 5
        container5Request = getRequestsOfOffice("Termin entstanden", None, None, None, None, None, True)
        container5 = ""
        for elem in container5Request:
            container5 += '<p class="alignleft">' + elem.name + ' </p> \n'
            container5 += '<p class="alignright">' + str(elem.appointment)[:16] + '</p><br/><br/>'
        context['container5'] = container5

        return render(request, 'homePruefungsamt.html', context)
    else:
        return redirect('/')


def homeStudent(request):
    """This function controls the behavior of the home page of the user group 'Student'"""
    if request.user.is_authenticated:
        if getUserGroup(request.user) == "Student" and not haveRequest(request.user):
            return redirect('/anfrage')
        context = {}
        group = getUserGroup(request.user)
        context['group'] = group
        content = getStudentRequest(request.user)
        context['title'] = content['title']
        context['supervisor1'] = content['supervisor1'].name
        context['supervisor2'] = content['supervisor2'].name
        context['deadline'] = content['deadline']
        context['topic'] = content['topic']
        context['type'] = content['type']
        context['status'] = content['status']
        context['subject'] = content['subject']
        if content['grade1'] is None:
            context['grade1'] = "/"
        else:
            context['grade1'] = content['grade1']
        if content['grade2'] is None:
            context['grade2'] = "/"
        else:
            context['grade2'] = content['grade2']
        if content['supervisor3']:
            context['supervisor3'] = 'Betreuer 3:<br><br>'
            context['supervisor3r'] = content['supervisor3'].name + '<br><br>'
        if content['grade3']:
            context['grade3'] = 'Note Betreuer 3:<br><br>'
            context['grade3r'] = str(content['grade3']) + '<br><br>'
        if content['appointment']:
            context['appointment'] = 'Verteidigung:<br><br>'
            context['appointmentr'] = content['appointment']
        constellation = getRequestConstellation(getStudent(request.user))
        if len(constellation) == 5:
            context['scheduling'] = True
            context['chairman'] = constellation['chairman'].name + '<br><br>'
            context['examiner'] = constellation['examiner'].name + '<br><br>'
            context['externalExaminer'] = constellation['externalExaminer'].name + '<br><br>'
            context['reporter1'] = constellation['reporter1'].name + '<br><br>'
            context['reporter2'] = constellation['reporter2'].name + '<br><br>'

        return render(request, 'requestDetails.html', context)
    else:
        return redirect('/')


def homeExaminer(request):
    """This function controls the behavior of the home page of the user group 'Examiner'"""
    if request.user.is_authenticated:
        if getUserGroup(request.user) == "Student" and not haveRequest(request.user):
            return redirect('/anfrage')
        context = {}
        group = getUserGroup(request.user)
        context['group'] = group
        if request.POST.get('details'):
            request.session['requestId'] = request.POST.get('details')
            return redirect('/confirmrequest')
        if request.POST.get('rate'):
            request.session['requestId'] = request.POST.get('rate')
            return redirect('/grading')
        if request.POST.get('answer'):
            request.session['requestId'] = request.POST.get('answer')
            request.session['amountSlots'] = 0
            return redirect('/answerInvitation')
        #Container 1
        container1 = ""
        container1Request = getRequestsOfExaminer(request.user, "Anfrage wird bestätigt", False, None, None, None, True)
        for elem in container1Request:
            container1 += '<p class="alignleft">' + elem.name + ' </p>'
            if isRequestRejected(elem):
                container1 += '<p class="alignright">Abgelehnt</p><br/><br/>'
            else:
                container1 += '<p class="alignright"><button type="submit" name="details" value="' + str(elem.id) \
                              + '">Details</button></p><br/><br/>'
        container1Request = getRequestsOfExaminer(request.user, "Schreibphase", True, None, None, None, True)
        for elem in container1Request:
            container1 += '<p class="alignleft">' + elem.name + ' </p>'
            container1 += '<p class="alignright">In Schreibphase</p><br/><br/>'
        container1Request = getRequestsOfExaminer(request.user, "Anfrage wird bestätigt", True, None, None, None, True)
        for elem in container1Request:
            container1 += '<p class="alignleft">' + elem.name + ' </p>'
            if isRequestRejected(elem):
                container1 += '<p class="alignright">Abgelehnt</p><br/><br/>'
            else:
                container1 += '<p class="alignright">Anfrage wird bestätigt</p><br/><br/>'
        context['container1'] = container1

        #Container 2
        container2 = ""
        container2Request = getRequestsOfExaminer(request.user, "Gutachteneingabe", None, False, None, None, True)
        for elem in container2Request:
            container2 += '<p class="alignleft">' + elem.name + ' </p>'
            container2 += '<p class="alignright"><button type="submit" name="rate" value="' + str(elem.id) \
                          + '">Bewerten</button></p><br/><br/>'
        container2Request = getRequestsOfExaminer(request.user, "Gutachteneingabe", None, True, None, None, True)
        for elem in container2Request:
            container2 += '<p class="alignleft">' + elem.name + ' </p>'
            container2 += '<p class="alignright">Bewertet</p><br/><br/>'
        context['container2'] = container2

        #Container 3
        container3 = ""
        container3Request = getRequestsOfExaminer(request.user, "Terminfindung", None, None, False)
        container3Request = container3Request | getRequestsOfExaminer(request.user, "Terminfindung", None,
                                                                      None, False, None, False)
        for elem in container3Request:
            container3 += '<p class="alignleft">' + elem.name + ' </p>'
            container3 += '<p class="alignright"><button type="submit" name="answer" value="' + str(elem.id) \
                          + '">Antworten</button></p><br/><br/>'
        context['container3'] = container3

        #Container 4
        container4 = ""
        container4Request = getRequestsOfExaminer(request.user, "Terminfindung", None, None, True)
        container4Request = container4Request | getRequestsOfExaminer(request.user, "Terminfindung", None,
                                                                      None, True, None, False)
        for elem in container4Request:
            container4 += '<p class="alignleft">' + elem.name + ' </p>'
            if noPossibleConstellation(elem):
                container4 += '<p class="alignright">Keine Konstellation möglich</p><br/><br/>'
            else:
                container4 += '<p class="alignright">Beantwortet</p><br/><br/>'
        context['container4'] = container4

        # Container 5
        container5 = ""
        examiner = getExaminer(request.user)
        container5Request = getRequestsOfExaminer(request.user, "Termin entstanden", None, None, None, True, False)
        for elem in container5Request:
            container5 += '<p class="alignleft">' + elem.name + ' </p>'
            container5 += '<p class="alignright">' + str(elem.appointment)[:16] + '</p><br/><br/>'
        container5Request = getRequestsOfExaminer(request.user, "Termin entstanden", None, None, None, False, False)
        for elem in container5Request:
            container5 += '<p class="alignleft">' + elem.name + ' </p> \n'
            container5 += '<p class="alignright">Prüfungsamt muss bestätigen</p><br/><br/>'
        context['container5'] = container5
        return render(request, 'homePruefer.html', context)
    else:
        return redirect('/')


def confirmRequest(request):
    context = {}
    group = getUserGroup(request.user)
    context['group'] = group
    content = getStudentRequest(None, request.session['requestId'])
    context['title'] = content['title']
    context['supervisor1'] = content['supervisor1'].name
    context['supervisor2'] = content['supervisor2'].name
    context['deadline'] = content['deadline']
    context['topic'] = content['topic']
    context['type'] = content['type']
    context['status'] = content['status']
    context['subject'] = content['subject']
    if request.POST.get('answerRequest'):
        if request.POST.get('answerRequest') == "accept":
            if group == "Examiner":
                # notify the users
                student = getStudent(None, request.session['requestId'])
                if confirmOrNotRequest(request.session['requestId'], True, "Examiner", request.user):
                    studentStatusUpdateNotification(student)
                if student.supervisor1Confirmed and student.supervisor2Confirmed and student.officeConfirmed:
                    officeWaitForRatingNotification(student, getOffice())

                return redirect('/')
            else:
                # notify the users
                student = getStudent(None, request.session['requestId'])
                if confirmOrNotRequest(request.session['requestId'], True, "Office", request.user):
                    studentStatusUpdateNotification(student)
                if student.supervisor1Confirmed and student.supervisor2Confirmed and student.officeConfirmed:
                    officeWaitForRatingNotification(student, getOffice())

                return redirect('/')
        elif request.POST.get('answerRequest') == "reject":
            if group == "Examiner":
                confirmOrNotRequest(request.session['requestId'], False, "Examiner", request.user)
                officeRequestRejectedNotification(getStudent(None, request.session['requestId']), getOffice())
                return redirect('/')
            else:
                confirmOrNotRequest(request.session['requestId'], False, "Office", request.user)
                officeRequestRejectedNotification(getStudent(None, request.session['requestId']), getOffice())
                return redirect('/')
    return render(request, 'requestDetails.html', context)


def anfrage(request):
    """This function controls the behavior of the page that is used to make a new request."""
    if request.user.is_authenticated:
        context = {}
        context['error'] = ''
        group = getUserGroup(request.user)
        context['group'] = group
        if request.POST.get('anfrage') == "anfrage":
            form = Anfrage(request.POST)
            if request.POST.get('abgabetermin') and request.POST.get('fach') and request.POST.get('betreuer1')\
                and request.POST.get('betreuer2') and request.POST.get('themengebiet') and request.POST.get('art')\
                and request.POST.get('titel'):
                abgabetermin = request.POST.get('abgabetermin')
                fach = request.POST.get('fach')
                betreuer1 = request.POST.get('betreuer1')[1:]
                betreuer1Intern = request.POST.get('betreuer1')[0] == "1"
                betreuer2 = request.POST.get('betreuer2')[1:]
                betreuer2Intern = request.POST.get('betreuer2')[0] == "1"
                themengebiet = request.POST.get('themengebiet')
                art = request.POST.get('art')
                titel = request.POST.get('titel')
                makeRequest(request.user, abgabetermin, fach, betreuer1, betreuer2, themengebiet, art, titel,
                            betreuer1Intern, betreuer2Intern)
                #notify the users
                examinerSupervisorNotification(getExaminer(None, betreuer1, betreuer1Intern), getStudent(request.user))
                examinerSupervisorNotification(getExaminer(None, betreuer2, betreuer2Intern), getStudent(request.user))
                officeRequestNotification(getStudent(request.user), getOffice())

                return redirect('/')
            elif request.POST.get('betreuer2') and request.POST.get('betreuer1') \
                    and request.POST.get('betreuer2') == request.POST.get('betreuer1'):
                context['errorSupervisor'] = '<ul class="errorlist"><li>Betreuer<ul class="errorlist">' \
                                             '<li>Wähle verschiedene Betreuer aus.</li></ul></li></ul>'
            if not form.is_valid():
                context['error'] = form.errors
        if getUserGroup(request.user) == "Student" and not haveRequest(request.user):
            # Fill supervisor selections with data of database
            supervisors = getExaminers()
            supervisorSelections = ''
            for elem in supervisors[1]:
                supervisorSelections += '<option value="1' + str(elem.id) + '">' + elem.name + '</option>'
            for elem in supervisors[0]:
                supervisorSelections += '<option value="0' + str(elem.id) + '">' + elem.name + '</option>'
            context['supervisors'] = supervisorSelections
            # Fill subjects selection with data of database
            subjectsList = getSubjects()
            subjects = ''
            for elem in subjectsList:
                subjects = '<option value="' + elem + '">' + elem + '</option>'
            context['subjects'] = subjects
            # Fill topics selection with data of database
            topicsList = getTopics('Informatik')
            topics = ''
            for elem in topicsList:
                topics += '<option value="' + elem + '">' + elem + '</option>'
            context['topics'] = topics
            return render(request, 'anfrage.html', context)
        return redirect('/')
    else:
        return redirect('/')


def logout(request):
    """This function is used to logout a user."""
    django_logout(request)
    return redirect('/')


def grading(request):
    """This function controls the behavior of the page that is used to give a grade for a request."""
    context = {}
    group = getUserGroup(request.user)
    context['group'] = group
    if request.POST.get('confirmation'):
        if gradeRequest(request.user, request.session['requestId'], float(request.POST.get('grade'))):
            officeWaitForSchedulingNotification(getStudent(None, request.session['requestId']), getOffice())
        return redirect('/')
    content = getStudentRequest(None, request.session['requestId'])
    context['title'] = content['title']
    context['supervisor1'] = content['supervisor1'].name
    context['supervisor2'] = content['supervisor2'].name
    context['deadline'] = content['deadline']
    context['topic'] = content['topic']
    context['type'] = content['type']
    context['status'] = content['status']
    context['subject'] = content['subject']
    return render(request, 'requestDetails.html', context)


def supervisor3(request):
    """This function controls the behavior of the page that is used to choose a third supervisor."""
    context = {}
    group = getUserGroup(request.user)
    context['group'] = group
    if request.POST.get('confirmation') and request.POST.get('supervisor3'):
        if not setSupervisor3(request.session['requestId'], request.POST.get('supervisor3')[1:],
                              request.POST.get('supervisor3')[0]):
            context['error'] = 'Wähle einen Drittprüfer, der nicht bereits ein Prüfer ist.'
        else:
            examinerSupervisorNotification(getExaminer(None, int(request.POST.get('supervisor3')[1:]),
                                                       int(request.POST.get('supervisor3')[0])),
                                           getStudent(None, request.session['requestId']))

            return redirect('/')
    content = getStudentRequest(None, request.session['requestId'])
    context['title'] = content['title']
    context['supervisor1'] = content['supervisor1'].name
    context['supervisor2'] = content['supervisor2'].name
    context['deadline'] = content['deadline']
    context['topic'] = content['topic']
    context['type'] = content['type']
    context['status'] = content['status']
    context['subject'] = content['subject']
    supervisors = ''
    externalExaminers, internExaminers = getExaminers(True, None, None, None, None, [content['supervisor1'],
                                                                                     content['supervisor2']])
    for elem in externalExaminers:
        supervisors += '<option value="0' + str(elem.id) + '">' + elem.name + '</option>'
    for elem in internExaminers:
        supervisors += '<option value="1' + str(elem.id) + '">' + elem.name + '</option>'
    context['supervisors'] = supervisors
    return render(request, 'requestDetails.html', context)


def chairman(request):
    """This function controls the behavior of the page that is used to choose the chairman for the oral exam."""
    context = {}
    group = getUserGroup(request.user)
    context['group'] = group
    student = getStudent(None, request.session['requestId'])
    if not getRequestsOfOffice("Gutachteneingabe", None, None, True, None).filter(id=student.id).count() > 0:
        return redirect('/')
    if request.POST.get('confirmation'):
        if len(request.POST['chairman']) > 1:
            examiner = getExaminer(None, int(request.POST['chairman'][1:]), int(request.POST['chairman'][0]))
            if not createExaminerConstellation(Student.objects.filter(id=request.session['requestId'])[0].user,
                                               {'chairman': examiner}):

                context['error'] = 'Leider gibt es nicht genug Prüfer um eine Konstellation zu generieren.'
            else:
                changeStatus(request.session['requestId'], "Terminfindung")
            return redirect('/')
    content = getStudentRequest(None, request.session['requestId'])
    context['title'] = content['title']
    context['supervisor1'] = content['supervisor1'].name
    context['supervisor2'] = content['supervisor2'].name
    context['deadline'] = content['deadline']
    context['topic'] = content['topic']
    context['type'] = content['type']
    context['status'] = content['status']
    context['subject'] = content['subject']
    if content['supervisor3']:
        context['supervisor3'] = 'Betreuer 3:<br><br>'
        context['supervisor3r'] = content['supervisor3'].name + '<br><br>'
    if content['grade3']:
        context['grade3'] = 'Note Betreuer 3:<br><br>'
        context['grade3r'] = str(content['grade3']) + '<br><br>'
    supervisors = ''
    externalExaminers, internExaminers = getExaminers(True)
    for elem in externalExaminers:
        supervisors += '<option value="0' + str(elem.id) + '">' + elem.name + '</option>'
    for elem in internExaminers:
        supervisors += '<option value="1' + str(elem.id) + '">' + elem.name + '</option>'
    context['supervisors'] = supervisors
    return render(request, 'requestDetails.html', context)


def answerInvitation(request):
    """This function controls the behavior of the page that is used to answer an invitation."""
    if request.user.is_authenticated:
        context = {}
        amountSlots = getRecentAvailabilities(request.user, request.session['requestId'], None, None).count()
        if request.POST.get('exit'):
            if request.POST.get('exit') == 'accept':
                if amountSlots > 0:
                    moveAvailabilitiesToRequest(request.user, request.session['requestId'])
                    acceptOrNotInvitation(request.user, request.session['requestId'], True)
                    invitationAnswered(request.session['requestId'], getExaminer(request.user), True)

                    return redirect('/')
                else:
                    context['error'] = 'Wähle erst Zeitslots aus, bevor du die Anfrage akzeptierst.'
            if request.POST.get('exit') == 'reject':
                if amountSlots == 0:
                    acceptOrNotInvitation(request.user, request.session['requestId'], False)
                    invitationAnswered(request.session['requestId'], getExaminer(request.user), False)
                    return redirect('/')
                else:
                    context['error'] = 'Entferne erst alle Zeitslots, bevor du die Anfrage ablehnst.'
        if request.POST.get('delete'):
            deleteAvailabilityOfInvitation(request.user, request.session['requestId'], request.POST.get('delete'))
        if not request.POST.get('weekNavigation'):
            if 'stay' in request.session:
                startDate = datetime.strptime(request.session['startDate'], "%m/%d/%Y")
                endDate = datetime.strptime(request.session['endDate'], "%m/%d/%Y")
                del request.session['stay']
            else:
                now = datetime.today().date()
                weekday = now.weekday()
                startDate = now + timedelta(days=7 - weekday)
                endDate = startDate + timedelta(days=4)
        else:
            if request.POST.get('weekNavigation') == "forth":
                sign = 1
            else:
                sign = -1
            startDate = datetime.strptime(request.session['startDate'], "%m/%d/%Y") + sign * timedelta(days=7)
            endDate = datetime.strptime(request.session['endDate'], "%m/%d/%Y") + sign * timedelta(days=7)
        week = startDate.isocalendar()[1]
        request.session['startDate'] = startDate.strftime("%m/%d/%Y")
        request.session['endDate'] = endDate.strftime("%m/%d/%Y")
        request.session['week'] = week
        context['week'] = week
        context['startDate'] = startDate.strftime("%d.%m")
        context['tuesday'] = (startDate + timedelta(days=1)).strftime("%d.%m")
        context['wednesday'] = (startDate + timedelta(days=2)).strftime("%d.%m")
        context['thursday'] = (startDate + timedelta(days=3)).strftime("%d.%m")
        context['endDate'] = endDate.strftime("%d.%m")
        group = getUserGroup(request.user)
        context['group'] = group
        constellation = getRequestConstellation(getStudent(None, request.session['requestId']))
        if len(constellation) == 5:
            context['chairman'] = constellation['chairman'].name + '<br><br>'
            context['examiner'] = constellation['examiner'].name + '<br><br>'
            context['externalExaminer'] = constellation['externalExaminer'].name + '<br><br>'
            context['reporter1'] = constellation['reporter1'].name + '<br><br>'
            context['reporter2'] = constellation['reporter2'].name + '<br><br>'


        timeSlots = getTimeSlots(request.session['requestId'], startDate.strftime("%m/%d/%Y"),
                                 endDate.strftime("%m/%d/%Y"))
        timeSlots = getWeekSlots(timeSlots, startDate.strftime("%m/%d/%Y"))
        chosenTimeSlots = getRecentAvailabilities(request.user, request.session['requestId'], startDate.strftime("%m/%d/%Y"),
                                 endDate.strftime("%m/%d/%Y"))
        chosenTimeSlots = getWeekSlots(chosenTimeSlots, startDate.strftime("%m/%d/%Y"))
        if request.POST.get('choose'):
            if request.POST.get('choose') == 'week':
                for i in range(1, 6):
                    for j in range(8, 17, 2):
                        if chosenTimeSlots[str(i)][str(j)] is not None:
                            pass
                        elif timeSlots[str(i)][str(j)] is not None:
                            addAvailabilityToInvitation(request.user, request.session['requestId'],
                                                        timeSlots[str(i)][str(j)].id)
                            request.session['stay'] = True
            elif request.POST.get('choose')[:3] == 'day':
                for j in range(8, 17, 2):
                    if chosenTimeSlots[request.POST.get('choose')[3]][str(j)] is not None:
                        pass
                    elif timeSlots[request.POST.get('choose')[3]][str(j)] is not None:
                        addAvailabilityToInvitation(request.user, request.session['requestId'],
                                                    timeSlots[request.POST.get('choose')[3]][str(j)].id)
                        request.session['stay'] = True
            else:
                addAvailabilityToInvitation(request.user, request.session['requestId'], request.POST.get('choose'))
                request.session['stay'] = True
            timeSlots = getTimeSlots(request.session['requestId'], startDate.strftime("%m/%d/%Y"),
                                     endDate.strftime("%m/%d/%Y"))
            timeSlots = getWeekSlots(timeSlots, startDate.strftime("%m/%d/%Y"))
            chosenTimeSlots = getRecentAvailabilities(request.user, request.session['requestId'],
                                                      startDate.strftime("%m/%d/%Y"),
                                                      endDate.strftime("%m/%d/%Y"))
            chosenTimeSlots = getWeekSlots(chosenTimeSlots, startDate.strftime("%m/%d/%Y"))
        for i in range(1, 6):
            for j in range(8, 17, 2):
                if chosenTimeSlots[str(i)][str(j)] is not None:
                    context['slot' + str(i) + str(j)] = '<button type="submit" name="delete" value="' \
                                                        + str(timeSlots[str(i)][str(j)].id) + '">Entfernen</button>'
                elif timeSlots[str(i)][str(j)] is not None:
                    context['slot' + str(i) + str(j)] = '<button type="submit" name="choose" value="' \
                                                        + str(timeSlots[str(i)][str(j)].id) + '">Wählen</button>'
                else:
                    context['slot' + str(i) + str(j)] = 'Nicht verfügbar'
        # Pass request information
        content = getStudentRequest(None, request.session['requestId'])
        context['student'] = content['student']
        context['title'] = content['title']
        context['supervisor1'] = content['supervisor1'].name
        context['supervisor2'] = content['supervisor2'].name
        context['deadline'] = content['deadline']
        context['topic'] = content['topic']
        context['type'] = content['type']
        context['status'] = content['status']
        context['subject'] = content['subject']
        examinerId, intern = getExaminer(request.user)
        if isSupervisorOrChairman(request.session['requestId'], examinerId, intern):
            context['confirmationText'] = 'Wollen Sie als Supervisor wirklich ablehnen? Dies würde verursachen, dass ' \
                                          'alle Prüfer erneut eingeladen werden. Sie inklusive.'
        else:
            context['confirmationText'] = 'Wollen Sie wirklich ablehnen?'
        context['role'] = getRole(examinerId, intern, request.session['requestId'])
        if content['grade1'] is None:
            context['grade1'] = "/"
        else:
            context['grade1'] = content['grade1']
        if content['grade2'] is None:
            context['grade2'] = "/"
        else:
            context['grade2'] = content['grade2']
        if content['supervisor3']:
            context['supervisor3'] = 'Betreuer 3:<br><br>'
            context['supervisor3r'] = content['supervisor3'].name + '<br><br>'
        if content['grade3']:
            context['grade3'] = 'Note Betreuer 3:<br><br>'
            context['grade3r'] = str(content['grade3']) + '<br><br>'
        return render(request, 'answerInvitation.html', context)
    else:
        return redirect('/')


def confirmAppointment(request):
    """This function controls the behavior of the page that is used to choose a final time slot for the appointment."""
    if request.user.is_authenticated:
        context = {}
        context['group'] = getUserGroup(request.user)
        if request.POST.get('confirmation') and request.POST.get('slot'):
            endRequest(request.session['requestId'], request.POST['slot'])
            constellation = getRequestConstellation(request.session['requestId'], True)
            student = getStudent(None, request.session['requestId'])
            for key in constellation:
                examinerFinalAppointmentNotification(constellation[key], student)
            return redirect('/')
        appointments = getRequestsAppointments(request.session['requestId'])
        options = ''
        for elem in appointments:
            options += '<option value="' + str(elem.id) + '">' + elem.start.strftime("%m/%d/%Y %H/%M") + '</option>'
        context['appointments'] = options

        content = getStudentRequest(None, request.session['requestId'])
        context['student'] = content['student']
        context['title'] = content['title']
        context['supervisor1'] = content['supervisor1'].name
        context['supervisor2'] = content['supervisor2'].name
        context['deadline'] = content['deadline']
        context['topic'] = content['topic']
        context['type'] = content['type']
        context['status'] = content['status']
        context['subject'] = content['subject']
        constellation = getRequestConstellation(getStudent(None, request.session['requestId']))
        if len(constellation) == 5:
            context['chairman'] = constellation['chairman'].name + '<br><br>'
            context['examiner'] = constellation['examiner'].name + '<br><br>'
            context['externalExaminer'] = constellation['externalExaminer'].name + '<br><br>'
            context['reporter1'] = constellation['reporter1'].name + '<br><br>'
            context['reporter2'] = constellation['reporter2'].name + '<br><br>'
        if content['grade1'] is None:
            context['grade1'] = "/"
        else:
            context['grade1'] = content['grade1']
        if content['grade2'] is None:
            context['grade2'] = "/"
        else:
            context['grade2'] = content['grade2']
        if content['supervisor3']:
            context['supervisor3'] = 'Betreuer 3:<br><br>'
            context['supervisor3r'] = content['supervisor3'].name + '<br><br>'
        if content['grade3']:
            context['grade3'] = 'Note 3:<br><br>'
            context['grade3r'] = str(content['grade3']) + '<br><br>'
        return render(request, 'appointment.html', context)
    else:
        return redirect('/')


def management(request):
    """This function controls the behavior of the page that is used to reach the management pages."""
    context = {}
    context['group'] = getUserGroup(request.user)
    if context['group'] != "Office":
        return redirect('/')
    if request.POST.get('send') == 'request':
        return redirect('/managementRequest')
    if request.POST.get('send') == 'intern':
        return redirect('/managementIntern')
    if request.POST.get('send') == 'extern':
        return redirect('/managementExtern')
    return render(request, 'management.html', context)


def managementIntern(request):
    """This function controls the behavior of the page that is used to manage the intern examiners."""
    context = {}
    context['group'] = getUserGroup(request.user)
    if context['group'] != "Office":
        return redirect('/')
    if request.POST.get('add') == 'intern':
        if request.POST.get('type') and request.POST.get('subject') and request.POST.get('topic') \
                and request.POST.get('approval') and request.POST.get('email') \
                and request.POST.get('name'):
            examinerId = createInternExaminer(request.POST.get('email'), request.POST.get('name'))
            addQualification(examinerId, True, request.POST.get('type'), request.POST.get('subject'),
                             request.POST.get('topic'), request.POST.get('approval'))
            context['error1'] = 'Prüfer hinzugefügt'
        else:
            context['error1'] = 'Füllen Sie bitte alles aus'

    if request.POST.get('send') == 'email' and (request.POST.get('email') or request.session['email']) or \
            request.POST.get('delete') or request.POST.get('addQuali'):
        if request.POST.get('email'):
            email = request.POST.get('email')
            request.session['email'] = email
        if request.POST.get('delete'):
            deleteQualification(request.POST.get('delete'))
        if request.POST.get('addQuali') and request.POST.get('subject') and request.POST.get('topic'):
            examiner = getExaminer(None, None, True, request.session['email'])
            addQualification(examiner.id, True, request.POST.get('title'), request.POST.get('subject'),
                             request.POST.get('topic'), request.POST.get('approval'))
        context['searched'] = True
        examiner = getExaminer(None, None, True, request.session['email'])
        if examiner:
            context['found'] = True
            context['name'] = examiner.name
            context['email'] = examiner.email
            qualifications = ''
            informations = getExaminerInformations(examiner)
            for i in range(len(informations['topic'])):
                qualifications += '<tr><td>' + informations['title'][i] + \
                                  '</td><td>' + informations['subject'][i] + \
                                  '</td><td>' + informations['topic'][i] + \
                                  '</td><td>' + str(informations['approval'][i]) + \
                                  '</td><td><button ' \
                                  'type="submit" class="button" name="delete" value="' \
                                  + str(informations['qualId'][i]) + '" onclick="return ' \
                                                                     'confirm(\'Sind Sie sicher?\');">' \
                                                                     'Entfernen</button></td></tr>'
            context['qualifications'] = qualifications
        else:
            context['found'] = False
    else:
        context['searched'] = False

    subjectsList = getSubjects()
    subjects = ''
    for elem in subjectsList:
        subjects = '<option value="' + elem + '">' + elem + '</option>'
    context['subjects'] = subjects
    # Fill topics selection with data of database
    topicsList = getTopics('Informatik')
    topics = ''
    for elem in topicsList:
        topics += '<option value="' + elem + '">' + elem + '</option>'
    context['topics'] = topics
    return render(request, 'managementExaminer.html', context)


def managementExtern(request):
    """This function controls the behavior of the page that is used to manage the external examiners."""
    context = {}
    context['group'] = getUserGroup(request.user)
    if context['group'] != "Office":
        return redirect('/')
    if request.POST.get('add') == 'extern':
        if request.POST.get('type') and request.POST.get('subject') and request.POST.get('topic') \
                and request.POST.get('approval') and request.POST.get('password') and request.POST.get('email') \
                and request.POST.get('name'):
            examinerId = createExternalExaminer(request.POST.get('name'), request.POST.get('email'),
                                                request.POST.get('password'))
            addQualification(examinerId, False, request.POST.get('type'), request.POST.get('subject'),
                             request.POST.get('topic'), request.POST.get('approval'))
            context['error1'] = 'Prüfer hinzugefügt'
        else:
            context['error1'] = 'Füllen Sie bitte alles aus'

    if request.POST.get('send') == 'email' and (request.POST.get('email') or request.session['email']) or\
        request.POST.get('delete') or request.POST.get('addQuali'):
        if request.POST.get('email'):
            email = request.POST.get('email')
            request.session['email'] = email
        if request.POST.get('delete'):
            deleteQualification(request.POST.get('delete'))
        if request.POST.get('addQuali') and request.POST.get('subject') and request.POST.get('topic'):
            examiner = getExaminer(None, None, False, request.session['email'])
            addQualification(examiner.id, False, request.POST.get('title'), request.POST.get('subject'),
                             request.POST.get('topic'), request.POST.get('approval'))
        context['searched'] = True
        examiner = getExaminer(None, None, False, request.session['email'])
        if examiner:
            context['found'] = True
            context['name'] = examiner.name
            context['email'] = examiner.email
            qualifications = ''
            informations = getExaminerInformations(examiner)
            for i in range(len(informations['topic'])):
                qualifications += '<tr><td>' + informations['title'][i] + \
                                  '</td><td>' + informations['subject'][i] + \
                                  '</td><td>' + informations['topic'][i] + \
                                  '</td><td>' + str(informations['approval'][i]) + \
                                  '</td><td><button ' \
                                  'type="submit" class="button" name="delete" value="' \
                                  + str(informations['qualId'][i]) + '" onclick="return ' \
                                                                     'confirm(\'Sind Sie sicher?\');">' \
                                                                     'Entfernen</button></td></tr>'
            context['qualifications'] = qualifications
        else:
            context['found'] = False

    else:
        context['searched'] = False

    subjectsList = getSubjects()
    subjects = ''
    for elem in subjectsList:
        subjects = '<option value="' + elem + '">' + elem + '</option>'
    context['subjects'] = subjects
    # Fill topics selection with data of database
    topicsList = getTopics('Informatik')
    topics = ''
    for elem in topicsList:
        topics += '<option value="' + elem + '">' + elem + '</option>'
    context['topics'] = topics
    return render(request, 'managementExaminer.html', context)


def managementRequest(request):
    """This function controls the behavior of the page that is used to manage the requests of the students."""
    context = {}
    context['group'] = getUserGroup(request.user)
    roles = ['chairman', 'reporter1', 'reporter2', 'examiner', 'externalExaminer']
    if context['group'] != "Office":
        return redirect('/')
    if request.POST.get('send') == 'email' or request.POST.get('change') or request.POST.get('confirmations'):
        context['searched'] = True
        if request.POST.get('send') == 'email':
            email = request.POST.get('email')
            request.session['email'] = email
        else:
            email = request.session['email']
        if request.POST.get('change'):
            if request.POST.get('change') == 'oral':
                if request.POST.get('appointment1') and request.POST.get('chairman') and request.POST.get('reporter1') \
                        and request.POST.get('reporter2') and request.POST.get('examiner') \
                        and request.POST.get('externalExaminer'):
                    constellation = {}
                    for role in roles:
                        constellation[role] = getExaminer(None, request.POST.get(role)[1:],
                                                          int(request.POST.get(role)[0]))
                    if checkConstellation(getStudentId(request.session['email']), constellation):
                        if setExam(getStudentId(request.session['email']),
                                   request.POST.get('appointment1') + ' ' + request.POST.get('appointment2'),
                                   constellation):
                            context['error1'] = 'Verteidigung erstellt<br><br>'
                        else:
                            context['error1'] = 'Konstellation oder Zeitslot nicht erlaubt<br><br>'
                    else:
                        context['error1'] = 'Konstellation nicht erlaubt <br><br>'
            elif request.POST.get('change') == 'appointment':
                updateRequest('appointment', request.POST.get('appointment1') + ' '
                              + request.POST.get('appointment2'), email)
            else:
                updateRequest(request.POST.get('change'), request.POST.get(request.POST.get('change')), email)
        if request.POST.get('confirmations'):
            updateRequest('supervisor1Confirmed', None, email)
            updateRequest('supervisor2Confirmed', None, email)
            updateRequest('officeConfirmed', None, email)
            context['error2'] = 'Bestätigungen zurückgesetzt <br><br>'
        content = getStudentRequest(None, None, email)
        if content is not None:
            context['found'] = True
            context['title'] = content['title']
            context['supervisor1'] = content['supervisor1'].name
            context['supervisor2'] = content['supervisor2'].name
            context['deadline'] = content['deadline']
            context['topic'] = content['topic']
            context['type'] = content['type']
            context['status'] = content['status']
            context['subject'] = content['subject']
            if content['grade1'] is None:
                context['grade1'] = "/"
            else:
                context['grade1'] = content['grade1']
            if content['grade2'] is None:
                context['grade2'] = "/"
            else:
                context['grade2'] = content['grade2']
            if content['supervisor3']:
                context['supervisor3Set'] = True
                context['supervisor3'] = 'Betreuer 3:'
                context['supervisor3r'] = content['supervisor3'].name
            if content['grade3']:
                context['grade3Set'] = True
                context['grade3'] = 'Note Betreuer 3:'
                context['grade3r'] = str(content['grade3'])
            if content['appointment']:
                context['appointment'] = 'Verteidigung:'
                context['appointmentr'] = content['appointment']
            else:
                context['appointmentr'] = '/'
            supervisors = getExaminers()
            supervisorSelections = ''
            for elem in supervisors[1]:
                supervisorSelections += '<option value="1' + str(elem.id) + '">' + elem.name + '</option>'
            for elem in supervisors[0]:
                supervisorSelections += '<option value="0' + str(elem.id) + '">' + elem.name + '</option>'
            context['supervisors'] = supervisorSelections
            # Fill subjects selection with data of database
            subjectsList = getSubjects()
            subjects = ''
            for elem in subjectsList:
                subjects = '<option value="' + elem + '">' + elem + '</option>'
            context['subjects'] = subjects
            # Fill topics selection with data of database
            topicsList = getTopics('Informatik')
            topics = ''
            for elem in topicsList:
                topics += '<option value="' + elem + '">' + elem + '</option>'
            context['topics'] = topics
            constellation = getRequestConstellation(getStudentId(request.session['email']))
            for key in constellation:
                constellation[key] = constellation[key].name
            context.update(constellation)
            for role in roles:
                if not role in context:
                    context[role] = '/'
    else:
        context['searched'] = False
    return render(request, 'managementRequest.html', context)