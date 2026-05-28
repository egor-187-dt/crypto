

import re
from typing import Dict, List, Tuple


class PasswordValidator:

    # Распространенные пароли для проверки
    COMMON_PASSWORDS = {
        "password", "qwerty", "123456", "admin", "welcome",
        "password123", "qwerty123", "123456789", "abc123",
        "letmein", "monkey", "dragon", "baseball", "football",
        "superman", "iloveyou", "trustno1", "1234567", "sunshine",
        "master", "hello", "whatever", "shadow", "fish", "access",
        "secret", "123123", "555555", "654321", "zxcvbnm", "asdfgh"
    }

    def __init__(self, min_length: int = 12):

        self.min_length = min_length

    def validate(self, password: str) -> Tuple[bool, List[str]]:

        errors = []

        if len(password) < self.min_length:
            errors.append(f"Минимальная длина {self.min_length} символов")

        if not any(c.isupper() for c in password):
            errors.append("Добавьте заглавные буквы (A-Z)")

        if not any(c.islower() for c in password):
            errors.append("Добавьте строчные буквы (a-z)")

        if not any(c.isdigit() for c in password):
            errors.append("Добавьте цифры (0-9)")

        if not any(not c.isalnum() for c in password):
            errors.append("Добавьте специальные символы (!@#$%^&*)")

        if self._is_common_password(password):
            errors.append("Пароль слишком распространенный, выберите другой")

        if self._has_repeating_patterns(password):
            errors.append("Пароль содержит повторяющиеся символы (например, 'aaa' или '123123')")

        return len(errors) == 0, errors

    def check_strength(self, password: str) -> Dict:

        score = 0
        warnings = []

        # Длина
        if len(password) >= self.min_length:
            score += 1
        else:
            warnings.append(f"Длина {len(password)}/{self.min_length} символов")

        # Заглавные буквы
        if any(c.isupper() for c in password):
            score += 1
        else:
            warnings.append("Нет заглавных букв")

        # Строчные буквы
        if any(c.islower() for c in password):
            score += 1
        else:
            warnings.append("Нет строчных букв")

        # Цифры
        if any(c.isdigit() for c in password):
            score += 1
        else:
            warnings.append("Нет цифр")

        # Спецсимволы
        if any(not c.isalnum() for c in password):
            score += 1
        else:
            warnings.append("Нет специальных символов")

        # Проверка на распространенные пароли
        if self._is_common_password(password):
            warnings.append("Слишком распространенный пароль")
            score = min(score, 2)  # Штраф

        # Проверка на повторяющиеся паттерны
        if self._has_repeating_patterns(password):
            warnings.append("Содержит повторяющиеся паттерны")
            score = max(0, score - 1)  # Штраф

        # Определение силы пароля
        if score <= 2:
            strength = "weak"
        elif score <= 4:
            strength = "medium"
        else:
            strength = "strong"

        return {
            'score': score,
            'strength': strength,
            'warnings': warnings,
            'is_valid': score >= 3
        }

    def _is_common_password(self, password: str) -> bool:

        pwd_lower = password.lower()

        # Прямое совпадение
        if pwd_lower in self.COMMON_PASSWORDS:
            return True

        # Содержит распространенный паттерн
        for common in self.COMMON_PASSWORDS:
            if common in pwd_lower or pwd_lower in common:
                return True

        return False

    def _has_repeating_patterns(self, password: str) -> bool:

        # Повторяющиеся символы (aaa, bbb)
        if re.search(r'(.)\1{2,}', password):
            return True

        # Повторяющиеся последовательности (123123, abcabc)
        for i in range(2, len(password) // 2 + 1):
            pattern = password[:i]
            if password.count(pattern) >= 2 and len(pattern) >= 2:
                return True

        # Клавиатурные последовательности
        keyboard_rows = [
            "qwertyuiop", "asdfghjkl", "zxcvbnm",
            "0123456789", "!@#$%^&*"
        ]
        pwd_lower = password.lower()
        for row in keyboard_rows:
            for i in range(len(row) - 2):
                seq = row[i:i+3]
                if seq in pwd_lower or seq[::-1] in pwd_lower:
                    return True

        return False

    def generate_feedback(self, password: str) -> str:

        is_valid, errors = self.validate(password)

        if is_valid:
            strength = self.check_strength(password)['strength']
            if strength == 'strong':
                return " Надежный пароль!"
            elif strength == 'medium':
                return " Средний пароль"
            else:
                return " Пароль слабый, рекомендуется усилить"

        return "✗ " + ", ".join(errors[:3])  # Показываем не более 3 ошибок