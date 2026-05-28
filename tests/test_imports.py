import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Python path:", sys.path[:3])
print("Current directory:", os.getcwd())
print("Project root:", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    print("\nTrying to import KeyDerivation...")
    from src.core.crypto.key_derivation import KeyDerivation
    print("OK: KeyDerivation imported")
except ImportError as e:
    print(f"FAIL: {e}")

try:
    print("\nTrying to import Authenticator...")
    from src.core.crypto.authentication import Authenticator
    print("OK: Authenticator imported")
except ImportError as e:
    print(f"FAIL: {e}")

try:
    print("\nTrying to import PasswordValidator...")
    from src.core.crypto.password_validator import PasswordValidator
    print("OK: PasswordValidator imported")
except ImportError as e:
    print(f"FAIL: {e}")

try:
    print("\nTrying to import EntryManager...")
    from src.core.vault.entry_manager import EntryManager
    print("OK: EntryManager imported")
except ImportError as e:
    print(f"FAIL: {e}")

print("\nChecking files on disk:")
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if os.path.exists(src_path):
    print(f"src directory exists at: {src_path}")
    for root, dirs, files in os.walk(src_path):
        level = root.replace(src_path, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 2 * (level + 1)
        for file in files[:5]:
            print(f'{subindent}{file}')
else:
    print(f"src directory NOT found at: {src_path}")