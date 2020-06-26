from app.models import Event, Comment
from app.serializers import CommentSerializer
from app.services import EventService

from django.http import HttpResponse, FileResponse
from wsgiref.util import FileWrapper

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests
import os
import io
import datetime

event_service = EventService(debug_mode=False)

@api_view(['POST'])
def load_events(request):
    #TODO: validate input params
    competitor_number = request.POST.get('competitor_number')
    competitor_last_name = request.POST.get('competitor_last_name')
    iwtm_ip = request.POST.get('iwtm_ip')
    iwtm_login = request.POST.get('iwtm_login')
    iwtm_password = request.POST.get('iwtm_password')
    date_and_time = request.POST.get('date_and_time')
    template_file = request.FILES.get('template_file')
    if (not competitor_number or not competitor_last_name or
            not iwtm_ip or not iwtm_login or not iwtm_password or
            not date_and_time or not template_file):
        return Response({'error': 'All fields is required'}, status=status.HTTP_400_BAD_REQUEST)
    #if event_service.get_participant_by_ip(iwtm_ip):
    #    return Response({'error': 'Competitor already exists'}, status=status.HTTP_400_BAD_REQUEST)
    template_file_path = 'app/static/upload/' + template_file.name
    print(iwtm_ip, iwtm_login, date_and_time, template_file)
    event_service.save_template_file(template_file_path, template_file)
    try:
        event_service.load_events(iwtm_ip,
                                    iwtm_login,
                                    iwtm_password,
                                    date_and_time, 
                                    template_file_path)
    except RuntimeError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    participant = {}
    participant['ip'] = iwtm_ip
    participant['number'] = competitor_number
    participant['last_name'] = competitor_last_name
    participant['isChecked'] = False
    participant['check_mode'] = 'none'
    event_service.save_participant(iwtm_ip, participant)
    return Response({'message': 'Success'}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def check_events(request):
    check_mode = request.data['check_mode']
    ip = request.data['ip']
    events = event_service.get_participant_result(ip)
    result = []
    if check_mode == 'normal':
        print('normal mode')
        result = event_service.check_events_normal_mode(events)
    else:
        print('max mode')
        result = event_service.check_events_max_mode(events)

    event_service.save_participant_result(ip, result)
    
    participant = event_service.get_participant_by_ip(ip)
    participant['isChecked'] = True
    participant['check_mode'] = check_mode
    event_service.save_participant(ip, participant)
    return Response(result)

@api_view(['GET'])
def get_participants(request):
    participants = event_service.get_participants()
    return Response(participants)

@api_view(['GET'])
def get_participant(request, ip):
    result = event_service.get_participant_by_ip(ip)
    return Response(result)

@api_view(['GET'])
def download_participant_result(request, ip):
    path = 'app/static/'
    filename = 'result-' + ip.replace('.', '-') + '.xlsx'
    result = event_service.get_participant_result(ip)
    event_service.export_participant_result(result, path + filename)
    result_file = io.open(path + filename, 'rb')
    response = HttpResponse(result_file, content_type='application/**')
    response['Content-Disposition'] = 'attachment; filename=' + filename
    return response

@api_view(['GET'])
def get_participant_result(request, ip):
    result = event_service.get_participant_result(ip)
    return Response(result)

@api_view(['GET'])
def check_testing(request):
    filename = 'app/static/template_events.xlsx'
    iwtm_login = 'officer'
    iwtm_password = 'xxXX1234'
    date_and_time = '2020-06-24-18-30'
    iwtm_ip = '10.228.6.236:17443'
    auth_cookies = event_service.login_to_iwtm(iwtm_ip, iwtm_login, iwtm_password)
    token = event_service.get_token_from_iwtm(iwtm_ip, auth_cookies)
    iwtm_events = event_service.load_events_from_iwtm(iwtm_ip, token, date_and_time)
    return Response(iwtm_events)
    #event_service.load_events(iwtm_ip,
    #                                  iwtm_login,
    #                                  iwtm_password,
    #                                  date_and_time, 
    #                                  filename)
    #events = event_service.get_participant_result(iwtm_ip)
    #return Response(events)
    #result = event_service.check_events_normal_mode(events)
    #path = 'app/static/'
    #filename = path + 'result-' + iwtm_ip.replace('.', '-') + '.xlsx'
    #event_service.export_participant_result(result, filename)
    #return Response(result)
    

@api_view(['GET'])
def login_to_iwtm(request):

    iwtm_ip = '10.228.6.236:17443'

    auth_cookies = event_service.login_to_iwtm(iwtm_ip, 'officer', 'xxXX1234')

    #response = requests.get('https://10.228.6.236:17443/api/protectedDocument?start=0&limit=10&filter%5Bcatalog.CATALOG_ID%5D=EF92807740E8698E38842817B3B9584700000000&sort%5BDISPLAY_NAME%5D=ASC&_=1592817531960',
    #                        cookies=auth_cookies, verify=False)
    
    #response = requests.get('https://10.228.6.236:17443/api/object?start=0&limit=1000&merge_with[]=objectContentFilenames&&sort[CAPTURE_DATE]=desc&filter[QUERY_ID]=1&_=1589364000',
    #                        cookies=auth_cookies, verify=False)
    
    #token = event_service.get_token_from_iwtm(iwtm_ip, auth_cookies)
    catalog_id = 'EF92807740E8698E38842817B3B9584700000000'
    technology_types = event_service.get_object_types(iwtm_ip, auth_cookies, catalog_id)
    return Response({'types': technology_types})

