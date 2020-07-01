class GraderRepository:
    def __init__(self):
        self.participant_results = {}
        self.participants = {}
        self.auth_cookies = {}

    def save_participant_result(self, participant_number, result):
        self.participant_results[participant_number] = result
    
    def find_participant_result_by_number(self, number):
        result = {}
        if number in self.participant_results:
            result = self.participant_results[number]
        return result
    
    def save_participant(self, participant):
        self.participants[participant['number']] = participant

    def get_all_participants(self):
        return self.participants.values()

    def find_participant_by_number(self, number):
        result = {}
        if number in self.participants:
            result = self.participants[number]
        return result

    def save_auth_cookie(self, participant_number, auth_cookie):
        self.auth_cookies[participant_number] = auth_cookie
    
    def get_auth_cookie(self, participant_number):
        result = {}
        if participant_number in self.auth_cookies:
            result = self.auth_cookies[participant_number]
        return result