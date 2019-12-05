from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser


class Student(models.Model):
    zdvId = models.IntegerField()
    name = models.CharField(max_length=50)
    email = models.EmailField()
    abgabetermin = models.DateField()
    fach = models.CharField(max_length=50)
    titel = models.CharField(max_length=50)
    themengebiet = models.CharField(max_length=50)
    artDerArbeit = models.CharField(max_length=50)
    prüfungsamtBestaetigt = models.BooleanField()
    terminEntstanden = models.BooleanField()
    # Eigentlich sollte das ein Foreign key sein, da wir aber
    # zwei verschiedene Pruefer Tabellen haben, nutzen wir IntegerField
    betreuer1Bestaetigt = models.BooleanField()
    betreuer2Bestaetigt = models.BooleanField()
    pruefungsamtBestaetigtTermin = models.BooleanField()
    betreuer1 = models.IntegerField()
    istBetreuer1Intern = models.BooleanField()
    betreuer2 = models.IntegerField()
    istBetreuer2Intern = models.BooleanField()
    drittgutachter = models.IntegerField()
    istDrittgutachterIntern = models.BooleanField()
    status = models.CharField(max_length=50)
    note1 = models.IntegerField()
    note2 = models.IntegerField()
    note3 = models.IntegerField()


class InternerPruefer(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField()
    zdvId = models.IntegerField()


class ExternerPruefer(models.Model):
    # Verknuepfung zum Auth_User von Django
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

