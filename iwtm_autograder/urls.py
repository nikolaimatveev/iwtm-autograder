from django.contrib import admin
from django.urls import include, path
from django.conf.urls import url

urlpatterns = [
    url('api/', include('app.urls')),
    path('admin/', admin.site.urls),
]