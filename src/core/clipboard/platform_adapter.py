"""
Platform-specific clipboard adapters for Windows
"""
import platform
from abc import ABC, abstractmethod
from typing import Optional

WIN32_AVAILABLE = False
PYPERCLIP_AVAILABLE = False

try:
    import win32clipboard
    WIN32_AVAILABLE = True
except ImportError:
    pass

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    pass


class ClipboardAdapter(ABC):

    @abstractmethod
    def copy_to_clipboard(self, data: str) -> bool:
        pass

    @abstractmethod
    def clear_clipboard(self) -> bool:
        pass

    @abstractmethod
    def get_clipboard_content(self) -> Optional[str]:
        pass


class WindowsClipboardAdapter(ClipboardAdapter):

    def __init__(self):
        if not WIN32_AVAILABLE:
            raise RuntimeError("pywin32 required for Windows clipboard")

    def copy_to_clipboard(self, data: str) -> bool:
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(data, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            return True
        except Exception:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass
            return False

    def clear_clipboard(self) -> bool:
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.CloseClipboard()
            return True
        except Exception:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass
            return False

    def get_clipboard_content(self) -> Optional[str]:
        try:
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
                return data
            win32clipboard.CloseClipboard()
            return None
        except Exception:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass
            return None


class FallbackClipboardAdapter(ClipboardAdapter):

    def __init__(self):
        if not PYPERCLIP_AVAILABLE:
            raise RuntimeError("pyperclip required for fallback")

    def copy_to_clipboard(self, data: str) -> bool:
        try:
            pyperclip.copy(data)
            return True
        except Exception:
            return False

    def clear_clipboard(self) -> bool:
        try:
            pyperclip.copy("")
            return True
        except Exception:
            return False

    def get_clipboard_content(self) -> Optional[str]:
        try:
            return pyperclip.paste()
        except Exception:
            return None


def get_platform_adapter() -> ClipboardAdapter:
    system = platform.system()

    if system == 'Windows' and WIN32_AVAILABLE:
        return WindowsClipboardAdapter()

    if PYPERCLIP_AVAILABLE:
        return FallbackClipboardAdapter()

    raise RuntimeError("No clipboard adapter available. Please install: pip install pywin32 pyperclip")