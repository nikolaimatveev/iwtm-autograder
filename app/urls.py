from django.urls import path
from django.conf.urls.static import static
from django.conf import settings

from . import api

app_name = 'app'
urlpatterns = [
    path('events/', api.load_events),
    path('events/check', api.check_events),
    path('participants/', api.get_participants),
    path('participants/<number>', api.get_participant),
    path('results/<number>', api.get_participant_result),
    path('results/<number>/download', api.download_participant_result),
    path('test/', api.check_testing)
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)