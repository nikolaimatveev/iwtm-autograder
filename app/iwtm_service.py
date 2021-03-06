import requests
import json
from . import utils
from urllib.parse import unquote

'''
Класс для выгрузки и обработки данных из IWTM    
'''
class IWTMService:
    
    def get_parsed_events(self, ip, auth_cookies, date_and_time, unique_senders, unique_recipients):
        '''
        Загрузка и обработка событий за указанный период date_and_time
        '''
        token = self.get_token(ip, auth_cookies)
        self.check_ldap_status(ip, auth_cookies)
        events = self.load_events(ip, token, date_and_time)
        persons = self.get_persons(ip, token)
        groups = self.get_groups(ip, token)
        events = self.parse_events(events, persons, groups, unique_senders, unique_recipients)
        return events

    def isAuthCookiesValid(self, ip, auth_cookies):
        '''
        Проверка, что сессия еще не истекла и куки авторизации валидны
        '''
        url = 'https://' + ip + '/api/user/check'
        response = requests.get(url, cookies=auth_cookies, verify=False)
        data = response.json()
        if response.status_code == 200 and data['state'] == 'data':
            return True
        else:
            return False
    
    def login(self, ip, username, password):
        '''
        Вход в TM, возвращает куки авторизации
        '''
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
        response.raise_for_status()
        return response.cookies
    
    def get_token(self, ip, auth_cookies):
        url = 'https://' + ip + '/api/plugin?merge_with[]=tokens'
        response = requests.get(url, cookies=auth_cookies, verify=False)
        data = response.json()
        for plugin in data['data']:
            #TODO Посмотреть как можно избавиться от сравнения с hard-coded именем 
            if plugin['DISPLAY_NAME'] == 'DataExport plugin':
                return plugin['tokens'][0]['USERNAME']
        raise RuntimeError('Plugin not found or named incorrect. Correct name: DataExport plugin')
    
    def load_events(self, ip, token, date_and_time):
        url = 'https://' + ip + '/xapi/event'
        headers = self.get_request_headers(token)
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

    def get_request_headers(self, token):
        headers = {}
        headers['X-API-Version'] = '1.2'
        headers['X-API-CompanyId'] = 'GUAP'
        headers['X-API-ImporterName'] = 'GUAP'
        headers['X-API-Auth-Token'] = token
        return headers

    def parse_events(self, events, persons, groups, unique_senders, unique_recipients):
        parsed_events = []
        for event in events:
            parsed_event = {}
            parsed_event['id'] = event['OBJECT_ID']
            parsed_event['capture_date'] = event['CAPTURE_DATE']
            parsed_event['filename'] = event['attachments'][0]['FILE_NAME']
            
            sender_id = event['senders'][0][0]['PARTICIPANT_ID']
            parsed_event['sender'] = self.get_person_group(sender_id, persons, groups, unique_senders)
            
            if event['recipients']:
                recipient_id = event['recipients'][0][0]['PARTICIPANT_ID']
                parsed_event['recipient'] = self.get_person_group(recipient_id, persons, groups, unique_recipients)
            else:
                parsed_event['recipient'] = 'External'
            
            parsed_event['policies'] = utils.simplify_json_array(event['policies'])
            parsed_event['protected_objects'] = utils.simplify_json_array(event['protected_documents'])
            parsed_event['tags'] = utils.simplify_json_array(event['tags'])
            parsed_event['verdict'] = event['VERDICT']
            parsed_event['violation_level'] = event['VIOLATION_LEVEL']
            parsed_events.append(parsed_event)
        return parsed_events

    def get_person_group(self, person_id, persons, groups, allowed_groups):
        empty_result = ''
        person = self.find_person_by_id(persons, person_id)
        for person_group in person['p2g']:
            group = self.find_group_by_id(groups, person_group['PARENT_GROUP_ID'])
            if group['DISPLAY_NAME'] in allowed_groups:
                return group['DISPLAY_NAME']
        return empty_result

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

    def get_persons(self, ip, token):
        url = 'https://' + ip + '/xapi/person'
        headers = self.get_request_headers(token)
        params = {}
        params['start'] = 0
        params['limit'] = 1000
        params['with[]'] = 'p2g'
        response = requests.get(url, headers=headers, params=params, verify=False)
        data = response.json()
        return data['data']
    
    def get_groups(self, ip, token):
        url = 'https://' + ip + '/xapi/group'
        headers = self.get_request_headers(token)
        params = {}
        params['start'] = 0
        params['limit'] = 1000
        response = requests.get(url, headers=headers, params=params, verify=False)
        data = response.json()
        return data['data']

    def find_person_by_id(self, persons, person_id):
        empty_result = {}
        for person in persons:
            if person_id == person['PERSON_ID']:
                return person
        return empty_result

    def find_group_by_id(self, groups, group_id):
        empty_result = {}
        for group in groups:
            if group_id == group['GROUP_ID']:
                return group
        return empty_result

    def get_policies(self, ip, auth_cookies):
        url = 'https://' + ip + '/api/policy?sort[CREATE_DATE]=asc'
        response = requests.get(url, cookies=auth_cookies, verify=False)
        data = response.json()
        return data['data']
    
    def find_policy_by_name(self, policies, name):
        empty_result = {}
        for policy in policies:
            if name == policy['DISPLAY_NAME']:
                return policy
        return empty_result
    
    def get_tags_from_policy_transfer_rules(self, policy):
        tags = set()
        for rule in policy['rules']:
            if rule['TYPE'] == 'transfer':
                for action in rule['actions']:
                    if action['TYPE'] == 'TAG':
                        for tag in action['DATA']['VALUE']:
                            tags.add(tag['NAME'])
        return tags

    def get_highest_violation_level_from_policy_transfer_rules(self, policy):
        violation_level = 'No'
        violation_level_int = 0
        for rule in policy['rules']:
            if rule['TYPE'] == 'transfer':
                for action in rule['actions']:
                    if action['TYPE'] == 'VIOLATION':
                        level = action['DATA']['VALUE'].capitalize()
                        level_int = utils.get_int_representation_of_violation_level(level)
                        if level_int > violation_level_int:
                            violation_level_int = level_int
                            violation_level = level
        return violation_level
    
    def check_ldap_status(self, ip, auth_cookies):
        url = 'https://' + ip + '/api/adlibitum/server'
        response = requests.get(url, cookies=auth_cookies, verify=False)
        data = response.json()
        if data['state'] == 'data' and len(data['data']) == 1:
            sync_status = data['data'][0]['sync_description']
            if sync_status != 'success':
                raise RuntimeError('LDAP server not sync')
        else:
            raise RuntimeError('LDAP server not found')