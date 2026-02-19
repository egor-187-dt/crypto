class StateManager:
    def __init__(self):
        self.is_logged_in = False
        self.is_locked = False
        self.clipboard_timer = None

    def login(self):
        self.is_logged_in = True
        self.is_locked = False

    def logout(self):
        self.is_logged_in = False
        self.is_locked = False

    def lock(self):
        if self.is_logged_in:
            self.is_locked = True

    def unlock(self, password):
        # Тут будет проверка пароля позже
        if self.is_locked:
            self.is_locked = False

state = StateManager()