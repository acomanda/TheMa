from django import forms

class Anfrage(forms.Form):
    abgabetermin = forms.DateField()
    fach = forms.CharField()
    betreuer1 = forms.CharField(label="betreuer1")
    betreuer2 = forms.CharField()
    themengebiet = forms.CharField()
    art = forms.CharField()
    titel = forms.CharField()