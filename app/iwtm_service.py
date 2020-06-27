import requests
import json
from . import utils
from urllib.parse import unquote

class IWTMService:
    def __init__(self, debug_mode):
        self.debug_mode = debug_mode
    
    def get_parsed_events(self, ip, auth_cookies, date_and_time):
        token = self.get_token(ip, auth_cookies)
        events = self.load_events(ip, token, date_and_time)
        events = self.parse_events(events, ip, auth_cookies)
        return events

    def isAuthCookiesValid(self, ip, auth_cookies):
        url = 'https://' + ip + '/api/user/check'
        response = requests.get(url, cookies=auth_cookies, verify=False)
        data = response.json()
        if response.status_code == 200 and data['state'] == 'data':
            return True
        else:
            return False
    
    def login(self, ip, username, password):
        api_root = 'https://' + ip + '/api/'
        resp = requests.get(api_root + 'user/check', verify=False)
        csrf_token = unquote(resp.cookies['YII_CSRF_TOKEN'])
    
        response = requests.get(api_root + 'salt', 
                                cookies=resp.cookies, verify=False)
    
        response_json = response.json()
        salt = response_json['data']['salt']
        crypted_password = utils.crypt_password(password, salt)
    
        data = {}
        data['username'] = username
        data['crypted_password'] = crypted_password

        headers = {}
        headers['x-csrf-token'] = csrf_token
    
        response = requests.post(api_root + 'login',
                                json=data, cookies=resp.cookies, 
                                headers=headers, verify=False)
        return response.cookies
    
    def get_token(self, ip, auth_cookies):
        url = 'https://' + ip + '/api/plugin?merge_with[]=tokens'
        response = requests.get(url, cookies=auth_cookies, verify=False)
        data = response.json()
        token = ''
        for plugin in data['data']:
            if plugin['DISPLAY_NAME'] == 'DataExport plugin':
                token = plugin['tokens'][0]['USERNAME']
        return token
    
    def load_events(self, ip, token, date_and_time):
        url = 'https://' + ip + '/xapi/event'
        headers = {}
        headers['X-API-Version'] = '1.2'
        headers['X-API-CompanyId'] = 'GUAP'
        headers['X-API-ImporterName'] = 'GUAP'
        headers['X-API-Auth-Token'] = token
        params = {}
        params['start'] = 0
        timestamp = utils.convert_datetime_to_timestamp(date_and_time)
        params['filter[date][from]'] = timestamp
        params['with[]'] = [
            'protected_documents', 'policies', 'protected_catalogs',
            'tags', 'senders', 'recipients',
            'senders_keys', 'recipients_keys',
            'perimeters', 'attachments']
        response = requests.get(url, headers=headers, params=params, verify=False)
        data = response.json()
        if data['meta']['totalCount'] == 0:
            raise RuntimeError('No events found for the specified time period')
        return data['data']

    def parse_events(self, events, ip, auth_cookies):
        parsed_events = []
        for event in events:
            parsed_event = {}
            parsed_event['id'] = event['OBJECT_ID']
            parsed_event['capture_date'] = event['CAPTURE_DATE']
            subject = json.loads(event['PREVIEW_DATA'])['subject'].split(', ')
            event_sender = subject[0].split(':')[1].strip()
            event_recipient = subject[1].split(':')[1].strip()
            event_filename = subject[2].split(':')[1].strip()
            parsed_event['sender'] = event_sender
            parsed_event['recipient'] = event_recipient
            parsed_event['filename'] = event_filename
            parsed_event['policies'] = utils.simplify_json_array(event['policies'])
            parsed_event['protected_objects'] = utils.simplify_json_array(event['protected_documents'])
            parsed_event['tags'] = utils.simplify_json_array(event['tags'])
            parsed_event['verdict'] = event['VERDICT']
            parsed_event['violation_level'] = event['VIOLATION_LEVEL']
            parsed_events.append(parsed_event)
        return parsed_events

    def get_protected_objects(self, ip, auth_cookies):
        url = 'https://' + ip + '/api/protectedDocument?start=0&limit=100'
        response = requests.get(url, cookies=auth_cookies, verify=False)
        data = response.json()
        return data['data']

    def set_object_technologies(self, events, protected_objects):
        for item in events:
            protected_object_name = item['protected_object']
            technologies = []
            if protected_object_name:
                found_protected_objects = self.find_protected_object_by_name(protected_objects, protected_object_name)
                technologies = self.get_protected_object_technologies(found_protected_objects)
            item['protected_object_technologies'] = technologies

    def find_protected_object_by_name(self, protected_objects, name):
        found_objects = []
        for protected_object in protected_objects:
            if name in protected_object['DISPLAY_NAME']:
                found_objects.append(protected_object)
        return found_objects
    
    def get_protected_object_technologies(self, protected_objects):
        technologies = set()
        for protected_object in protected_objects:
            for entry in protected_object['entries_pool']:
                if entry['ENTRY_TYPE'] == 'text_object':
                    technologies.add(entry['ENTRY_TYPE'])
                else:
                    technology = entry['content']['TYPE']
                    technologies.add(technology)
        return technologies