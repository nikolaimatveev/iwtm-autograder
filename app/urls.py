from django.urls import path

from . import views

app_name = 'app'
urlpatterns = [
    path('events/', views.load_events),
    path('events/check', views.check_events),
    path('participants/', views.get_participant_ip_list),
    path('participants/<ip>', views.get_participant_info),
    path('results/<ip>', views.get_participant_results),
    path('results/<ip>/download', views.download_participant_results),
    path('test/', views.check_testing),
    path('login/', views.login_to_iwtm)
]