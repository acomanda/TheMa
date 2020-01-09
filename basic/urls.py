from django.urls import path
from . import views

urlpatterns = [
    path('', views.index),
    path('homeoffice', views.homeOffice),
    path('homestudent', views.homeStudent),
    path('homeexaminer', views.homeExaminer),
    path('logout', views.logout),
    path('anfrage', views.anfrage),
    path('confirmrequest', views.confirmRequest),
    path('grading', views.grading),
    path('supervisor3', views.supervisor3),
    path('chairman', views.chairman),
    path('answerInvitation', views.answerInvitation)
]
