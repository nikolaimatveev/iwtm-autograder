
class GraderRepository:
    def __init__(self):
        self.participant_results = {}
        self.participants = {}

    def save_participant_result(self, ip, result):
        self.participant_results[ip] = result
    
    def find_participant_result_by_ip(self, ip):
        result = {}
        if ip in self.participant_results:
            result = self.participant_results[ip]
        return result
    
    def save_participant(self, ip, participant):
        self.participants[ip] = participant

    def get_all_participants(self):
        return self.participants.values()

    def find_participant_by_ip(self, ip):
        result = {}
        if ip in self.participants:
            result = self.participants[ip]
        return result