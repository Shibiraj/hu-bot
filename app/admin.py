from django.contrib import admin

from app.models import *

# Register your models here.
admin.site.register(MyUser)
admin.site.register(Votes)
admin.site.register(History)
admin.site.register(RestaurantVote)
