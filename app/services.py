import csv
import os
import json

# Цель веб-приложения: показать что в задании выполнено неправильно,
# внести правки в найденные ошибки при необходимости,
# вычислить баллы и вывести их в таблицу?

# Сравнивать нужно НЕ поэлементно, а по уникальному ключу


class EventService:

    def get_template(self, filename):
        events = []
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
                events.append(event)
        return events
    
    def find_all_by_id(self, events, filename, sender, recipient):
        found_events = []
        for event in events:
            subject = json.loads(event['PREVIEW_DATA'])['subject'].split(', ')
            event_sender = subject[0].split(':')[1].strip()
            event_recipient = subject[1].split(':')[1].strip()
            event_filename = subject[2].split(':')[1].strip()
            event['sender'] = event_sender
            event['recipient'] = event_recipient
            event['filename'] = event_filename
            if event_filename == filename and event_sender == sender and event_recipient == recipient:
                found_events.append(event)
        return found_events

    def align_real(self, real_events, template_events):
        result = []
        for event in template_events:
            found_events = self.find_all_by_id(real_events, event['filename'], event['sender'], event['recipient'])
            for e in found_events:
                result.append(e)
        return result
    
    def align_template(template_events, real_events):
        result = []
        for event in template_events:
            found_events = self.find_all_by_id(real_events, event.filename, event.sender, event.recipient)
            result.append(event)
            empty_event = {}
            empty_event['filename'] = 'null'
            for _ in found_events:
                result.append(empty_event)
        return result

    def get_real(self, filename):
        data = []
        with open(filename, encoding='utf-8') as json_file:
            data = json.load(json_file)
        return data['data']

    def compare(self, template_events, real_events):
        deltas = []
        delta_id = 1
        for template_event, real_event in zip(template_events, real_events):
            event_delta = {}
            diff_policies = []
            for policy in real_event['policies']:
                if policy['DISPLAY_NAME'] not in template_event['policies']:
                    diff_policies.append(policy['DISPLAY_NAME'])
            event_delta['policies'] = diff_policies

            diff_tags = []
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
            print(event_delta)
            deltas.append(event_delta)
        return deltas