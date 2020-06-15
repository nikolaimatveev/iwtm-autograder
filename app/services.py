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

    def check_tasks_first_method(self):
        self.deltas = []
        self.align_real()
        self.tasks = self.create_task_list()
        for t1 in self.tasks:
            task_deltas = []
            policy = 'Политика ' + t1['number']
            protected_document = 'Задание ' + t1['number']
            wrong_policy_count = 0
            missing_policy_count = 0
            wrong_tag_count = 0
            wrong_document_count = 0
            missing_document_count = 0
            wrong_verdict_count = 0
            wrong_violation_level_count = 0
            self.tasks2 = self.create_task_list()
            for t2 in self.tasks2:
                for real_event, template_event in t2['events']:
                    if template_event['task_number'] != t1['number']:
                        if policy in real_event['policies'] and policy not in template_event['policies']:
                            wrong_policy_count += 1
                        if protected_document in real_event['protected_documents']:
                            wrong_document_count += 1
                    else:
                        #for p in real_event['policies']:
                        #    if p not in template_event['policies']:
                        #        wrong_policy_count += 1
                        #for doc in real_event['protected_documents']:
                        #    if doc not in template_event['protected_documents']:
                        #        wrong_document_count += 1
                        for p in template_event['policies']:
                            if p not in real_event['policies']:
                                missing_policy_count += 1
                        for doc in template_event['protected_documents']:
                            if doc not in real_event['protected_documents']:
                                missing_document_count += 1
                        for tag in real_event['tags']:
                            if tag['DISPLAY_NAME'] not in template_event['tags']:
                                wrong_tag_count += 1
            for real_event, template_event in t1['events']:
                event_delta = {}
                diff_policies = []       
                for policy in real_event['policies']:
                    if policy not in template_event['policies']:
                        diff_policies.append(policy)
                event_delta['policies'] = diff_policies

                diff_documents = []
                for document in real_event['protected_documents']:
                    if document not in template_event['protected_documents']:
                        diff_documents.append(document)
                event_delta['protected_documents'] = diff_documents

                diff_tags = []
                if not real_event['tags']:
                    real_event['tags'] = [{'DISPLAY_NAME': 'No'}]
                for tag in real_event['tags']:
                    if tag['DISPLAY_NAME'] not in template_event['tags']:
                        diff_tags.append(tag['DISPLAY_NAME'])
                event_delta['tags'] = diff_tags

                if template_event['verdict'] != real_event['VERDICT']:
                    event_delta['verdict'] = real_event['VERDICT']
                    wrong_verdict_count += 1
                else:
                     event_delta['verdict'] = 'ok'

                if template_event['violation_level'] != real_event['VIOLATION_LEVEL']:
                    event_delta['violation_level'] = real_event['VIOLATION_LEVEL']
                    wrong_violation_level_count += 1
                else:
                    event_delta['violation_level'] = 'ok'

                task_deltas.append(event_delta)
            t1['events_deltas'] = zip(t1['real_events'], t1['template_events'], task_deltas)
            t1['wrong_policies'] = wrong_policy_count
            t1['missing_policies'] = missing_policy_count
            t1['wrong_tags'] = wrong_tag_count
            t1['wrong_documents'] = wrong_document_count
            t1['missing_documents'] = missing_document_count
            t1['doc_errors'] = wrong_document_count + missing_document_count
            t1['wrong_verdict'] = wrong_verdict_count
            t1['wrong_violation_level'] = wrong_violation_level_count
            t1['total_errors'] = (wrong_tag_count + wrong_policy_count + 
                                    missing_policy_count + wrong_document_count + 
                                    missing_document_count + wrong_verdict_count +
                                    wrong_violation_level_count)
        self.save_results()

    def check_tasks_second_method(self):
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
            wrong_verdict_count = 0
            wrong_violation_level_count = 0
            
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

                if template_event['verdict'] != real_event['VERDICT']:
                    event_delta['verdict'] = real_event['VERDICT']
                    wrong_verdict_count += 1
                else:
                     event_delta['verdict'] = 'ok'

                if template_event['violation_level'] != real_event['VIOLATION_LEVEL']:
                    event_delta['violation_level'] = real_event['VIOLATION_LEVEL']
                    wrong_violation_level_count += 1
                else:
                    event_delta['violation_level'] = 'ok'
                
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
            task['doc_errors'] = task_wrong_documents + task_missing_documents
            task['wrong_verdict'] = wrong_verdict_count
            task['wrong_violation_level'] = wrong_violation_level_count
            task['total_errors'] = (task_wrong_tags + task_wrong_policies + 
                                    task_missing_policies + task_wrong_documents + 
                                    task_missing_documents + wrong_verdict_count + 
                                    wrong_violation_level_count)
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
        column_headers = ['Ложные политики', 'Отсутствующие политики', 
                        'Ложные объекты', 'Отсутствующие объекты', 
                        'Ложные теги', 'Ложные вердикты',
                        'Ложные уровни нарушения', 'Итого недочетов']
        
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
            sheet.cell(x_idx, y_idx).value = task['wrong_tags']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = task['wrong_verdict']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = task['wrong_violation_level']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = task['total_errors']
            sheet.cell(x_idx, y_idx).border = thin_border
        
        
        column_headers_doc = ['Ложные объекты', 'Отсутствующие объекты', 'Итого недочетов']
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

        for task in self.tasks:
            if task['number'] == '3':
                continue
            x_idx += 1
            y_idx = start_y
            sheet.cell(x_idx, y_idx).value = 'Объект защиты №' + task['number']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = 'Задание №' + task['number']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = task['wrong_documents']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = task['missing_documents']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = task['doc_errors']
            sheet.cell(x_idx, y_idx).border = thin_border
        
        book.save("app/static/results.xlsx")