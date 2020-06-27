from django.urls import path

from . import api

app_name = 'app'
urlpatterns = [
    path('events/', api.load_events),
    path('events/check', api.check_events),
    path('participants/', api.get_participants),
    path('participants/<ip>', api.get_participant),
    path('results/<ip>', api.get_participant_result),
    path('results/<ip>/download', api.download_participant_result),
    path('test/', api.check_testing)
]