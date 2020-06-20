from app.models import Event, Comment
from app.serializers import CommentSerializer
from app.services import EventService

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

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
def download_participant_results(request, ip):
    result = {}
    result['participant'] = ip
    return Response(result)

@api_view(['GET'])
def get_participant_results(request, ip):
    result = event_service.get_participant_result(ip)
    return Response(result)

@api_view(['GET'])
def check_testing(request):
    iw_ip = '211'
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
    return Response(result)