from .grader_repository import GraderRepository
from .iwtm_service import IWTMService
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Border, Side, Alignment
from openpyxl.utils import get_column_letter

class GraderService:
    def __init__(self, debug_mode):
        self.grader_repository = GraderRepository()
        self.iwtm_service = IWTMService(debug_mode)
    
    def save_template_file(self, path, file):
        with open(path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
    
    def save_participant_result(self, ip, result):
        self.grader_repository.save_participant_result(ip, result)
    
    def find_participant_result_by_ip(self, ip):
        return self.grader_repository.find_participant_result_by_ip(ip)
    
    def save_participant(self, ip, participant):
        self.grader_repository.save_participant(ip, participant)

    def get_all_participants(self):
        return self.grader_repository.get_all_participants()

    def find_participant_by_ip(self, ip):
        return self.grader_repository.find_participant_by_ip(ip)

    def load_events(self, iwtm_ip, username, password, date_and_time, template_file_path):
        template_events = self.load_template_events(template_file_path)
        
        auth_cookies = self.iwtm_service.login(iwtm_ip, username, password)
        iwtm_events = self.iwtm_service.get_parsed_events(iwtm_ip, auth_cookies, date_and_time)
        
        mapped_events = self.map_events(template_events, iwtm_events)
        protected_objects = self.iwtm_service.get_protected_objects(iwtm_ip, auth_cookies)
        self.iwtm_service.set_object_technologies(mapped_events, protected_objects)
        return mapped_events
    
    def load_template_events(self, filename):
        template_events = []
        wb = load_workbook(filename)
        sheet = wb.active
        row = 3
        while (sheet['D' + str(row)].value != None):
            task_item = {}
            task_item['task_number'] = sheet['A' + str(row)].value
            task_item['policy'] = sheet['B' + str(row)].value
            task_item['protected_object'] = sheet['C' + str(row)].value
            events = []
            current_task = task_item['task_number']
            while (current_task == task_item['task_number'] and sheet['D' + str(row)].value != None):
                event = {}
                event['filename'] = sheet['D' + str(row)].value
                event['sender'] = sheet['E' + str(row)].value
                event['recipient'] = sheet['F' + str(row)].value
                policies = sheet['G' + str(row)].value
                if policies:
                    event['policies'] = policies.split(',')
                else:
                    event['policies'] = []
                protected_objects = sheet['H' + str(row)].value
                if protected_objects:
                    event['protected_objects'] = protected_objects.split(',')
                else:
                    event['protected_objects'] = []
                event['verdict'] = sheet['I' + str(row)].value
                event['violation_level'] = sheet['J' + str(row)].value
                tags = sheet['K' + str(row)].value
                if tags:
                    event['tags'] = tags.split(',')
                else:
                    event['tags'] = []
                events.append(event)
                row += 1
                if sheet['A' + str(row)].value == None:
                    current_task = task_item['task_number']
                else:
                    current_task = sheet['A' + str(row)].value
            task_item['events'] = events
            task_item['stats'] = {}
            template_events.append(task_item)
        return template_events

    def map_events(self, template_events, iwtm_events):
        mapped_events = []
        for item in template_events:
            mapped_item = item
            for event in mapped_item['events']:
                event['iwtm_event'] = self.find_event_by_id(iwtm_events, event['filename'], event['sender'], event['recipient'])
            mapped_events.append(mapped_item)
        return mapped_events

    def find_event_by_id(self, events, filename, sender, recipient):
        found_event = {}
        for event in events:
            if event['filename'] == filename and event['sender'] == sender and event['recipient'] == recipient:
                found_event = event
                return found_event
        return found_event

    def check_events_normal_mode(self, grouped_events):
        self.check_events_max_mode(grouped_events)
        for item in grouped_events:
            self.find_false_triggering_and_update_stats(item, grouped_events)
        return grouped_events

    def find_false_triggering_and_update_stats(self, item, grouped_events):
        policy = item['policy']
        protected_object = item['protected_object']
        for any_item in grouped_events:
            for policy_event in any_item['events']:
                iwtm_event = policy_event['iwtm_event']
                if (policy in iwtm_event['policies'] and
                        policy not in policy_event['policies']):
                    item['stats']['false_policies'] += 1
                    any_item['stats']['false_policies'] -= 1
                    item['stats']['false_tags'] += 1
                    any_item['stats']['false_tags'] -= 1
                    
                if (protected_object in iwtm_event['protected_objects'] and
                        protected_object not in policy_event['protected_objects']):
                    item['stats']['false_objects'] += 1
                    any_item['stats']['false_objects'] -= 1

    def check_events_max_mode(self, grouped_events):
        for item in grouped_events:
            self.init_task_stats(item)
            self.check_events_one_to_one(item)
        return grouped_events

    def check_events_one_to_one(self, item):
        for task_event in item['events']:
            self.find_and_set_event_difference(task_event['iwtm_event'], task_event)
            self.update_task_stats(item, task_event['iwtm_event'], task_event)

    def init_task_stats(self, item):
        item['stats']['failed_policies'] = 0
        item['stats']['false_policies'] = 0
        item['stats']['failed_objects'] = 0
        item['stats']['false_objects'] = 0
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
        failed_objects_diff = self.get_array_difference(template_event['protected_objects'],
                                                              iwtm_event['protected_objects'])
        false_objects_diff = self.get_array_difference(iwtm_event['protected_objects'],
                                                             template_event['protected_objects'])
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
        iwtm_event['diff']['protected_objects'] = false_objects_diff
        template_event['diff']['protected_objects'] = failed_objects_diff
        iwtm_event['diff']['tags'] = false_tags_diff
        template_event['diff']['tags'] = failed_tags_diff
        iwtm_event['diff']['verdict'] = wrong_verdict_diff
        iwtm_event['diff']['violation_level'] = wrong_violation_level_diff
    
    def update_task_stats(self, item, iwtm_event, template_event):
        item['stats']['failed_policies'] += len(template_event['diff']['policies'])
        item['stats']['false_policies'] += len(iwtm_event['diff']['policies'])
        item['stats']['failed_objects'] += len(template_event['diff']['protected_objects'])
        item['stats']['false_objects'] += len(iwtm_event['diff']['protected_objects'])
        item['stats']['wrong_tags'] += len(template_event['diff']['tags'])
        item['stats']['false_tags'] += len(iwtm_event['diff']['tags'])
        if iwtm_event['diff']['verdict']:
            item['stats']['wrong_verdict'] += 1
        if iwtm_event['diff']['violation_level']:
            item['stats']['wrong_violation_level'] += 1
    
    def export_participant_result(self, result, filename):
        start_x = 2
        start_y = 1
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                            top=Side(style='thin'), bottom=Side(style='thin'))
        cell_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        book = Workbook()
        sheet = book.active
        x_idx = start_x
        y_idx = start_y
        column_headers = ['Задание', 'Политика', 'Ложные политики', 'Несработавшие политики', 
                        'Ложные объекты', 'Несработавшие объекты', 
                        'Ложные теги', 'Неправильные теги', 'Неправильные вердикты',
                        'Неправильные уровни нарушения', 'Итого недочетов']
        
        for header in column_headers:
            sheet.cell(x_idx, y_idx).value = header
            sheet.cell(x_idx, y_idx).border = thin_border
            sheet.cell(x_idx, y_idx).alignment = cell_align
            sheet.column_dimensions[get_column_letter(y_idx)].width = 18
            y_idx += 1
        
        for item in result:
            x_idx += 1
            y_idx = start_y
            policy = item['policy']
            task = item['task_number']
            total_errors = (item['stats']['false_policies'] + item['stats']['failed_policies'] +
                            item['stats']['false_objects'] + item['stats']['failed_objects'] +
                            item['stats']['false_tags'] + item['stats']['wrong_tags'] +
                            item['stats']['wrong_verdict'] + item['stats']['wrong_violation_level'])
            sheet.cell(x_idx, y_idx).value = task
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = policy
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = item['stats']['false_policies']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = item['stats']['failed_policies']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = item['stats']['false_objects']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = item['stats']['failed_objects']
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
        
        
        column_headers_doc = ['Задание', 'Объект защиты', 'Ложные объекты', 
                              'Несработавшие объекты', 'Итого недочетов', 'Типы технологий']
        y_idx = start_y
        x_idx += 3
        for header in column_headers_doc:
            sheet.cell(x_idx, y_idx).value = header
            sheet.cell(x_idx, y_idx).border = thin_border
            sheet.cell(x_idx, y_idx).alignment = cell_align
            sheet.column_dimensions[get_column_letter(y_idx)].width = 18
            y_idx += 1

        for item in result:
            x_idx += 1
            y_idx = start_y
            protected_object = item['protected_object']
            task = item['task_number']
            total_errors = item['stats']['false_objects'] + item['stats']['failed_objects']
            sheet.cell(x_idx, y_idx).value = task
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = protected_object
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = item['stats']['false_objects']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = item['stats']['failed_objects']
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            sheet.cell(x_idx, y_idx).value = total_errors
            sheet.cell(x_idx, y_idx).border = thin_border
            y_idx += 1
            if item['protected_object_technologies']:
                technologies_str = ", ".join(item['protected_object_technologies'])
                sheet.cell(x_idx, y_idx).value = technologies_str
            sheet.cell(x_idx, y_idx).border = thin_border
        book.save(filename)