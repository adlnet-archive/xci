from django.db import models
from djangotoolbox.fields import ListField, DictField
from django.contrib.auth.models import AbstractUser

class SystemUser(AbstractUser):
	competencies = ListField(DictField(), null=True)

class CompFramework(models.Model):
	title = models.CharField(max_length=50)
	description = models.TextField()
	encoded_string = models.CharField(max_length=50)
	catalog = models.CharField(max_length=50)
	entry = models.CharField(max_length=50)
	comp_type = models.CharField(max_length=50)
	date = models.DateTimeField(auto_now_add=True, null=True)
	competencies = ListField(DictField())

class PerfFramework(models.Model):
	title = models.CharField(max_length=50)
	description = models.TextField()
	encoded_string = models.CharField(max_length=50)
	catalog = models.CharField(max_length=50)
	entry = models.CharField(max_length=50)
	comp_type = models.CharField(max_length=50)
	date = models.DateTimeField(auto_now_add=True, null=True)
	references = ListField(DictField())
	components = ListField(DictField())