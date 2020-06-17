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

@api_view(['GET'])
def check_events(request):
    print('todo')
    comment = Comment(email='leila@example.com', content='check events')
    serializer = CommentSerializer(comment)
    return Response(serializer.data)

@api_view(['GET'])
def get_participant_ip_list(request):
    ip_list = event_service.get_participant_ip_list()
    return Response(ip_list)

@api_view(['GET'])
def download_participant_results(request, ip):
    result = {}
    result['participant'] = ip
    return Response(result)

@api_view(['GET'])
def get_participant_results(request, ip):
    result = event_service.get_participant_result(ip)
    return Response(result)