from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=0)
    zdvId = models.CharField(max_length=50)
    name = models.CharField(max_length=50)
    email = models.EmailField()
    abgabetermin = models.DateField(null=True)
    fach = models.CharField(max_length=50, null=True)
    titel = models.CharField(max_length=50, null=True)
    themengebiet = models.CharField(max_length=50, null=True)
    artDerArbeit = models.CharField(max_length=50, null=True)
    betreuer1 = models.IntegerField(null=True)
    istBetreuer1Intern = models.BooleanField(null=True)
    betreuer2 = models.IntegerField(null=True)
    istBetreuer2Intern = models.BooleanField(null=True)
    drittgutachter = models.IntegerField(null=True)
    istDrittgutachterIntern = models.BooleanField(null=True)
    status = models.CharField(max_length=50, null=True)
    note1 = models.IntegerField(null=True)
    note2 = models.IntegerField(null=True)
    note3 = models.IntegerField(null=True)

    betreuer1Bestaetigt = models.BooleanField(null=True)
    betreuer2Bestaetigt = models.BooleanField(null=True)
    prüfungsamtBestaetigt = models.BooleanField(null=True)
    terminEntstanden = models.BooleanField(null=True)
    pruefungsamtBestaetigtTermin = models.BooleanField(null=True)


class InternerPruefer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=0)
    name = models.CharField(max_length=50)
    email = models.EmailField()
    zdvId = models.CharField(max_length=50)


class ExternerPruefer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=0)
    name = models.CharField(max_length=50)
    email = models.EmailField()


class Qualifikation(models.Model):
    titel = models.CharField(max_length=50)
    fach = models.CharField(max_length=50)
    themengebiet = models.CharField(max_length=50)
    prueferzulassung = models.BooleanField()
    pruefer = models.IntegerField()
    istPrueferIntern = models.BooleanField()


class Einladung(models.Model):
    angenommen = models.BooleanField()
    anzahlEinladungen = models.IntegerField()
    pruefer = models.IntegerField()
    istPrueferIntern = models.BooleanField()
    student = models.ForeignKey(Student, on_delete=models.CASCADE)


class Zeitslot(models.Model):
    beginn = models.DateTimeField()


class VerfuegbarkeitEinladung(models.Model):
    einladung = models.ForeignKey(Einladung, on_delete=models.CASCADE)
    zeitslot = models.ForeignKey(Zeitslot, on_delete=models.CASCADE)


class VerfuegbarkeitAnfrage(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    zeitslot = models.ForeignKey(Zeitslot, on_delete=models.CASCADE)


class Bevorzugt(models.Model):
    class Meta:
        unique_together = ['pruefer', 'student']
    pruefer = models.IntegerField()
    istPrueferIntern = models.BooleanField()
    student = models.ForeignKey(Student, on_delete=models.CASCADE)


class Pruefungsamt(models.Model):
    # Verknuepfung zum Auth_User von Django
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=0)

class PasswordLess(object):
    def authenticate(self, request, username, password=None, **kwargs):
        User = get_user_model()
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            return None
        else:
            if getattr(user, 'is_active', False):
                return user
        return None
    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

