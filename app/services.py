import csv
import os
import json
import urllib.parse
import urllib.request
import ssl

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
            event['sender'] = event_sender
            event['recipient'] = event_recipient
            event['filename'] = event_filename
    
    # Почему в событии появился объект защиты, который не указан в политике?
    # protected_documents - объекты защиты
    def load_events_from_iwtm(self, ip, token, timestamp):
        #token = '1bs23q0mf47941ctode8'
        HTTP_HEADERS = {'X-API-Version': 1,
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
    
    def remove_delta(self, delta_id):
        print(delta_id)
        for delta in self.deltas:
            if delta['verdict'] == int(delta_id):
                delta['verdict']['name'] = 'ok'
                

    def add_delta(self, delta_id, value):
        for delta in self.deltas:
            if delta['verdict']['id'] == delta_id:
                self.delta['verdict']['name'] = value
    
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
            task_wrong_documents = 0
            for real_event, template_event in task['events']:
                event_delta = {}
                diff_policies = []

                if not real_event['policies']:
                    real_event['policies'] = [{'DISPLAY_NAME': 'No'}]

                wrong_policy_count = 0                
                for policy in real_event['policies']:
                    if policy['DISPLAY_NAME'] not in template_event['policies']:
                        diff_policies.append(policy['DISPLAY_NAME'])
                        wrong_policy_count += 1
                event_delta['policies'] = diff_policies
                event_delta['wrong_policies'] = wrong_policy_count

                diff_documents = []
                if not real_event['protected_documents']:
                    real_event['protected_documents'] = [{'DISPLAY_NAME': 'No'}]            
                
                wrong_document_count = 0
                for document in real_event['protected_documents']:
                    if document['DISPLAY_NAME'] not in template_event['protected_documents']:
                        diff_documents.append(document['DISPLAY_NAME'])
                        wrong_document_count += 1
                event_delta['protected_documents'] = diff_documents
                event_delta['wrong_documents'] = wrong_document_count
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
                task_wrong_documents += event_delta['wrong_documents']
                task_deltas.append(event_delta)
            task['events_deltas'] = zip(task['real_events'], task['template_events'], task_deltas)
            task['wrong_tags'] = task_wrong_tags
            task['wrong_policies'] = task_wrong_policies
            task['wrong_documents'] = task_wrong_documents

    def compare(self):
        self.deltas = []
        delta_id = 1
        self.align_real()
        for template_event, real_event in zip(self.template_events, self.real_events):
            event_delta = {}
            diff_policies = []

            if not real_event['policies']:
                real_event['policies'] = [{'DISPLAY_NAME': 'No'}]

            for policy in real_event['policies']:
                if policy['DISPLAY_NAME'] not in template_event['policies']:
                    diff_policies.append(policy['DISPLAY_NAME'])
            event_delta['policies'] = diff_policies

            diff_documents = []
            if not real_event['protected_documents']:
                real_event['protected_documents'] = [{'DISPLAY_NAME': 'No'}]            
            
            for document in real_event['protected_documents']:
                if document['DISPLAY_NAME'] not in template_event['protected_documents']:
                    diff_documents.append(document['DISPLAY_NAME'])
            event_delta['protected_documents'] = diff_documents
            
            diff_tags = []
            if not real_event['tags']:
                real_event['tags'] = [{'DISPLAY_NAME': 'No'}]

            for tag in real_event['tags']:
                if tag['DISPLAY_NAME'] not in template_event['tags']:
                    diff_tags.append(tag['DISPLAY_NAME'])
            event_delta['tags'] = diff_tags

            tmp_diff = {}
            tmp_diff['id'] = delta_id
            delta_id += 1
            tmp_diff['name'] = (
                real_event['VERDICT']
                if template_event['verdict'] != real_event['VERDICT']
                else 'ok'
            )

            event_delta['verdict'] = tmp_diff

            event_delta['violation_level'] = (
                real_event['VIOLATION_LEVEL']
                if template_event['violation_level'] != real_event['VIOLATION_LEVEL']
                else 'ok'
            )
            self.deltas.append(event_delta)
        return self.deltas