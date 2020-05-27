import datetime
import os.path
import json

from .models import Event
from .services import EventService
from itertools import zip_longest
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.http import HttpResponseRedirect

event_service = EventService()
template_path = 'app/static/upload/template.csv'

def index(request):
    
    if os.path.isfile(template_path):
        event_service.load_template(template_path)
    
    context = {}
    if event_service.real_events:
        context['events'] = zip_longest(event_service.real_events, event_service.template_events)
    return render(request, 'app/index.html', context)

def upload_template_events(request):
    if request.method == 'POST':
        save_template_file(request.FILES['template_file'])
    return HttpResponseRedirect('/')

def upload_real_events(request):
    if request.method=='POST':
        #event_service.load_real('app/static/sample-events.json')
        event_service.load_events_from_iwtm(request.POST['iw_ip'], request.POST['iw_token'], '1589364000')
    return HttpResponseRedirect('/') 

def list_real_events(request):

    iw_ip = request.GET.get('ip')
    token = request.GET.get('token')
    timestamp = request.GET.get('timestamp')

    result = {}
    if iw_ip and token and timestamp:
        result = event_service.load_events_from_iwtm(iw_ip, token, timestamp)
    else:
        result['message'] = 'Error: parameters not specified'
    return JsonResponse(result, safe=False, json_dumps_params={'indent': 4, 'ensure_ascii': False})

def compare_events(request):
    event_service.task_compare()
    context = {}
    context['tasks'] = event_service.tasks
    return render(request, 'app/results.html', context)

def save_template_file(file):
    with open('app/static/upload/template.csv', 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)

def sent_date_sorting(event):
    return datetime.datetime.strptime(event['SENT_DATE'], '%Y-%m-%d %H:%M:%S').timestamp()
