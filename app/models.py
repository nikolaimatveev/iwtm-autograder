from datetime import datetime

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
    def __init__(self, number, real_events, template_events, summary):
        self.number = number
        self.real_events = real_events
        self.template_events = template_events
        self.summary = summary

class Comment(object):
    def __init__(self, email, content, created=None):
        self.email = email
        self.content = content
        self.created = created or datetime.now()