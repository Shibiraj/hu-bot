from django.conf.urls import url

from app.views import *

# django web views
urlpatterns = [
    url(r'^webhook', webhook, name="webhook"),
]
