from django.contrib.auth.models import AbstractUser
from django.db import models

from .validators import username_validator


LIMIT_EMAIL = 254
LIMIT_USERNAME = 150
OUTPUT_LENGTH = 30


class User(AbstractUser):
    email = models.EmailField(
        'Электронная почта',
        max_length=LIMIT_EMAIL,
        unique=True,
        error_messages={
            'unique': 'Пользователь с таким email уже существует!',
        },
    )

    username = models.CharField(
        'Имя пользователя',
        max_length=LIMIT_USERNAME,
        unique=True,
        help_text=f'Обязательное поле. Не более {LIMIT_USERNAME} символов. '
                  f'Только буквы, цифры и @/./+/-/_.',
        validators=[username_validator],
        error_messages={
            'unique': 'Пользователь с таким именем уже существует!',
        },
    )
    first_name = models.CharField(
        'Имя',
        max_length=LIMIT_USERNAME,
        blank=True
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=LIMIT_USERNAME,
        blank=True
    )

    avatar = models.ImageField(
        'Аватар',
        upload_to='users/',
        default='avatars/default.jpg',
        blank=True,
        null=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username[:OUTPUT_LENGTH]
