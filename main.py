import tkinter as tk
from src.database.db import db
from src.database.migration import run_migrations
from src.core.config import config
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Application:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CryptoSafe Manager")
        self.root.geometry("900x600")

        # Connect database and run migrations
        db.connect()
        run_migrations(config.get('db_path', 'data/vault.db'))

        # Audit components (Sprint 5)
        self.audit_logger = None
        self.audit_verifier = None
        self.audit_signer = None

        # Initialize audit system
        self._init_audit_system()

        # Show main window
        self.root.deiconify()
        self.root.update()

        # Check first run after window displays
        self.root.after(100, self._check_first_run)

        self.root.mainloop()

    def _init_audit_system(self):
        """Initialize audit logging system for Sprint 5."""
        try:
            # Import audit modules
            from src.core.audit.log_signer import AuditLogSigner
            from src.core.audit.audit_logger import AuditLogger
            from src.core.audit.log_verifier import LogVerifier
            from src.core.key_manager import KeyManager

            # Get database connection from db.conn
            conn = db.conn

            # Create key manager - без аргументов
            key_manager = KeyManager()

            # Create audit signer
            self.audit_signer = AuditLogSigner(key_manager, use_ed25519=True)

            # Simple event bus stub
            class EventBusStub:
                def __init__(self):
                    self.listeners = {}

                def subscribe(self, event, callback):
                    if event not in self.listeners:
                        self.listeners[event] = []
                    self.listeners[event].append(callback)

                def publish(self, event, data):
                    if event in self.listeners:
                        for callback in self.listeners[event]:
                            callback(data)

            event_bus = EventBusStub()

            # Create audit logger
            audit_config = {
                'async_logging': True,
                'periodic_verification': True,
                'verification_sample_size': 1000,
                'lock_vault_on_tamper': True
            }

            self.audit_logger = AuditLogger(
                conn,
                self.audit_signer,
                event_bus,
                audit_config
            )

            # Create audit verifier
            verifier_config = {
                'periodic_verification': True,
                'verification_interval_hours': 24,
                'verification_sample_size': 1000,
                'lock_vault_on_tamper': True
            }

            self.audit_verifier = LogVerifier(
                conn,
                self.audit_signer,
                event_bus,
                verifier_config
            )

            # Log application startup
            self.audit_logger.log_event(
                event_type='APP_STARTUP',
                severity='INFO',
                source='main',
                details={'version': '1.0.0', 'sprint': 5},
                user_id='system'
            )

            # Verify integrity at startup (VER-1)
            result = self.audit_verifier.verify_at_startup()
            if not result.verified:
                logger.warning(f"Audit log integrity check failed: {len(result.invalid_entries)} invalid entries")
            else:
                logger.info("Audit log integrity verified successfully")

            logger.info("Audit system initialized for Sprint 5")

        except Exception as e:
            logger.error(f"Failed to initialize audit system: {e}")
            import traceback
            traceback.print_exc()

    def _check_first_run(self):
        """Check if first run and show main window."""
        from src.gui.main_window import MainWindow

        self.main_window = MainWindow(self.root)

        # Store audit components in main window if it has the attribute
        if hasattr(self.main_window, 'set_audit_components'):
            self.main_window.set_audit_components(self.audit_logger, self.audit_verifier)


if __name__ == "__main__":
    app = Application()