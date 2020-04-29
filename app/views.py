import datetime

from .models import Event
from .services import EventService
from django.shortcuts import render
from django.http import HttpResponse

# Шаблонные события - просто выводим в таблицу
# Реальные события - преобразовать к упрощенному виду
# Результат сравнения - дельта (двумерный или одномерный массив)
# Порядок событий в двух таблицах должен совпадать
# Проблема: одному шаблонному событию может соответствовать несколько реальных
# В этом случае политика неправильная в том случае, если все события неверные

files = ['report.jpg', 'report.jpg', 'nepravilno.rtf', 
         'Wordlskilz.rtf', 'dogovor.doc', 'dogovor_direktor.doc',
         'dogovor_pechat.pdf', 'anketa.docx', 'anketa_pechat.pdf',
         'anketa.docx', 'anketa_pechat.pdf', 'promoall',
         'promotwo', 'promoall', 'promotwo',
         'catoo', 'catoo_reduced', 'catoo',
         'catoo_reduced', 'evil_routes', 'routes',
         'evil_routes', 'routes', 'candy',
         'candy', 'taxi', 'dbfull',
         'dbsmall', 'dbfull', 'dbsmall',
         'email', 'ne-email', 'strogo_konfidencialno',
         'konfidencialno', 'strogo_konfidencialno_m', 'Win1.zip']
 
def index(request):
    event_service = EventService()
    template_events = event_service.get_template('app/static/template.csv')
    real_events = event_service.get_real('app/static/sample-events.json')
    real_events = sorted(real_events, key=sent_date_sorting)
    deltas = event_service.compare(template_events, real_events)
    context = {'template_events': template_events,
                'real_events_with_deltas': zip(real_events, deltas, files)}
    return render(request, 'app/index.html', context)

def test(request):
    event = Event('cat.jpg', 'Sales', 'HR', ['Policy 3, Policy 5'], 'Allowed', 'Low', 'Tag 1')
    context = {'event': event}
    return render(request, 'app/test.html', context)

def sent_date_sorting(event):
    return datetime.datetime.strptime(event['SENT_DATE'], '%Y-%m-%d %H:%M:%S').timestamp()
