import requests
from app.grader_service import GraderService
from app.iwtm_service import IWTMService
from django.http import HttpResponse, FileResponse
from wsgiref.util import FileWrapper
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

grader_service = GraderService(True)

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
    
    grader_service.save_template_file(template_file_path, template_file)
    try:
        mapped_events = grader_service.load_events(iwtm_ip,
                                    iwtm_login,
                                    iwtm_password,
                                    date_and_time, 
                                    template_file_path)
    except requests.exceptions.ConnectionError as e:
        return Response({'error': 'No connection to IWTM'}, status=status.HTTP_400_BAD_REQUEST)
    except requests.exceptions.HTTPError as e:
        error_message = ''
        status_code = e.response.status_code
        if status_code == 403:
            error_message = 'Invalid username or password'
        else:
            error_message = 'HTTP Error'
        return Response({'error': error_message}, status=status.HTTP_400_BAD_REQUEST)
    except RuntimeError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    participant = {}
    participant['ip'] = iwtm_ip
    participant['number'] = competitor_number
    participant['last_name'] = competitor_last_name
    participant['isChecked'] = False
    participant['check_mode'] = 'none'
    grader_service.save_participant(iwtm_ip, participant)
    grader_service.save_participant_result(iwtm_ip, mapped_events)
    return Response({'message': 'Success'}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def check_events(request):
    check_mode = request.data['check_mode']
    ip = request.data['ip']
    try:
        events = grader_service.find_participant_result_by_ip(ip)
    except RuntimeError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    result = []
    if check_mode == 'normal':
        print('normal mode')
        result = grader_service.check_events_normal_mode(events)
    else:
        print('max mode')
        result = grader_service.check_events_max_mode(events)

    grader_service.save_participant_result(ip, result)
    
    participant = grader_service.find_participant_by_ip(ip)
    participant['isChecked'] = True
    participant['check_mode'] = check_mode
    grader_service.save_participant(ip, participant)
    return Response(result)

@api_view(['GET'])
def get_participants(request):
    participants = grader_service.get_all_participants()
    return Response(participants)

@api_view(['GET'])
def get_participant(request, ip):
    participant = grader_service.find_participant_by_ip(ip)
    return Response(participant)

@api_view(['GET'])
def download_participant_result(request, ip):
    path = 'app/static/'
    locale = request.GET.get('locale')
    filename = 'result-' + ip.replace('.', '-') + '.xlsx'
    result = grader_service.find_participant_result_by_ip(ip)
    grader_service.export_participant_result(result, path + filename, locale)
    result_file = open(path + filename, 'rb')
    response = HttpResponse(result_file, content_type='application/**')
    response['Content-Disposition'] = 'attachment; filename=' + filename
    result_file.close()
    return response

@api_view(['GET'])
def get_participant_result(request, ip):
    result = grader_service.find_participant_result_by_ip(ip)
    return Response(result)

@api_view(['GET'])
def check_testing(request):
    iwtm_service = IWTMService(True)
    filename = 'app/static/template_events.xlsx'
    username = 'officer'
    password = 'xxXX1234'
    date_and_time = '2020-06-24-18-30'
    iwtm_ip = '10.228.6.236:17443'
    auth_cookies = iwtm_service.login(iwtm_ip, username, password)
    token = iwtm_service.get_token(iwtm_ip, auth_cookies)
    events = iwtm_service.load_events(iwtm_ip, token, date_and_time)
    return Response(events)