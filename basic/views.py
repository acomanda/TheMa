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
            changeStatus(request.POST.get('rating'), "Gutachteneingabe")
        if request.POST.get('scheduling'):
            request.session['requestId'] = request.POST.get('scheduling')
            return redirect('/chairman')
        if request.POST.get('supervisor3'):
            request.session['requestId'] = request.POST.get('supervisor3')
            return redirect('/supervisor3')
        # Container 1
        container1Request = getRequestsOfOffice("Anfrage wird bestätigt", False)
        container1 = ""
        for elem in container1Request:
            container1 += '<p class="alignleft">' + elem.name + ' </p> \n'
            container1 += '<p class="alignright"><button type="submit" name="details" value="' + str(elem.id) \
                          + '">Details</button></p><br/><br/>'
        container1Request = getRequestsOfOffice("Anfrage wird bestätigt", True)
        for elem in container1Request:
            container1 += '<p class="alignleft">' + elem.name + ' </p> \n'
            container1 += '<p class="alignright">Bestätigt</p><br/><br/>'
        container1Request = getRequestsOfOffice("Schreibphase", None, True)
        for elem in container1Request:
            container1 += '<p class="alignleft">' + elem.name + ' </p> \n'
            container1 += '<p class="alignright"><button type="submit" name="rating" value="' + str(elem.id) \
                          + '">Gutachteineingabe frei geben</button></p><br/><br/>'
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
                          + '">Terminfindung starten</button></p><br/><br/>'
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
        container4Request = getRequestsOfOffice("Terminfindung", None, None, None, None, True, False)
        container4 = ""
        for elem in container4Request:
            container4 += '<p class="alignleft">' + elem.name + ' </p> \n'
            container4 += '<p class="alignright"><button type="submit" name="supervisor3" value="' + str(elem.id) \
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
        container1Request = getRequestsOfExaminer(request.user, "Anfrage wird bestätigt", False)
        for elem in container1Request:
            container1 += '<p class="alignleft">' + elem.name + ' </p>'
            container1 += '<p class="alignright"><button type="submit" name="details" value="' + str(elem.id) \
                          + '">Details</button></p><br/><br/>'
        container1Request = getRequestsOfExaminer(request.user, "Schreibphase", True)
        for elem in container1Request:
            container1 += '<p class="alignleft">' + elem.name + ' </p>'
            container1 += '<p class="alignright">In Schreibphase</p><br/><br/>'
        container1Request = getRequestsOfExaminer(request.user, "Anfrage wird bestätigt", True)
        for elem in container1Request:
            container1 += '<p class="alignleft">' + elem.name + ' </p>'
            container1 += '<p class="alignright">Anfrage wird bestätigt</p><br/><br/>'
        context['container1'] = container1

        #Container 2
        container2 = ""
        container2Request = getRequestsOfExaminer(request.user, "Gutachteneingabe", None, False)
        for elem in container2Request:
            container2 += '<p class="alignleft">' + elem.name + ' </p>'
            container2 += '<p class="alignright"><button type="submit" name="rate" value="' + str(elem.id) \
                          + '">Bewerten</button></p><br/><br/>'
        container2Request = getRequestsOfExaminer(request.user, "Gutachteneingabe", None, True)
        for elem in container2Request:
            container2 += '<p class="alignleft">' + elem.name + ' </p>'
            container2 += '<p class="alignright">Bewertet</p><br/><br/>'
        context['container2'] = container2

        #Container 3
        container3 = ""
        container3Request = getRequestsOfExaminer(request.user, "Terminfindung", None, None, False)
        for elem in container3Request:
            container3 += '<p class="alignleft">' + elem.name + ' </p>'
            container3 += '<p class="alignright"><button type="submit" name="answer" value="' + str(elem.id) \
                          + '">Antworten</button></p><br/><br/>'
        context['container3'] = container3

        #Container 4
        container4 = ""
        container4Request = getRequestsOfExaminer(request.user, "Terminfindung", None, None, True)
        names = []
        for elem in container4Request:
            container4 += '<p class="alignleft">' + elem.name + ' </p>'
            container4 += '<p class="alignright">Beantwortet</p><br/><br/>'
        context['container4'] = container4

        # Container 5
        container5 = ""
        container5Request = getRequestsOfExaminer(request.user, "Termin enstanden", None, None, None, True)
        for elem in container5Request:
            container5 += '<p class="alignleft">' + elem.name + ' </p>'
            container5 += '<p class="alignright">' + str(elem.verteidigungstermin)[:16] + '</p><br/><br/>'
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
    context['supervisor1'] = content['supervisor1']
    context['supervisor2'] = content['supervisor2']
    context['deadline'] = content['deadline']
    context['topic'] = content['topic']
    context['type'] = content['type']
    context['status'] = content['status']
    context['subject'] = content['subject']
    if request.POST.get('answerRequest'):
        if request.POST.get('answerRequest') == "accept":
            if group == "Examiner":
                confirmOrNotRequest(request.session['requestId'], True, "Examiner", request.user)
                return redirect('/')
            else:
                confirmOrNotRequest(request.session['requestId'], True, "Office", request.user)
                return redirect('/')
        elif request.POST.get('answerRequest') == "reject":
            if group == "Examiner":
                confirmOrNotRequest(request.session['requestId'], False, "Examiner", request.user)
                return redirect('/')
            else:
                confirmOrNotRequest(request.session['requestId'], False, "Office", request.user)
                return redirect('/')
    return render(request, 'requestDetails.html', context)


def anfrage(request):
    """This function controls the behavior of the page that is used to make a new request."""
    if request.user.is_authenticated:
        context = {}
        if request.POST.get('anfrage') == "anfrage":
            form = Anfrage(request.POST)
            if (form.is_valid() and form.cleaned_data['betreuer1'] != form.cleaned_data['betreuer2']):
                abgabetermin = form.cleaned_data['abgabetermin']
                fach = form.cleaned_data['fach']
                betreuer1 = form.cleaned_data['betreuer1'][1:]
                betreuer1Intern = form.cleaned_data['betreuer1'][0] == "1"
                betreuer2 = form.cleaned_data['betreuer2'][1:]
                betreuer2Intern = form.cleaned_data['betreuer2'][0] == "1"
                themengebiet = form.cleaned_data['themengebiet']
                art = form.cleaned_data['art']
                titel = form.cleaned_data['titel']
                makeRequest(request.user, abgabetermin, fach, betreuer1, betreuer2, themengebiet, art, titel, betreuer1Intern, betreuer2Intern)
                return redirect('/')
            else:
                context = {}
                context['error'] = form.errors
                if form.cleaned_data['betreuer1'] == form.cleaned_data['betreuer2']:
                    context['errorSupervisor'] = '<ul class="errorlist"><li>Betreuer<ul class="errorlist">' \
                                                 '<li>Wähle verschiedene Betreuer aus.</li></ul></li></ul>'
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
    context = {}
    group = getUserGroup(request.user)
    context['group'] = group
    if request.POST.get('confirm'):
        gradeRequest(request.user, request.session['requestId'], float(request.POST.get('grade')))
        return redirect('/')
    content = getStudentRequest(None, request.session['requestId'])
    context['title'] = content['title']
    context['supervisor1'] = content['supervisor1']
    context['supervisor2'] = content['supervisor2']
    context['deadline'] = content['deadline']
    context['topic'] = content['topic']
    context['type'] = content['type']
    context['status'] = content['status']
    context['subject'] = content['subject']
    return render(request, 'requestDetails.html', context)


def supervisor3(request):
    context = {}
    group = getUserGroup(request.user)
    context['group'] = group
    if request.POST.get('confirm'):
        if not setSupervisor3(request.session['requestId'], request.POST.get('supervisor3')[1],
                       request.POST.get('supervisor3')[0]):
            context['error'] = 'Wähle einen Drittprüfer, der nicht bereits ein Prüfer ist.'
        else:
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
    externalExaminers, internExaminers = getExaminers(True)
    for elem in externalExaminers:
        supervisors += '<option value="0' + str(elem.id) + '">' + elem.name + '</option>'
    for elem in internExaminers:
        supervisors += '<option value="1' + str(elem.id) + '">' + elem.name + '</option>'
    context['supervisors'] = supervisors
    return render(request, 'requestDetails.html', context)


def chairman(request):
    context = {}
    group = getUserGroup(request.user)
    context['group'] = group
    if request.POST.get('confirm'):
        if not createExaminerConstellation(Student.objects.filter(id=request.session['requestId'])[0].user,
                                           {'chairman': ExternalExaminer.objects.filter(id=1)[0]}):

            context['error'] = 'Leider gibt es nicht genug Prüfer um eine Konstellation zu generieren.'
        else:
            print('hallo')
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
    # todo Implement the choice of an entire day and week
    if request.user.is_authenticated:
        amountSlots = getRecentAvailabilities(request.user, request.session['requestId'], None, None).count()
        if request.POST.get('exit'):
            if request.POST.get('exit') == 'accept' and amountSlots > 0:
                moveAvailabilitiesToRequest(request.user, request.session['requestId'])
                acceptOrNotInvitation(request.user, request.session['requestId'], True)
                return redirect('/')
            elif request.POST.get('exit') == 'reject' and amountSlots == 0:
                acceptOrNotInvitation(request.user, request.session['requestId'], False)
                return redirect('/')
        if request.POST.get('choose'):
            if request.POST.get('choose') == 'week':
                pass
            addAvailabilityToInvitation(request.user, request.session['requestId'], request.POST.get('choose'))
            request.session['stay'] = True
        if request.POST.get('delete'):
            deleteAvailabilityOfInvitation(request.user, request.session['requestId'], request.POST.get('delete'))
        context = {}
        group = getUserGroup(request.user)
        context['group'] = group
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

        timeSlots = getTimeSlots(request.session['requestId'], startDate.strftime("%m/%d/%Y"),
                                 endDate.strftime("%m/%d/%Y"))
        timeSlots = getWeekSlots(timeSlots, startDate.strftime("%m/%d/%Y"))
        chosenTimeSlots = getRecentAvailabilities(request.user, request.session['requestId'], startDate.strftime("%m/%d/%Y"),
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
        return render(request, 'answerInvitation.html', context)
    else:
        return redirect('/')
