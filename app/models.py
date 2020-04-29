class Event:
    def __init__(self, filename,
                 sender, recipient,
                 policies, verdict, 
                 violation_level, tag):
        self.filename = filename
        self.sender = sender
        self.recipient = recipient
        self.policies = policies
        self.verdict = verdict
        self.violation_level = violation_level
        self.tag = tag

class Task:
    def __init__(self, number, events):
        self.number = number
        self.events = events