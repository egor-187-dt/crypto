"""
Main clipboard service for CryptoSafe Manager
"""
import threading
from datetime import datetime
from typing import Optional

from src.core.clipboard.secure_memory import SecureClipboardItem
from src.core.clipboard.platform_adapter import get_platform_adapter, ClipboardAdapter
from src.core.clipboard.clipboard_monitor import ClipboardMonitor
from src.core.events import events


class ClipboardService:

    PRESET_PROFILES = {
        'standard': {
            'timeout_seconds': 30,
            'notifications': True,
            'security_level': 'basic',
            'accelerate_on_access': False
        },
        'secure': {
            'timeout_seconds': 15,
            'notifications': True,
            'security_level': 'advanced',
            'accelerate_on_access': True
        },
        'public_computer': {
            'timeout_seconds': 5,
            'notifications': True,
            'security_level': 'paranoid',
            'accelerate_on_access': True
        }
    }

    def __init__(self, config_manager=None):
        self.config = config_manager
        self.platform = None
        self.current_item: Optional[SecureClipboardItem] = None
        self.timer: Optional[threading.Timer] = None
        self.lock = threading.RLock()
        self.is_vault_unlocked = False

        self.timeout_seconds = self._load_setting('clipboard_timeout', 30)
        self.notifications_enabled = self._load_setting('clipboard_notifications', True)
        self.security_level = self._load_setting('clipboard_security_level', 'basic')
        self.accelerate_on_access = self._load_setting('clipboard_accelerate_on_access', False)

        try:
            self.platform = get_platform_adapter()
        except RuntimeError as e:
            events.publish('clipboard_error', {'error': str(e)})
            self.platform = None

        self.monitor = ClipboardMonitor(
            on_external_access_callback=self._on_external_access,
            on_content_changed_callback=self._on_content_changed
        )

        events.subscribe('user_logged_in', self._on_vault_unlocked)
        events.subscribe('user_logged_out', self._on_vault_locked)

        if self.platform:
            self.monitor.start()

    def _load_setting(self, key: str, default):
        if self.config:
            return self.config.get(key, default)
        return default

    def _save_setting(self, key: str, value):
        if self.config:
            self.config.set(key, value)

    def _on_vault_unlocked(self, data=None):
        self.is_vault_unlocked = True

    def _on_vault_locked(self, data=None):
        self.clear_clipboard(reason="vault_locked")
        self.is_vault_unlocked = False

    def _on_external_access(self, data):
        if self.accelerate_on_access and self.current_item and self.platform:
            events.publish('clipboard_suspicious_access', {
                'access_count': data.get('access_count'),
                'action': 'accelerating_clear'
            })
            self.clear_clipboard(reason="suspicious_access")

    def _on_content_changed(self, data):
        if self.current_item:
            self._cancel_timer()
            self.current_item = None
            events.publish('clipboard_external_change', data)

    def copy_to_clipboard(self, data: str, data_type: str = "password",
                          source_entry_id: Optional[int] = None) -> bool:

        if not self.is_vault_unlocked:
            events.publish('clipboard_error', {'error': 'vault_locked'})
            return False

        if not self.platform:
            events.publish('clipboard_error', {'error': 'no clipboard adapter'})
            return False

        with self.lock:
            self._clear_system_clipboard()

            self.current_item = SecureClipboardItem(
                data=data,
                data_type=data_type,
                source_entry_id=source_entry_id
            )

            success = self.platform.copy_to_clipboard(data)

            if success:
                self._cancel_timer()

                if self.timeout_seconds > 0:
                    self.timer = threading.Timer(self.timeout_seconds, self._on_timeout)
                    self.timer.daemon = True
                    self.timer.start()

                events.publish('clipboard_copied', {
                    'data_type': data_type,
                    'source_entry_id': source_entry_id,
                    'timeout_seconds': self.timeout_seconds
                })

                if self.notifications_enabled:
                    self._show_notification(f"Copied {data_type} to clipboard")

                return True

            return False

    def _on_timeout(self):
        with self.lock:
            if self.current_item:
                self._clear_system_clipboard()
                self.current_item.secure_wipe()
                self.current_item = None
                events.publish('clipboard_cleared', {'reason': 'timeout'})

                if self.notifications_enabled:
                    self._show_notification("Clipboard cleared automatically")

    def clear_clipboard(self, reason: str = "manual"):
        with self.lock:
            self._clear_system_clipboard()

            if self.current_item:
                self.current_item.secure_wipe()
                self.current_item = None

            self._cancel_timer()
            events.publish('clipboard_cleared', {'reason': reason})

            if self.notifications_enabled and reason == "manual":
                self._show_notification("Clipboard cleared")

    def _clear_system_clipboard(self):
        if self.platform:
            try:
                self.platform.clear_clipboard()
            except Exception as e:
                events.publish('clipboard_error', {'error': f'Failed to clear: {e}'})

    def _cancel_timer(self):
        if self.timer:
            self.timer.cancel()
            self.timer = None

    def _show_notification(self, message: str):
        events.publish('clipboard_notification', {'message': message})

    def get_status(self) -> dict:
        with self.lock:
            if not self.current_item:
                return {'active': False, 'remaining_seconds': 0}

            elapsed = (datetime.now() - self.current_item.copied_at).total_seconds()
            remaining = max(0, self.timeout_seconds - elapsed) if self.timeout_seconds > 0 else 0

            return {
                'active': True,
                'data_type': self.current_item.data_type,
                'source_entry_id': self.current_item.source_entry_id,
                'remaining_seconds': remaining,
                'security_level': self.security_level,
                'suspicious_activity': self.monitor.is_suspicious_activity() if self.monitor else False
            }

    def set_timeout(self, seconds: int):
        if seconds < 0:
            raise ValueError("Timeout cannot be negative")
        if seconds > 300:
            seconds = 300

        self.timeout_seconds = seconds
        self._save_setting('clipboard_timeout', seconds)

        with self.lock:
            if self.current_item and seconds > 0 and self.platform:
                self._cancel_timer()
                self.timer = threading.Timer(seconds, self._on_timeout)
                self.timer.daemon = True
                self.timer.start()
            elif seconds == 0 and self.current_item:
                self._cancel_timer()

    def set_security_level(self, level: str):
        if level not in ['basic', 'advanced', 'paranoid']:
            raise ValueError(f"Invalid security level: {level}")

        self.security_level = level
        self._save_setting('clipboard_security_level', level)

        if level in self.PRESET_PROFILES:
            profile = self.PRESET_PROFILES[level]
            self.set_timeout(profile['timeout_seconds'])
            self.set_notifications(profile['notifications'])
            self.set_accelerate_on_access(profile['accelerate_on_access'])

    def set_notifications(self, enabled: bool):
        self.notifications_enabled = enabled
        self._save_setting('clipboard_notifications', enabled)

    def set_accelerate_on_access(self, enabled: bool):
        self.accelerate_on_access = enabled
        self._save_setting('clipboard_accelerate_on_access', enabled)

    def apply_preset(self, preset_name: str):
        if preset_name not in self.PRESET_PROFILES:
            raise ValueError(f"Unknown preset: {preset_name}")

        profile = self.PRESET_PROFILES[preset_name]
        self.set_timeout(profile['timeout_seconds'])
        self.set_notifications(profile['notifications'])
        self.set_security_level(profile['security_level'])
        self.set_accelerate_on_access(profile['accelerate_on_access'])

    def shutdown(self):
        self.clear_clipboard(reason="application_shutdown")
        if self.monitor:
            self.monitor.stop()

    def get_masked_preview(self) -> Optional[str]:
        with self.lock:
            if not self.current_item:
                return None

            plaintext = self.current_item.get_plaintext()

            if self.current_item.data_type == 'password':
                if len(plaintext) <= 8:
                    return chr(8226) * len(plaintext)
                return plaintext[:3] + chr(8226) * 6 + plaintext[-1]
            else:
                if len(plaintext) <= 7:
                    return plaintext
                return plaintext[:4] + chr(8226) * 3


clipboard_service = None

def get_clipboard_service(config_manager=None) -> ClipboardService:
    global clipboard_service
    if clipboard_service is None:
        clipboard_service = ClipboardService(config_manager)
    return clipboard_service