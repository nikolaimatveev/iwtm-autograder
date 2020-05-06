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
                event['verdict'] = row['verdict']
                event['violation_level'] = row['violation_level']
                event['tags'] = row['tags'].split(',')
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
    
    def load_events_from_iwtm(self, ip, token):
        #token = '1bs23q0mf47941ctode8'
        HTTP_HEADERS = {'X-API-Version': 1,
                        'X-API-CompanyId': 'GUAP',
                        'X-API-ImporterName': 'GUAP',
                        'X-API-Auth-Token': token}
        string_timestamp = '1588759200'
        url = 'https://' + ip + ':17443/xapi/event?with[protected_documents]&with[policies]&with[protected_catalogs]&with[tags]&with[senders]&with[recipients]&with[recipients_keys]&with[senders_keys]&start=0&filter[date][from]=' + string_timestamp
        req = urllib.request.Request(url, headers=HTTP_HEADERS)
        data = []
        with urllib.request.urlopen(req, context=ssl._create_unverified_context()) as response:
            the_page = response.read()
            data = json.loads(the_page)
        self.real_events = data['data']
        self.fix_real()

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