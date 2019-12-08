from django.shortcuts import render, HttpResponse, redirect
from .authorization import *
from .databaseHandler import *
from django.contrib.auth import authenticate, login, logout as django_logout

stateLength = 30

def index(request):
    if request.user.is_authenticated:
        return redirect('/home')
    if request.method == 'GET' and 'state' in request.GET:
        if request.session['state'] == request.GET['state']:
            claims = getClaims(request.GET['code'])
            user = getUser(claims['email'], claims['sub'], request.GET['state'], stateLength)
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
    return render(request, 'index.html')

def home(request):
    return render(request, 'home.html')

def logout(request):
    django_logout(request)
    return redirect('/')