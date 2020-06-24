import csv
import os
import json
import urllib.parse
import urllib.request
import ssl
from openpyxl import Workbook
from openpyxl.styles import Border, Side, Alignment
from openpyxl.utils import get_column_letter
import blowfish
import base64
import requests
from datetime import datetime, timezone
from time import gmtime, strftime
from urllib.parse import unquote

class EventService:
    def __init__(self, debug_mode):
        self.debug_mode = debug_mode
        # todo: store in db
        self.participant_results = {}
        self.participants = {}
        self.auth_cookies = []

    def load_grouped_events(self, iwtm_ip, iwtm_login, iwtm_password, 
                            date_and_time, template_file_path):
        template_events = self.load_template_events(template_file_path)
        iwtm_events = []
        if self.debug_mode:
            iwtm_events_file = 'app/static/sample-events.json'
            iwtm_events = self.load_iwtm_events_from_file(iwtm_events_file)
        else:
            if not self.isAuthCookiesValid(iwtm_ip, self.auth_cookies):
                self.auth_cookies = self.login_to_iwtm(iwtm_ip, iwtm_login, iwtm_password)
            token = self.get_token_from_iwtm(iwtm_ip, self.auth_cookies)
            iwtm_events = self.load_events_from_iwtm(iwtm_ip, token, date_and_time)
        
        iwtm_events = self.parse_iwtm_events(iwtm_events)
        mapped_events = self.get_mapped_events_one_to_one(template_events, iwtm_events)
        grouped_events = self.get_grouped_events(mapped_events)
        self.save_participant_result(iwtm_ip, grouped_events)
        return True

    def isAuthCookiesValid(self, iwtm_ip, auth_cookies):
        url = 'https://' + iwtm_ip + '/api/user/check'
        response = requests.get(url, cookies=auth_cookies, verify=False)
        data = response.json()
        if response.status_code == 200 and data['state'] == 'data':
            return True
        else:
            return False

    def save_participant(self, ip, participant_info):
        self.participants[ip] = participant_info

    def save_participant_result(self, ip, result):
        self.participant_results[ip] = result

    def get_participants(self):
        return self.participants.values()

    def get_participant_by_ip(self, ip):
        result = {}
        if ip in self.participants:
            result = self.participants[ip]
        return result

    def get_participant_result(self, ip):
        result = {}
        if ip in self.participant_results:
            result = self.participant_results[ip]
        return result
    
    def save_template_file(self, path, file):
        with open(path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

    def load_template_events(self, filename):
        template_events = []
        with open(filename, encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter=';')
            for row in reader:
                event = {}
                event['task_number'] = row['task_number']
                event['filename'] = row['filename']
                event['sender'] = row['sender']
                event['recipient'] = row['recipient']
                if row['policies']:
                    event['policies'] = row['policies'].split(',')
                else:
                    event['policies'] = []     
                if row['protected_documents']:
                    event['protected_documents'] = row['protected_documents'].split(',')
                else:
                    event['protected_documents'] = []
                event['verdict'] = row['verdict']
                event['violation_level'] = row['violation_level']
                if row['tags']:
                    event['tags'] = row['tags'].split(',')
                else:
                    event['tags'] = []
                template_events.append(event)
        return template_events
    
    def load_iwtm_events_from_file(self, filename):
        data = []
        with open(filename, encoding='utf-8') as json_file:
            data = json.load(json_file)
        return data['data']
    
    def get_token_from_iwtm(self, iwtm_ip, auth_cookies):
        response = requests.get('https://' + iwtm_ip + '/api/plugin?merge_with[]=tokens',
                            cookies=auth_cookies, verify=False)
        data = response.json()
        token = ''
        for plugin in data['data']:
            if plugin['DISPLAY_NAME'] == 'DataExport plugin':
                token = plugin['tokens'][0]['USERNAME']
        return token

    def get_object_types(self, iwtm_ip, auth_cookies, catalog_id):
        API_ROOT = 'https://' + iwtm_ip + '/api/'
        url = API_ROOT + 'protectedDocument?start=0&limit=50&filter[catalog.CATALOG_ID]=' + catalog_id
        
        url_alt = API_ROOT + 'protectedDocument?start=0&limit=100&filter%5Bcatalog.CATALOG_ID%5D=EC6965EA7D1B0EE750E47DF2040BF4E800000000&filter%5BDOCUMENT_ID%5D=4F61ECD2791CC87FA4907F21C4FEAAC000000000'
        
        response = requests.get(url_alt, cookies=auth_cookies, verify=False)
        data = response.json()['data'][0]

        technology_types = set()
        
        for entry in data['entries_pool']:
            technology_type = entry['content']['TYPE']
            technology_types.add(technology_type)

        return technology_types

    def convert_datetime_to_timestamp(self, date_and_time):
        attr = date_and_time.split('-')
        dt = datetime(year=int(attr[0]), month=int(attr[1]), 
                      day=int(attr[2]), hour=int(attr[3]), minute=int(attr[4]))
        timestamp = dt.replace(tzinfo=timezone.utc).timestamp()
        return timestamp

    def load_events_from_iwtm(self, iwtm_ip, token, date_and_time):
        url = 'https://' + iwtm_ip + '/xapi/event'
        headers = {}
        headers['X-API-Version'] = '1.2'
        headers['X-API-CompanyId'] = 'GUAP'
        headers['X-API-ImporterName'] = 'GUAP'
        headers['X-API-Auth-Token'] = token
        params = {}
        params['start'] = 0
        timestamp = self.convert_datetime_to_timestamp(date_and_time)
        params['filter[date][from]'] = timestamp
        params['with[]'] = [
            'protected_documents', 'policies', 'protected_catalogs',
            'tags', 'senders', 'recipients',
            'senders_keys', 'recipients_keys'
            ]
        response = requests.get(url, headers=headers, params=params, verify=False)
        data = response.json()
        if data['meta']['totalCount'] == 0:
            raise RuntimeError('No events found for the specified time period')
        return data['data']

    def login_to_iwtm(self, iwtm_ip, username, password):    
        resp = requests.get('https://10.228.6.236:17443/api/user/check', verify=False)
        csrf_token = unquote(resp.cookies['YII_CSRF_TOKEN'])
    
        response = requests.get('https://10.228.6.236:17443/api/salt', 
                                cookies=resp.cookies, verify=False)
    
        response_json = response.json()
        salt = response_json['data']['salt']
        crypted_password = self.crypt_password(password, salt)
    
        data = {}
        data['username'] = username
        data['crypted_password'] = crypted_password

        headers = {}
        headers['x-csrf-token'] = csrf_token
    
        response = requests.post('https://10.228.6.236:17443/api/login',
                                json=data, cookies=resp.cookies, headers=headers, verify=False)
        return response.cookies
    
    def crypt_password(self, password, salt):
        key_bytes = salt.encode('utf-8')
        cipher = blowfish.Cipher(key_bytes)
        msg_bytes = password.encode('utf-8')
        
        block_size = 8
        padding_len = -len(msg_bytes) % block_size
        msg_bytes = msg_bytes.ljust(len(msg_bytes) + padding_len, b'\0')
        
        data_encrypted = b"".join(cipher.encrypt_ecb(msg_bytes))
        crypted_bytes = base64.b64encode(data_encrypted)
        crypted_base64 = crypted_bytes.decode('utf-8')
        return crypted_base64
    
    def parse_iwtm_events(self, events):
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
            parsed_event['policies'] = self.simplify_json_array(event['policies'])
            parsed_event['protected_documents'] = self.simplify_json_array(event['protected_documents'])
            parsed_event['tags'] = self.simplify_json_array(event['tags'])
            parsed_event['verdict'] = event['VERDICT']
            parsed_event['violation_level'] = event['VIOLATION_LEVEL']
            parsed_events.append(parsed_event)
        return parsed_events

    def get_mapped_events_one_to_one(self, template_events, iwtm_events):
        mapped_events = []
        for event in template_events:
            iwtm_event = self.find_event_by_id(iwtm_events, event['filename'], event['sender'], event['recipient'])
            mapped_event = iwtm_event
            mapped_event['template_event'] = event
            mapped_events.append(mapped_event)
        return mapped_events

    def find_event_by_id(self, events, filename, sender, recipient):
        found_event = {}
        for event in events:
            if event['filename'] == filename and event['sender'] == sender and event['recipient'] == recipient:
                found_event = event
                return found_event
        return found_event

    def simplify_json_array(self, json_array):
        result = []
        for item in json_array:
            result.append(item['DISPLAY_NAME'])
        return result
    
    def get_grouped_events(self, events):
        task_numbers = self.get_task_numbers(events)
        grouped_events = []
        for number in task_numbers:
            policy_events = {}
            policy_events['policy_number'] = number
            policy_events['events'] = self.get_events_by_task_number(events, number)
            policy_events['stats'] = {}
            grouped_events.append(policy_events)
        return grouped_events
    
    def get_task_numbers(self, events):
        task_numbers = []
        for event in events:
            task_number = event['template_event']['task_number']
            if task_number not in task_numbers:
                task_numbers.append(task_number)
        return task_numbers
    
    def get_events_by_task_number(self, events, task_number):
        result = []
        for event in events:
            if event['template_event']['task_number'] == task_number:
                result.append(event)
        return result

    def check_events_normal_mode(self, grouped_events):
        self.check_events_max_mode(grouped_events)
        for item in grouped_events:
            self.find_false_triggering_and_update_stats(item, grouped_events)
        return grouped_events

    def find_false_triggering_and_update_stats(self, item, grouped_events):
        policy = 'Политика ' + item['policy_number']
        protected_document = 'Задание ' + item['policy_number']
        for any_item in grouped_events:
            for policy_event in any_item['events']:
                template_event = policy_event['template_event']  
                if (policy in policy_event['policies'] and
                        policy not in template_event['policies']):
                    item['stats']['false_policies'] += 1
                    any_item['stats']['false_policies'] -= 1
                    item['stats']['false_tags'] += 1
                    any_item['stats']['false_tags'] -= 1
                    
                if (protected_document in policy_event['protected_documents'] and
                        protected_document not in template_event['protected_documents']):
                    item['stats']['false_documents'] += 1
                    any_item['stats']['false_documents'] -= 1

    def check_events_max_mode(self, grouped_events):
        for item in grouped_events:
            self.init_task_stats(item)
            self.check_events_one_to_one(item)
        return grouped_events

    def check_events_one_to_one(self, item):
        for task_event in item['events']:
            self.find_and_set_event_difference(task_event, task_event['template_event'])
            self.update_task_stats(item, task_event, task_event['template_event'])

    def init_task_stats(self, item):
        item['stats']['failed_policies'] = 0
        item['stats']['false_policies'] = 0
        item['stats']['failed_documents'] = 0
        item['stats']['false_documents'] = 0
        item['stats']['wrong_tags'] = 0
        item['stats']['false_tags'] = 0
        item['stats']['wrong_verdict'] = 0
        item['stats']['wrong_violation_level'] = 0

    def get_array_difference(self, first_array, second_array):
        diff = []
        for item in first_array:
            if item not in second_array:
                diff.append(item)
        return diff

    def find_and_set_event_difference(self, iwtm_event, template_event):
        failed_policies_diff = self.get_array_difference(template_event['policies'],
                                                         iwtm_event['policies'])
        false_policies_diff = self.get_array_difference(iwtm_event['policies'],
                                                            template_event['policies'])
        failed_documents_diff = self.get_array_difference(template_event['protected_documents'],
                                                              iwtm_event['protected_documents'])
        false_documents_diff = self.get_array_difference(iwtm_event['protected_documents'],
                                                             template_event['protected_documents'])
        failed_tags_diff = self.get_array_difference(template_event['tags'],
                                                  iwtm_event['tags'])
        false_tags_diff = self.get_array_difference(iwtm_event['tags'],
                                                        template_event['tags'])
        wrong_verdict_diff = ''
        if iwtm_event['verdict'] != template_event['verdict']:
            wrong_verdict_diff = iwtm_event['verdict']
            
        wrong_violation_level_diff = ''
        if iwtm_event['violation_level'] != template_event['violation_level']:
            wrong_violation_level_diff = iwtm_event['violation_level']
            
        iwtm_event['diff'] = {}
        template_event['diff'] = {}
        iwtm_event['diff']['policies'] = false_policies_diff
        template_event['diff']['policies'] = failed_policies_diff
        iwtm_event['diff']['protected_documents'] = false_documents_diff
        template_event['diff']['protected_documents'] = failed_documents_diff
        iwtm_event['diff']['tags'] = false_tags_diff
        template_event['diff']['tags'] = failed_tags_diff
        iwtm_event['diff']['verdict'] = wrong_verdict_diff
        iwtm_event['diff']['violation_level'] = wrong_violation_level_diff
    
    def update_task_stats(self, item, iwtm_event, template_event):
        item['stats']['failed_policies'] += len(template_event['diff']['policies'])
        item['stats']['false_policies'] += len(iwtm_event['diff']['policies'])
        item['stats']['failed_documents'] += len(template_event['diff']['protected_documents'])
        item['stats']['false_documents'] += len(iwtm_event['diff']['protected_documents'])
        item['stats']['wrong_tags'] += len(template_event['diff']['tags'])
        item['stats']['false_tags'] += len(iwtm_event['diff']['tags'])
        if iwtm_event['diff']['verdict']:
            item['stats']['wrong_verdict'] += 1
        if iwtm_event['diff']['violation_level']:
            item['stats']['wrong_violation_level'] += 1
    
    def export_participant_result(self, result, filename):
        start_x = 3
        start_y = 3
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                            top=Side(style='thin'), bottom=Side(style='thin'))
        cell_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        book = Workbook()
        sheet = book.active
        x_idx = start_x
        y_idx = start_y
        column_headers = ['Ложные политики', 'Несработавшие политики', 
                        'Ложные объекты', 'Несработавшие объекты', 
                        'Ложные теги', 'Неправильные теги', 'Неправильные вердикты',
                        'Неправильные уровни нарушения', 'Итого недочетов']
        
        sheet.cell(x_idx, y_idx).border = thin_border
        sheet.column_dimensions[get_column_letter(y_idx)].width = 15
        y_idx += 1
        sheet.cell(x_idx, y_idx).border = thin_border
        sheet.column_dimensions[get_column_letter(y_idx)].width = 15
        
        y_idx += 1
        for header in column_headers:
            sheet.cell(x_idx, y_idx).value = header
            sheet.cell(x_idx, y_idx).border = thin_border
            sheet.cell(x_idx, y_idx).alignment = cell_align
            sheet.column_dimensions[get_column_letter(y_idx)].width = 15
            y_idx += 1
        
        for item in result:
            x_idx += 1
            y_idx = start_y
            policy = 'Политика №' + item['policy_number']
            task = 'Задание №' + item['policy_number']
            total_errors = (item['stats']['false_policies'] + item['stats']['failed_policies'] +
                            item['stats']['false_documents'] + item['stats']['failed_documents'] +
                            item['stats']['false_tags'] + item['stats']['wrong_tags'] +
                            item['stats']['wrong_verdict'] + item['stats']['wrong_violation_level'])
            sheet.cell(x_idx, y_idx).value = policy
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = task
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = item['stats']['false_policies']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = item['stats']['failed_policies']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = item['stats']['false_documents']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = item['stats']['failed_documents']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = item['stats']['false_tags']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = item['stats']['wrong_tags']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = item['stats']['wrong_verdict']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = item['stats']['wrong_violation_level']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = total_errors
            sheet.cell(x_idx, y_idx).border = thin_border
        
        
        column_headers_doc = ['Ложные объекты', 'Несработавшие объекты', 'Итого недочетов']
        y_idx = start_y
        x_idx += 3
        sheet.cell(x_idx, y_idx).border = thin_border
        sheet.column_dimensions[get_column_letter(y_idx)].width = 20
        y_idx += 1
        sheet.cell(x_idx, y_idx).border = thin_border
        sheet.column_dimensions[get_column_letter(y_idx)].width = 15
        y_idx += 1
        
        for header in column_headers_doc:
            sheet.cell(x_idx, y_idx).value = header
            sheet.cell(x_idx, y_idx).border = thin_border
            sheet.cell(x_idx, y_idx).alignment = cell_align
            sheet.column_dimensions[get_column_letter(y_idx)].width = 15
            y_idx += 1

        for item in result:
            x_idx += 1
            y_idx = start_y
            protected_document = 'Объект защиты №' + item['policy_number']
            task = 'Задание №' + item['policy_number']
            total_errors = item['stats']['false_documents'] + item['stats']['failed_documents']
            sheet.cell(x_idx, y_idx).value = protected_document
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = task
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = item['stats']['false_documents']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = item['stats']['failed_documents']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = total_errors
            sheet.cell(x_idx, y_idx).border = thin_border
        book.save(filename)