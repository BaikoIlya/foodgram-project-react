![example workflow](https://github.com/BaikoIlya/foodgram-project-react/actions/workflows/foodgram_workflow.yml/badge.svg)

IP: 178.154.192.231

### Описание:
Проект Foodgram позволяет пользователям делиться рецептами и составлять список покупок для их приготовления.

### Установка:

Для начала вам необходимо сделать Fork данного проекта к себе в профиль.

Клонировать репозиторий и перейти в него в командной строке:

```
git clone https://github.com/<ваш_ник>/<Имя_проекта>.git
```

Перейти в настройки проекта и добавить Reppository Secrets

```
DB_ENGIINE= # Основа базы данных
DB_NAME= # Имя базы данных
POSTGRES_USER= # Супер прользователь для взаимодействия с базой
POSTGRES_PASSWORD= # Пароль для пользователя
DB_HOST= # Хост внутри контейнера для базы данных
DB_PORT= # Порт внутри контейра
DOCKER_USERNAME= #Имя пользователя для DOCKER HUB
DOCKER_PASSWORD= #Пароль от DOCKER HUB
HOST= # IP облачного сервиса
PASSPHRASE= # Пароль от приватного ключа
TELEGRAM_TO= # Id получателя сообщения в телеграм
TELEGRAM_TOKEN= #ID Telegram bota
```

Внесите изменения в файле /infra/docker-compose.yaml

```
backend:
  image: <ник Docker_hub>/<имя_проекта>:latest
```

Выполнить пушь проекта на github.

После получения сообщения об успешном развертывании, подключиться на удаленный сервер и выполнить миграции:

```
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
docker-compose exec backend python manage.py collectstatic --no-input 
```

Наполнить базу Ингредиентами:

```commandline
docker-compose exec backend python manage.py db_ingredients
```