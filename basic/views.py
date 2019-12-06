from django.shortcuts import render, HttpResponse, redirect
from .authorization import *

# Create your views here.
def index(request):
    if request.method == 'GET' and 'state' in request.GET:
        if request.session['state'] == request.GET['state']:
            claims = getClaims(request.GET['code'])
        return HttpResponse(claims['email'])
    url, state = getAuthorizationURL()
    request.session['state'] = state
    print(url)
    return redirect(url)