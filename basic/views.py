from django.shortcuts import render, HttpResponse, redirect
from .authorization import *
from .databaseHandler import *
from django.contrib.auth import authenticate, login, logout as django_logout
from .forms import *

stateLength = 30

def index(request):
    if request.user.is_authenticated:
        return redirect('/home')
    if request.method == 'GET' and 'state' in request.GET:
        if request.session['state'] == request.GET['state']:
            claims = getClaims(request.GET['code'])
            user = getUser(claims['email'], claims['sub'], request.GET['state'], stateLength, claims['name'])
            user.backend = 'basic.auth_backend.PasswordlessAuthBackend'
            authenticate(username=claims['email'])
            login(request, user)
            return redirect('/home')
    if request.POST.get('loginAs') == "student":
        url, state = getAuthorizationURL("student", stateLength)
        request.session['state'] = state
        request.POST
        return redirect(url)
    if request.POST.get('loginAs') == "pruefer":
        url, state = getAuthorizationURL("pruefer", stateLength)
        request.session['state'] = state
        return redirect(url)
    if request.POST.get('loginAs') == "extern":
        user = authenticate(username=request.POST['email'], password=request.POST['password'])
        if user is not None:
            login(request, user)
            return redirect('/home')
        else:
            return render(request, 'index.html', {'error': "Falsche Anmeldedaten <br> "})
    return render(request, 'index.html')

def home(request):
    if request.user.is_authenticated:
        if getUserGroup(request.user) == "Student" and not haveRequest(request.user):
            return redirect('/anfrage')
        context = {}
        group = getUserGroup(request.user)
        context['group'] = group
        if group == "Student":
            content = getRequest(request.user)
            context['titel'] = content['titel']
            context['betreuer1'] = content['betreuer1']
            context['betreuer2'] = content['betreuer2']
            context['abgabetermin'] = content['abgabetermin']
            context['themengebiet'] = content['themengebiet']
            context['art'] = content['art']
            context['status'] = content['status']
            if content['note1'] is None:
                context['note1'] = "/"
            else:
                context['note1'] = content['note1']
            if content['note2'] is None:
                context['note2'] = "/"
            else:
                context['note2'] = content['note2']
            return render(request, 'homeStudent.html', context)
        if group == "Prüfungsamt":
            container1Request = getNotAcceptedRequests("Prüfer", request.user)
            container1 = ""
            for elem in container1Request:
                container1 += '<p class="alignleft">' + elem.name + ' </p> \n'
                container1 += '<p class="alignright">Text on the right</p>'
            context['container1'] = container1
            return render(request, 'homePruefungsamt.html', context)
        if group == "Prüfer":
            if request.POST.get('details'):
                #TODO redirect to a details page
                print(request.POST.get('details'))
            #Container 1
            container1 = ""
            container1Request = getNotAcceptedRequests("Prüfer", request.user)
            for elem in container1Request:
                container1 += '<p class="alignleft">' + elem.name + ' </p>'
                container1 += '<p class="alignright"><button type="submit" name="details" value="' + str(elem.id) \
                              + '">Details</button></p><br/><br/>'
            container1Request = getRequestsOfPrüfer(request.user, "Schreibphase")
            for elem in container1Request:
                container1 += '<p class="alignleft">' + elem.name + ' </p>'
                container1 += '<p class="alignright">In Schreibphase</p><br/><br/>'
            context['container1'] = container1

            #Container 2
            container2 = ""
            container2Request = getNotRatedRequests(request.user)
            for elem in container2Request:
                container2 += '<p class="alignleft">' + elem.name + ' </p>'
                container2 += '<p class="alignright"><button type="submit" name="bewerten" value="' + str(elem.id) \
                              + '">Bewerten</button></p><br/><br/>'
            container2Request = getRatedRequests(request.user)
            for elem in container2Request:
                container2 += '<p class="alignleft">' + elem.name + ' </p>'
                container2 += '<p class="alignright">Bewertet</p><br/><br/>'
            context['container2'] = container2

            #Container 3
            container3 = ""
            container3Request = getNotAnsweredInvitations(request.user)
            names = []
            for elem in container3Request:
                name = getStudentName(elem.student)
                if name not in names:
                    container3 += '<p class="alignleft">' + name + ' </p>'
                    container3 += '<p class="alignright"><button type="submit" name="antworten" value="' + str(elem.id) \
                                  + '">Antworten</button></p><br/><br/>'
                    names.append(name)
            context['container3'] = container3

            #Container 4
            container4 = ""
            container4Request = getAnsweredInvitations(request.user)
            names = []
            for elem in container4Request:
                name = getStudentName(elem.student)
                if name not in names:
                    container4 += '<p class="alignleft">' + name + ' </p>'
                    container4 += '<p class="alignright">Beantwortet</p><br/><br/>'
                    names.append(name)
            context['container4'] = container4

            # Container 5
            container5 = ""
            container5Request = getFinalDates(request.user)
            for elem in container5Request:
                container5 += '<p class="alignleft">' + elem.name + ' </p>'
                container5 += '<p class="alignright">' + str(elem.verteidigungstermin)[:16] + '</p><br/><br/>'
            context['container5'] = container5
            return render(request, 'homePruefer.html', context)
    else:
        return redirect('/')

def anfrage(request):
    #TODO Fill the drop down selections with data from the database
    if request.user.is_authenticated:
        if request.POST.get('anfrage') == "anfrage":
            form = Anfrage(request.POST)
            if (form.is_valid()):
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
                return redirect('/home')
            else:
                context = {}
                context['error'] = form.errors
                return render(request, 'anfrage.html', context)
        if getUserGroup(request.user) == "Student" and not haveRequest(request.user):
            return render(request, 'anfrage.html')
        return redirect('/home')
    else:
        return redirect('/')

def logout(request):
    django_logout(request)
    return redirect('/')