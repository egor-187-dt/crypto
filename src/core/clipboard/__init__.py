"""
Clipboard module for CryptoSafe Manager - Sprint 4
"""

from src.core.clipboard.clipboard_service import ClipboardService, get_clipboard_service
from src.core.clipboard.platform_adapter import WindowsClipboardAdapter, get_platform_adapter
from src.core.clipboard.clipboard_monitor import ClipboardMonitor
from src.core.clipboard.secure_memory import SecureClipboardItem, secure_zero

__all__ = [
    'ClipboardService',
    'get_clipboard_service',
    'WindowsClipboardAdapter',
    'get_platform_adapter',
    'ClipboardMonitor',
    'SecureClipboardItem',
    'secure_zero'
]