from django.urls import path

from . import views

app_name = 'app'
urlpatterns = [
    path('', views.index, name='index'),
    path('results', views.compare_events, name='results'),
    path('events', views.list_real_events, name='events'),
    path('uploadTemplate', views.upload_template_events, name='upload-template'),
    path('uploadReal', views.upload_real_events, name='upload-real')
]