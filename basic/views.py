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
        context['group'] = getUserGroup(request.user)
        return render(request, 'home.html', context)
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