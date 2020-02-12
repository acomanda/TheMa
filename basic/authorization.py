import requests
import string
import random
import base64
import json

client_id = 'jgu.net_test_thema'
# Usually the client secret should be saved separately.
# In this case, however, it is only a test client ID that will never actually be used.
client_secret = 'jcOdxmM,IjY6W8DSv[qn_,+*WidEjZLaEZ/*D05qRJS2_yv1'
redirect_uri = 'http://localhost:8000'
authorize_url = "https://openid.uni-mainz.de/connect/authorize"
token_url = "https://openid.uni-mainz.de/connect/token"
user_url = "https://openid.uni-mainz.de/connect/userinfo"


def getAuthorizationURL(group, stateLength):
    """
    This function is used to receive the URL that is needed to authenticate a user by his ZDV account
    :param group: String that tells which kind of user is trying to login (str)
    :param stateLength: Length of the random string that is used to identify the answer of the server
    :return:
    """
    state = generateState(stateLength, group)
    return authorize_url + "?response_type=code&client_id=" \
           + client_id + "&redirect_uri=" + redirect_uri \
           + "&scope=openid+email+name&state=" + state + "&client_secret=" \
           + client_secret, state


def generateState(length, group):
    """
    This function generates a string that contains the group of the user that want to login and a random string
    :param length: Length of the random string that is added to the group (int)
    :param group: String that tells which kind of user is trying to login (str)
    :return: Newly generated string that consists of the group and a random string of the given length
    """
    state = ""
    for i in range(length):
        state += random.choice(string.ascii_letters + string.digits)
    state += group
    return state


def getToken(code):
    """
    This function is used to receive a token by using an authorization code
    :param code: Authorization code (str)
    :return: Tuple that contains the access Token and the id Token (JSon, JSon)
    """
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
    """
    This function extracts the ZDV Id of the given id Token
    :param idToken: Id Token (JSon)
    :return: ZDV Id that was encoded in the id Token (str)
    """
    content = idToken.split('.')[1]
    sub = json.loads(base64.b64decode(content + "=="))['sub']
    return sub


def getEmail(accessToken):
    """
    This function extracts the E-Mail of the given access Token
    :param accessToken: Access Token (JSon)
    :return: ZDV E-Mail that was encoded in the access Token (str)
    """
    headers = {'Authorization': "Bearer " + accessToken}
    r = requests.post(user_url, headers=headers)
    return r.json()['email']


def getName(accessToken):
    """
    This function extracts the Name of the given access Token
    :param accessToken: Access Token (JSon)
    :return: Name of the user that was encoded in the access Token (str)
    """
    headers = {'Authorization': "Bearer " + accessToken}
    r = requests.post(user_url, headers=headers)
    return r.json()['name']


def getClaims(code):
    """
    This function uses the other functions in this file to return the claims that the system gets if the given
    authorization code is used
    :param code: Authorization code (str)
    :return: Dictionary that contains the ZDV Id, E-mail and Name of the user that has done the login
    """
    accessToken, idToken = getToken(code)
    sub = getUserId(idToken)
    email = getEmail(accessToken)
    name = getName(accessToken)
    return {'sub': sub,
            'email': email,
            'name': name}