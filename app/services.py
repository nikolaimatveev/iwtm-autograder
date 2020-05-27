import csv
import os
import json
import urllib.parse
import urllib.request
import ssl
from openpyxl import Workbook
from openpyxl.styles import Border, Side, Alignment
from openpyxl.utils import get_column_letter

class EventService:

    def __init__(self):
        self.deltas = []
        self.template_events = []
        self.real_events = []
        self.task_numbers = []

    def load_template(self, filename):
        self.template_events = []
        with open(filename, encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter=';')
            for row in reader:
                event = {}
                event['task_number'] = row['task_number']
                event['filename'] = row['filename']
                event['sender'] = row['sender']
                event['recipient'] = row['recipient']
                event['policies'] = row['policies'].split(',')
                event['protected_documents'] = row['protected_documents'].split(',')
                event['verdict'] = row['verdict']
                event['violation_level'] = row['violation_level']
                event['tags'] = row['tags'].split(',')
                if event['task_number'] not in self.task_numbers:
                    self.task_numbers.append(event['task_number'])
                self.template_events.append(event)
        return self.template_events
    
    def load_real(self, filename):
        data = []
        with open(filename, encoding='utf-8') as json_file:
            data = json.load(json_file)
        self.real_events = data['data']
        self.fix_real()
    
    def fix_real(self):
        for event in self.real_events:
            subject = json.loads(event['PREVIEW_DATA'])['subject'].split(', ')
            event_sender = subject[0].split(':')[1].strip()
            event_recipient = subject[1].split(':')[1].strip()
            event_filename = subject[2].split(':')[1].strip()
            policies_names = []
            if not event['policies']:
                policies_names.append('No')
            else:
                for policy in event['policies']:
                    policies_names.append(policy['DISPLAY_NAME'])
            event['policies'] = policies_names
            document_names = []
            if not event['protected_documents']:
                document_names.append('No')
            else:
                for doc in event['protected_documents']:
                    document_names.append(doc['DISPLAY_NAME'])
            event['protected_documents'] = document_names
            event['sender'] = event_sender
            event['recipient'] = event_recipient
            event['filename'] = event_filename

    # Почему в событии появился объект защиты, который не указан в политике?
    # protected_documents - объекты защиты
    def load_events_from_iwtm(self, ip, token, timestamp):
        #token = '1bs23q0mf47941ctode8'
        HTTP_HEADERS = {'X-API-Version': '1.2',
                        'X-API-CompanyId': 'GUAP',
                        'X-API-ImporterName': 'GUAP',
                        'X-API-Auth-Token': token}
        #string_timestamp = '1588759200'
        url = 'https://' + ip + '/xapi/event?with[protected_documents]&with[policies]&with[protected_catalogs]&with[tags]&with[senders]&with[recipients]&with[recipients_keys]&with[senders_keys]&start=0&filter[date][from]=' + timestamp
        req = urllib.request.Request(url, headers=HTTP_HEADERS)
        data = []
        with urllib.request.urlopen(req, context=ssl._create_unverified_context()) as response:
            the_page = response.read()
            data = json.loads(the_page)
        self.real_events = data['data']
        self.fix_real()
        return self.real_events

    def find_by_id(self, filename, sender, recipient):
        found_event = {}
        for event in self.real_events:
            if event['filename'] == filename and event['sender'] == sender and event['recipient'] == recipient:
                found_event = event
                return found_event
        return found_event

    def align_real(self):
        result = []
        for event in self.template_events:
            found_event = self.find_by_id(event['filename'], event['sender'], event['recipient'])
            found_event['task_number'] = event['task_number']
            result.append(found_event)
        self.real_events = result
    
    def align_template(template_events, real_events):
        result = []
        for event in template_events:
            found_events = self.find_all_by_id(event.filename, event.sender, event.recipient)
            result.append(event)
            empty_event = {}
            empty_event['filename'] = 'null'
            for _ in found_events:
                result.append(empty_event)
        return result
    
    def get_events_by_task_number(self, events, task_number):
        result = []
        for event in events:
            if event['task_number'] == task_number:
                result.append(event)
        return result

    def create_task_list(self):
        tasks = []
        for number in self.task_numbers:
            task = {}
            task_real_events = self.get_events_by_task_number(self.real_events, number)
            task_template_events = self.get_events_by_task_number(self.template_events, number)
            task['events'] = zip(task_real_events, task_template_events)
            task['real_events'] = task_real_events
            task['template_events'] = task_template_events
            task['number'] = number
            tasks.append(task)
        return tasks

    def task_compare(self):
        self.deltas = []
        self.align_real()
        self.tasks = self.create_task_list()
        for task in self.tasks:
            task_deltas = []
            task_wrong_tags = 0
            task_wrong_policies = 0
            task_missing_policies = 0
            task_wrong_documents = 0
            task_missing_documents = 0
            task_total_errors = 0
            
            for real_event, template_event in task['events']:
                event_delta = {}
                
                diff_policies = []
                wrong_policy_count = 0
                missing_policy_count = 0

                for policy in template_event['policies']:
                    if policy not in real_event['policies']:
                        missing_policy_count += 1             
                
                for policy in real_event['policies']:
                    if policy not in template_event['policies']:
                        diff_policies.append(policy)
                        wrong_policy_count += 1
                
                if wrong_policy_count >= missing_policy_count:
                    wrong_policy_count -= missing_policy_count
                else:
                    wrong_policy_count = 0
                
                event_delta['policies'] = diff_policies
                event_delta['wrong_policies'] = wrong_policy_count
                event_delta['missing_policies'] = missing_policy_count

                diff_documents = []                
                wrong_document_count = 0
                missing_document_count = 0

                for document in template_event['protected_documents']:
                    if document not in real_event['protected_documents']:
                        missing_document_count += 1  

                for document in real_event['protected_documents']:
                    if document not in template_event['protected_documents']:
                        diff_documents.append(document)
                        wrong_document_count += 1
                
                if wrong_document_count >= missing_document_count:
                    wrong_document_count -= missing_document_count
                else:
                    wrong_document_count = 0

                event_delta['protected_documents'] = diff_documents
                event_delta['wrong_documents'] = wrong_document_count
                event_delta['missing_documents'] = missing_document_count

                diff_tags = []
                if not real_event['tags']:
                    real_event['tags'] = [{'DISPLAY_NAME': 'No'}]

                wrong_tag_count = 0
                for tag in real_event['tags']:
                    if tag['DISPLAY_NAME'] not in template_event['tags']:
                        wrong_tag_count += 1
                        diff_tags.append(tag['DISPLAY_NAME'])
                event_delta['tags'] = diff_tags
                event_delta['wrong_tags'] = wrong_tag_count

                event_delta['verdict'] = (
                    real_event['VERDICT']
                    if template_event['verdict'] != real_event['VERDICT']
                    else 'ok'
                )

                event_delta['violation_level'] = (
                    real_event['VIOLATION_LEVEL']
                    if template_event['violation_level'] != real_event['VIOLATION_LEVEL']
                    else 'ok'
                )
                task_wrong_tags += event_delta['wrong_tags']
                task_wrong_policies += event_delta['wrong_policies']
                task_missing_policies += event_delta['missing_policies']
                task_wrong_documents += event_delta['wrong_documents']
                task_missing_documents += event_delta['missing_documents']
                task_deltas.append(event_delta)
            task['events_deltas'] = zip(task['real_events'], task['template_events'], task_deltas)
            task['wrong_tags'] = task_wrong_tags
            task['wrong_policies'] = task_wrong_policies
            task['missing_policies'] = task_missing_policies
            task['wrong_documents'] = task_wrong_documents
            task['missing_documents'] = task_missing_documents
            task['total_errors'] = (task_wrong_tags + task_wrong_policies + 
                                    task_missing_policies + task_wrong_documents + 
                                    task_missing_documents)
        self.save_results()
    
    def save_results(self):
        start_x = 3
        start_y = 3
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                            top=Side(style='thin'), bottom=Side(style='thin'))
        cell_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        book = Workbook()
        sheet = book.active
        x_idx = start_x
        y_idx = start_y
        column_headers = ['Ложные теги', 'Ложные политики', 'Отсутствующие политики', 
                        'Ложные объекты', 'Отсутствующие объекты', 'Итого недочетов']
        
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
        
        for task in self.tasks:
            x_idx += 1
            y_idx = start_y
            sheet.cell(x_idx, y_idx).value = 'Политика №' + task['number']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = 'Задание №' + task['number']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = task['wrong_tags']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = task['wrong_policies']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = task['missing_policies']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = task['wrong_documents']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = task['missing_documents']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = task['total_errors']
            sheet.cell(x_idx, y_idx).border = thin_border
        
        book.save("app/static/results.xlsx")