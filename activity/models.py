from django.conf import settings
from django.db import models
class Activity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    username = models.CharField(max_length=150)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    action = models.CharField(max_length=30)
    section = models.CharField(max_length=150)
    object_id = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    changes = models.JSONField(default=dict)
    class Meta:
        ordering = ['-created', '-pk']
        default_permissions = ('view',)
