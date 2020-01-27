from django.contrib.auth.models import AbstractUser
from django.db import models


class MyUser(AbstractUser):
    is_admin = models.BooleanField(default=False)
    points = models.FloatField(default=0)
    address = models.TextField(null=True, blank=True)
    mobile_number = models.CharField(null=True, blank=True, max_length=100)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    place_id = models.CharField(max_length=64, blank=True, null=True)
    rating = models.IntegerField(default=1)


class Votes(models.Model):
    lx_id = models.CharField(max_length=128, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    voted_by = models.ManyToManyField(MyUser, related_name='voted_user', blank=True)

    def __str__(self):
        return 'Adventure {}'.format(self.lx_id) if int(self.lx_id) in [170364, 546233, 311106, 404252,
                                                                        188309] else self.lx_id


class History(models.Model):
    req_user = models.CharField(max_length=128, null=True, blank=True)
    user = models.ForeignKey(MyUser, null=True, blank=True, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

class HistoryChat(models.Model):
    req_user = models.CharField(max_length=128, null=True, blank=True)
    is_active = models.BooleanField(default=True)
