# Foodgram

### Foodgram — это Django-проект, представляющий собой платформу для обмена кулинарными рецептами. Пользователи могут создавать, редактировать и просматривать рецепты, добавлять их в избранное и корзину покупок, а также подписываться на других пользователей.

## Описание проекта

### Foodgram позволяет пользователям:

- Создавать, редактировать и просматривать рецепты с ингредиентами, тегами и временем приготовления.
- Добавлять рецепты в избранное и корзину покупок.
- Подписываться на других пользователей.
- Создавать список продуктов, которые необходимы для приготовления нужных блюд

### Стек технологий:

* Python — разработка backend, версия 3.9
* Django — веб-фреймворк, версия 3.2
* Django REST Framework — создание API, версия 3.12
* JavaScript — разработка frontend
* React — фреймворк для frontend
* Nginx — веб-сервер и обратный прокси
* Docker — контейнеризация и деплой
* PostgreSQL — база данных
* GitHub Actions — автоматизация CI/CD
* npm — управление пакетами frontend

### Автор:

- **al3eon** (GitHub: [https://github.com/al3eon](https://github.com/al3eon))

### Развернутый проект:

- [https://kulinarka.site/](https://kulinarka.site/) 

## Установка и настройка

### 1. Клонирование репозитория:
```
git clone https://github.com/al3eon/foodgram
cd foodgram
```

### 2. Настройка переменных окружения:

Создайте файл .env в корне проекта и добавьте следующие переменные:
```
DB_ENGINE=django.db.backends.postgresql
DB_NAME=foodgram
POSTGRES_USER=foodgram_user
POSTGRES_PASSWORD=foodgram_password
DB_HOST=db
DB_PORT=5432
SECRET_KEY=your_django_secret_key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,foodgram.example.com
```

### 3. Запуск контейнеров:
```
docker compose up -d --build
```

### 4. Применение миграций в контейнере:
```
bashdocker exec -it foodgram-back python manage.py migrate
```
### 5. Загрузка тестовых данных:
```
bashdocker exec -it foodgram-back python manage.py load_data
```
### 6. Остановка и удаление контейнеров (при необходимости):
```
bashdocker compose down
```