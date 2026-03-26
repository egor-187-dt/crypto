import secrets
import string


class PasswordGenerator:
    """Безопасный генератор паролей"""

    DEFAULT_LENGTH = 16
    AMBIGUOUS = 'lI1O0'

    def __init__(self):
        self.history = []

    def generate(self, length: int = DEFAULT_LENGTH, use_upper=True, use_lower=True,
                 use_digits=True, use_symbols=True, exclude_ambiguous=True) -> str:
        """Генерирует пароль с заданными параметрами"""
        if length < 8:
            length = 8
        if length > 64:
            length = 64

        chars = ''
        if use_upper:
            chars += string.ascii_uppercase
        if use_lower:
            chars += string.ascii_lowercase
        if use_digits:
            chars += string.digits
        if use_symbols:
            chars += '!@#$%^&*'

        if exclude_ambiguous:
            chars = ''.join(c for c in chars if c not in self.AMBIGUOUS)

        password_parts = []

        # Гарантируем хотя бы один символ из каждого набора
        if use_upper:
            password_parts.append(secrets.choice(string.ascii_uppercase))
        if use_lower:
            password_parts.append(secrets.choice(string.ascii_lowercase))
        if use_digits:
            password_parts.append(secrets.choice(string.digits))
        if use_symbols:
            password_parts.append(secrets.choice('!@#$%^&*'))

        # Добираем остальные символы
        remaining = length - len(password_parts)
        if remaining > 0 and chars:
            password_parts.extend(secrets.choice(chars) for _ in range(remaining))

        # Перемешиваем
        for i in range(len(password_parts) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            password_parts[i], password_parts[j] = password_parts[j], password_parts[i]

        password = ''.join(password_parts)

        # Проверяем историю
        if password in self.history:
            return self.generate(length, use_upper, use_lower, use_digits, use_symbols, exclude_ambiguous)

        # Сохраняем в историю
        self.history.append(password)
        if len(self.history) > 20:
            self.history.pop(0)

        return password

    def check_strength(self, password: str) -> dict:
        """Проверка надежности пароля"""
        score = 0
        if len(password) >= 12:
            score += 1
        if any(c.isupper() for c in password):
            score += 1
        if any(c.islower() for c in password):
            score += 1
        if any(c.isdigit() for c in password):
            score += 1
        if any(not c.isalnum() for c in password):
            score += 1

        if score <= 2:
            strength = 'weak'
        elif score <= 4:
            strength = 'medium'
        else:
            strength = 'strong'

        return {'score': score, 'strength': strength}