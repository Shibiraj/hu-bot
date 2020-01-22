from django.conf.urls import url
from app.views import *

# django web views
urlpatterns = [
    url(r'^callback', call_back, name="callback"),
    url(r'^msgin', msg_in, name="msgin"),
    url(r'^webhook', webhook, name="webhook"),
    url(r'^upvote$',  upvote, name="upvote"),

    url(r'^test$', TestView.as_view(), name="test")
]