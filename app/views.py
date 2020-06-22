from app.models import Event, Comment
from app.serializers import CommentSerializer
from app.services import EventService

from django.http import HttpResponse
from wsgiref.util import FileWrapper

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests

event_service = EventService(debug_mode=True)

@api_view(['POST'])
def load_events(request):
    #TODO: validate input params
    iw_ip = request.POST.get('ip')
    token = request.POST.get('token')
    date_and_time = request.POST.get('date-time')
    #check_mode = request.POST.get('check-mode')
    template_file = request.FILES['template-file']
    template_file_path = 'app/static/upload/' + template_file.name
    print(iw_ip, token, date_and_time, template_file)
    event_service.load_grouped_events(iw_ip,
                                      token,
                                      date_and_time, 
                                      template_file_path,
                                      template_file)
    return Response({'message': 'Success'}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def check_events(request):
    check_mode = request.data['check_mode']
    ip = request.data['ip']
    events = event_service.get_participant_result(ip)
    result = event_service.check_events_normal_mode(events)
    event_service.save_participant_result(ip, result)
    info = event_service.get_participant_info(ip)
    info['isChecked'] = True
    info['check_mode'] = check_mode
    event_service.save_participant_info(ip, info)
    return Response(result)

@api_view(['GET'])
def get_participant_ip_list(request):
    ip_list = event_service.get_participant_ip_list()
    return Response(ip_list)

@api_view(['GET'])
def get_participant_info(request, ip):
    result = event_service.get_participant_info(ip)
    return Response(result)

@api_view(['GET'])
def download_participant_result(request, ip):
    result = {}
    result['participant'] = ip
    return Response(result)

@api_view(['GET'])
def get_participant_result(request, ip):
    result = event_service.get_participant_result(ip)
    return Response(result)

@api_view(['GET'])
def check_testing(request):
    iw_ip = '192.168.108.102'
    token = 'abs'
    date_and_time = 'dasd'
    template_file_path = 'app/static/upload/template.csv'
    template_file = 'da'
    
    event_service.load_grouped_events(iw_ip,
                                      token,
                                      date_and_time, 
                                      template_file_path,
                                      template_file)
    events = event_service.get_participant_result(iw_ip)
    result = event_service.check_events_normal_mode(events)
    path = 'app/static/'
    filename = path + 'result-' + iw_ip.replace('.', '-') + '.xlsx'
    event_service.export_participant_result(result, filename)
    return Response(result)

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

