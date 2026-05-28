from datetime import datetime, timedelta


class StateManager:
    def __init__(self):
        self.is_logged_in = False
        self.is_locked = False
        self.clipboard_timer = None
        self.login_time = None
        self.last_activity = None

    def login(self):
        self.is_logged_in = True
        self.is_locked = False
        self.login_time = datetime.now()
        self.last_activity = datetime.now()

    def logout(self):
        self.is_logged_in = False
        self.is_locked = False
        self.login_time = None
        self.last_activity = None

    def lock(self):
        if self.is_logged_in:
            self.is_locked = True

    def unlock(self):
        if self.is_locked:
            self.is_locked = False
            self.last_activity = datetime.now()

    def update_activity(self):
        if self.is_logged_in:
            self.last_activity = datetime.now()

    def is_inactive(self, timeout_minutes=60):
        if not self.last_activity:
            return True
        return datetime.now() - self.last_activity > timedelta(minutes=timeout_minutes)


state = StateManager()