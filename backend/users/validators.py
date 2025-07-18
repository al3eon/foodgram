import re

from django.core.exceptions import ValidationError


def username_validator(value):
    if value.lower() == 'me':
        raise ValidationError('Имя пользователя "me" использовать нельзя!')

    invalid_chars = re.sub(r'^[\w.@+-]+\Z', '', value)
    if invalid_chars:
        raise ValidationError(
            f'Имя пользователя содержит недопустимые символы: {invalid_chars}'
        )
    return value
