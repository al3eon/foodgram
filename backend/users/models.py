from django.contrib.auth.models import AbstractUser
from django.db import models

from .constants import LIMIT_EMAIL, LIMIT_USERNAME, OUTPUT_LENGTH
from .validators import username_validator


class User(AbstractUser):
    email = models.EmailField(
        max_length=LIMIT_EMAIL,
        unique=True,
        error_messages={
            'unique': 'Пользователь с таким email уже существует!',
        },
        verbose_name='Электронная почта',
    )

    username = models.CharField(
        max_length=LIMIT_USERNAME,
        unique=True,
        help_text=f'Обязательное поле. Не более {LIMIT_USERNAME} символов. '
                  f'Только буквы, цифры и @/./+/-/_.',
        validators=[username_validator],
        error_messages={
            'unique': 'Пользователь с таким именем уже существует!',
        },
        verbose_name='Имя пользователя',
    )
    first_name = models.CharField(
        verbose_name='Имя',
        max_length=LIMIT_USERNAME,
        blank=False,
        null=False,
    )
    last_name = models.CharField(
        max_length=LIMIT_USERNAME,
        verbose_name='Фамилия',
        blank=False,
        null=False,
    )

    avatar = models.ImageField(
        upload_to='users/',
        verbose_name='Аватар',
        blank=True,
        null=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username[:OUTPUT_LENGTH]


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name='Автор'
    )

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'], name='unique_subscription'),
            models.CheckConstraint(
                name='no_self_subscription',
                check=~models.Q(user=models.F('author'))
            )
        ]

    def __str__(self):
        return f'{self.user} -> {self.author}'
