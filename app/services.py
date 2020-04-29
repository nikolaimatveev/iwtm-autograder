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
                events.append(row)
        return events
    
    def find_by_complex_id(events, filename, sender, recipient):
        found_events = []
        for event in events:
            if event.filename == filename and event.sender == sender and event.recipient == recipient:
                found_events.append(event)
        return found_events

    def get_real(self, filename):
        data = []
        with open(filename, encoding='utf-8') as json_file:
            data = json.load(json_file)
        return data['data']
    
    # Входные данные - лист заданий для реальных событий, лист заданий для шаблонных событий
    # Порядок политик, тэгов в шаблоне и факте может отличаться, как сравнивать?
    def compare(self, template_events, real_events):
        deltas = []
        template_real_events_zipped = zip(template_events, real_events)
        for template_event, real_event in template_real_events_zipped:
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
            deltas.append(event_delta)
        return deltas