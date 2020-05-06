import datetime
import os.path
import json

from .models import Event
from .services import EventService
from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponseRedirect

event_service = EventService()
template_path = 'app/static/upload/template.csv'

def index(request):
    if request.method=='POST' and 'template' in request.POST:
        print('saving template')
        save_template_file(request.FILES['template_file'])
        return HttpResponseRedirect('/')

    if os.path.isfile(template_path):
        event_service.load_template(template_path)
    
    if request.method=='POST' and 'iw_ip' in request.POST:
        #event_service.load_real('app/static/sample-events.json')
        event_service.load_events_from_iwtm(request.POST['iw_ip'], request.POST['iw_token'])
        return HttpResponseRedirect('/') 
    
    context = {'template_events': event_service.template_events,
                'real_events': event_service.real_events}
    if event_service.deltas:
        context['real_events_diff'] = zip(event_service.real_events, event_service.deltas)
    return render(request, 'app/index.html', context)

def list_real_events(request):
    events = event_service.load_events_from_iwtm()
    json_pretty = json.dumps(events, indent=4, ensure_ascii=False)
    return HttpResponse(json_pretty, content_type="application/json; charset=utf-8")

def compare_events(request):
    event_service.compare()
    return HttpResponseRedirect('/')

def add_delta(request):
    print(request.GET['id'])
    return HttpResponseRedirect('/')

def remove_delta(request):
    event_service.remove_delta(request.GET['id'])
    return HttpResponseRedirect('/')

def save_template_file(file):
    with open('app/static/upload/template.csv', 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)

def test(request):
    event = Event('cat.jpg', 'Sales', 'HR', ['Policy 3, Policy 5'], 'Allowed', 'Low', 'Tag 1')
    context = {'event': event}
    event_service = EventService()
    real_events = event_service.get_real('app/static/sample-events.json')
    event_service.find_all_by_id(real_events, 'catoo.jpg', 'IT', 'External')
    return render(request, 'app/index.html', context)

def sent_date_sorting(event):
    return datetime.datetime.strptime(event['SENT_DATE'], '%Y-%m-%d %H:%M:%S').timestamp()
