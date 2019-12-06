import requests
import string
import random
import base64
import json

client_id = 'jgu.net_test_thema'
client_secret = 'jcOdxmM,IjY6W8DSv[qn_,+*WidEjZLaEZ/*D05qRJS2_yv1'
redirect_uri = 'http://localhost:8000'
authorize_url = "https://openid.uni-mainz.de/connect/authorize"
token_url = "https://openid.uni-mainz.de/connect/token"
user_url = "https://openid.uni-mainz.de/connect/userinfo"

def getAuthorizationURL():
    state = generateState(30)
    return authorize_url + "?response_type=code&client_id=" \
           + client_id + "&redirect_uri=" + redirect_uri \
           + "&scope=openid+email&state=" + state + "&client_secret=" \
           + client_secret, state

def generateState(length):
    #todo code into state if user is prüfer or student
    state = ""
    for i in range(length):
        state += random.choice(string.ascii_letters + string.digits)
    if not isStateUsed(state):
        return state
    return generateState(length)

def isStateUsed(state):
    return False

def getToken(code):
    data = {'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret}
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    r = requests.post(token_url, data = data, headers=headers)
    params = r.json()
    return (params['access_token'],params['id_token'])

def getUserId(idToken):
    content = idToken.split('.')[1]
    sub = json.loads(base64.b64decode(content + "=="))['sub']
    return sub

def getEmail(accessToken):
    headers = {'Authorization': "Bearer " + accessToken}
    r = requests.post(user_url, headers=headers)
    return r.json()['email']

def getClaims(code):
    accessToken, idToken = getToken(code)
    sub = getUserId(idToken)
    email = getEmail(accessToken)
    print(sub)
    return {'sub': sub,
            'email': email}