from django.urls import path

from . import views

app_name = 'app'
urlpatterns = [
    path('events/', views.load_events),
    path('events/check', views.check_events),
    path('participants/', views.get_participants),
    path('participants/<ip>', views.get_participant),
    path('results/<ip>', views.get_participant_result),
    path('results/<ip>/download', views.download_participant_result),
    path('test/', views.check_testing),
    path('login/', views.login_to_iwtm)
]