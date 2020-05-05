import datetime
import os.path

from .models import Event
from .services import EventService
from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponseRedirect

# Шаблонные события - просто выводим в таблицу
# Реальные события - преобразовать к упрощенному виду
# Результат сравнения - дельта (двумерный или одномерный массив)
# Порядок событий в двух таблицах должен совпадать
# Проблема: одному шаблонному событию может соответствовать несколько реальных
# В этом случае политика неправильная в том случае, если все события неверные
 
def index(request):
    if request.method=='POST' and 'template' in request.POST:
        print('saving template')
        save_template_file(request.FILES['template_file'])

    if request.method=='POST' and 'iw_ip' in request.POST:
        print('loading events from iw')
    
    event_service = EventService()
    template_events = []
    template_path = 'app/static/upload/template.csv'
    real_events = event_service.get_real('app/static/sample-events.json')
    
    #real_events = sorted(real_events, key=sent_date_sorting)
    deltas = []
    if os.path.isfile(template_path):
        template_events = event_service.get_template(template_path)
        real_events = event_service.align_real(real_events, template_events)
        deltas = event_service.compare(template_events, real_events)
    
    context = {'template_events': template_events,
                'real_events_with_deltas': zip(real_events, deltas)}
    return render(request, 'app/test.html', context)

def add_delta(request):
    print(request.GET['id'])
    return HttpResponseRedirect('/')

def remove_delta(request):
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
    return render(request, 'app/test.html', context)

def sent_date_sorting(event):
    return datetime.datetime.strptime(event['SENT_DATE'], '%Y-%m-%d %H:%M:%S').timestamp()
