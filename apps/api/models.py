from django.db import models
import uuid
from django.contrib.auth.models import User

# Create your models here.
class TimeStampedUUIDModel(models.Model):
    pkid = models.BigAutoField(primary_key=True, editable=False)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class WorkingUnit(TimeStampedUUIDModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    code = models.CharField(max_length=255, blank=True, null=True)
    level = models.IntegerField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, related_name="children", blank=True, null=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

class Log(TimeStampedUUIDModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(null=True, blank=True)
    feature_name = models.CharField(null=True, blank=True)
    message = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.message 

class Profile(TimeStampedUUIDModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    nik = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    gender = models.CharField(max_length=255, blank=True, null=True)
    working_unit = models.ForeignKey(WorkingUnit, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE,blank=True, null=True)