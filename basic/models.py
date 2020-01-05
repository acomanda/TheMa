from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model


class Student(models.Model):
    # Connection to the django user
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=0)
    # Id used in the zdv servers
    zdvId = models.CharField(max_length=50)
    name = models.CharField(max_length=50)
    email = models.EmailField()
    # deadline for the physical thesis
    deadline = models.DateField(null=True)
    title = models.CharField(max_length=50, null=True)
    subject = models.CharField(max_length=50, null=True)
    topic = models.CharField(max_length=50, null=True)
    type = models.CharField(max_length=50, null=True)
    supervisor1 = models.IntegerField(null=True)
    # Bool that says whether the examiner is an internal or external
    isSupervisor1Intern = models.BooleanField(null=True)
    supervisor2 = models.IntegerField(null=True)
    # Bool that says whether the examiner is an internal or external
    isSupervisor2Intern = models.BooleanField(null=True)
    supervisor3 = models.IntegerField(null=True)
    # Bool that says whether the examiner is an internal or external
    isSupervisor3Intern = models.BooleanField(null=True)
    # String that contains the status of the request
    status = models.CharField(max_length=50, null=True)
    grade1 = models.FloatField(null=True)
    grade2 = models.FloatField(null=True)
    grade3 = models.FloatField(null=True)
    # Date for the defense of the thesis
    appointment = models.DateTimeField(null=True)
    # Booleans that are set true if the examination office and the supervisors confirm the request at the beginning
    supervisor1Confirmed = models.BooleanField(null=True)
    supervisor2Confirmed = models.BooleanField(null=True)
    officeConfirmed = models.BooleanField(null=True)
    # Bool that indicates whether an appointment has already been found
    appointmentEmerged = models.BooleanField(null=True)
    # Bool that indicates whether the examination office has finally confirmed the date
    officeConfirmedAppointment = models.BooleanField(null=True)


class InternExaminer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=0)
    name = models.CharField(max_length=50)
    email = models.EmailField()
    zdvId = models.CharField(max_length=50)


class ExternalExaminer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=0)
    name = models.CharField(max_length=50)
    email = models.EmailField()


class Qualification(models.Model):
    title = models.CharField(max_length=50)
    subject = models.CharField(max_length=50)
    topic = models.CharField(max_length=50)
    # Bool that indicates if the examiner is allowed to test
    approvalToTest = models.BooleanField()
    examiner = models.IntegerField()
    isExaminerIntern = models.BooleanField()


class Invitation(models.Model):
    # Bool that says whether the invitation was accepted
    accepted = models.BooleanField(null=True)
    # Integer that indicates how often the examiner has already been invited
    # for the same request
    numberInvitations = models.IntegerField()
    examiner = models.IntegerField()
    isExaminerIntern = models.BooleanField()
    student = models.ForeignKey(Student, on_delete=models.CASCADE)


class TimeSlot(models.Model):
    # Only the start is saved since each time slot is reserved exactly for 2 hours
    start = models.DateTimeField()


class AvailabilityInvitation(models.Model):
    # This table stores the time slots that an examiner selects when responding to an invitation
    invitation = models.ForeignKey(Invitation, on_delete=models.CASCADE)
    timeSlot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)


class AvailabilityRequest(models.Model):
    # This table stores the time slots that are still possible for a request
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    timeSlot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)


class Preference(models.Model):
    # This table actually stores a student's preferences for examiners
    # It is currently not used but can be integrated in later developments
    class Meta:
        unique_together = ['examiner', 'student']
    examiner = models.IntegerField()
    isExaminerIntern = models.BooleanField()
    student = models.ForeignKey(Student, on_delete=models.CASCADE)


class Office(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=0)


class PasswordLess(object):
    # This class is used to log in a user without entering a password
    # It is required to ensure the ZDV log in

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
