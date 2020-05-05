from django.urls import path

from . import views

app_name = 'app'
urlpatterns = [
    path('', views.index, name='index'),
    path('skip', views.remove_delta, name='skip'),
    path('compare', views.compare_events, name='compare'),
    path('events', views.list_real_events, name='events'),
    path('test', views.test, name='test')
]