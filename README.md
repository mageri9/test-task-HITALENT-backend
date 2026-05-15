````markdown
# Organization Structure API

API для управления организационной структурой компании: подразделения и сотрудники с поддержкой древовидной иерархии.

---

## Особенности

- Древовидная структура подразделений
- Защита от циклов при изменении иерархии
- Два режима удаления: `cascade` и `reassign`
- Рекурсивная сериализация дерева подразделений
- Централизованная обработка ошибок
- Разделение слоёв: API / Services / ORM / Schemas
- Автоматическое применение миграций Alembic при старте контейнера
- Покрытие ключевой бизнес-логики тестами

---

## Технологии

- **FastAPI** — веб-фреймворк
- **SQLAlchemy 2.0** — ORM
- **Alembic** — миграции базы данных
- **PostgreSQL 16** — СУБД
- **Pydantic v2** — валидация и сериализация
- **pytest** — тестирование
- **Docker / Docker Compose** — контейнеризация

---

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/mageri9/test-task-HITALENT-backend.git
cd test-task-HITALENT-backend
````

### 2. Запустить проект

```bash
docker compose up --build
```

После запуска:

* API: `http://localhost:8000`
* Swagger UI: `http://localhost:8000/docs`
* ReDoc: `http://localhost:8000/redoc`

---

## Структура проекта

```text
app/
├── api/                 # FastAPI роутеры
│   └── v1/
├── core/                # конфиг, БД, exceptions, handlers
├── models/              # SQLAlchemy ORM модели
├── schemas/             # Pydantic схемы
├── services/            # бизнес-логика
└── main.py              # точка входа

alembic/                 # миграции БД
tests/                   # pytest тесты

Dockerfile
docker-compose.yml
entrypoint.sh
requirements.txt
```

---

## API Эндпоинты

| Метод    | Путь                           | Описание                         |
| -------- | ------------------------------ | -------------------------------- |
| `POST`   | `/departments/`                | Создать подразделение            |
| `GET`    | `/departments/{id}`            | Получить подразделение с деревом |
| `PATCH`  | `/departments/{id}`            | Обновить подразделение           |
| `DELETE` | `/departments/{id}`            | Удалить подразделение            |
| `POST`   | `/departments/{id}/employees/` | Создать сотрудника               |

---

## Параметры эндпоинтов

### GET `/departments/{id}`

| Параметр            | Тип  | Значение по умолчанию | Описание               |
| ------------------- | ---- | --------------------- | ---------------------- |
| `depth`             | int  | `1`                   | Глубина дерева (`1-5`) |
| `include_employees` | bool | `true`                | Включать сотрудников   |

---

### DELETE `/departments/{id}`

| Параметр                    | Тип    | Описание                     |
| --------------------------- | ------ | ---------------------------- |
| `mode`                      | string | `cascade` или `reassign`     |
| `reassign_to_department_id` | int    | ID департамента для переноса |

---

## Примеры запросов

### Создание корневого подразделения

```bash
curl -X POST http://localhost:8000/departments/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Engineering"
  }'
```

---

### Создание дочернего подразделения

```bash
curl -X POST http://localhost:8000/departments/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Backend",
    "parent_id": 1
  }'
```

---

### Получение дерева подразделений

```bash
curl "http://localhost:8000/departments/1?depth=3&include_employees=true"
```

---

### Обновление подразделения

```bash
curl -X PATCH http://localhost:8000/departments/2 \
  -H "Content-Type: application/json" \
  -d '{
    "parent_id": 3
  }'
```

---

### Создание сотрудника

```bash
curl -X POST http://localhost:8000/departments/1/employees/ \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "position": "Backend Developer"
  }'
```

---

### Каскадное удаление

```bash
curl -X DELETE \
"http://localhost:8000/departments/2?mode=cascade"
```

---

### Удаление с переносом

```bash
curl -X DELETE \
"http://localhost:8000/departments/2?mode=reassign&reassign_to_department_id=1"
```

---

## Архитектура

```text
API (routers)
        ↓
Services (business logic)
        ↓
Models (SQLAlchemy ORM)
        ↓
PostgreSQL

Schemas (Pydantic DTO / validation)

Core:
- config
- database
- exceptions
- handlers
```

---

## Принятые решения

### Сервисный слой

Бизнес-логика вынесена в отдельный слой `services`.

Роутеры остаются тонкими:

* принимают HTTP-запрос
* валидируют входные данные
* вызывают сервис
* возвращают ответ

Сервисы не зависят от FastAPI и HTTP.

---

### Сборка дерева подразделений

Для ограничения `depth ≤ 5` рекурсивный SQL CTE был признан избыточным.

Дерево собирается в Python из предварительно загруженных данных. Такой подход упрощает реализацию и делает её более читаемой для тестового задания.

---

### Защита от циклов

При изменении `parent_id` выполняется проверка:

* нельзя назначить подразделение родителем самому себе
* нельзя переместить подразделение в одного из своих потомков

При нарушении выбрасывается `409 Conflict`.

---

### Удаление в режиме `cascade`

Используется `ON DELETE CASCADE` на уровне базы данных:

* удаляются дочерние подразделения
* удаляются сотрудники подразделений

ORM использует `passive_deletes=True`, чтобы избежать двойного удаления.

---

### Удаление в режиме `reassign`

При удалении подразделения:

1. сотрудники переносятся в другой департамент
2. дочерние подразделения переподвешиваются к родителю удаляемого
3. подразделение удаляется

Все операции выполняются в одной транзакции.

При ошибке выполняется rollback.

---

### PATCH-семантика

Для частичного обновления используется:

```python
model_dump(exclude_unset=True)
```

Обновляются только переданные поля.

Поддерживается:

```json
{
  "parent_id": null
}
```

что делает подразделение корневым.

---

### Уникальность имён

В БД используется:

```sql
UNIQUE(parent_id, name)
```

Для корневых подразделений (`parent_id IS NULL`) PostgreSQL допускает одинаковые значения `name`, поскольку `NULL != NULL`.

В рамках тестового задания это дополнительно контролируется сервисным слоем.

В production-системе можно использовать partial unique index.

---

## Обработка ошибок

Приложение использует централизованную систему исключений.

| Исключение          | HTTP-код | Описание               |
| ------------------- | -------- | ---------------------- |
| `NotFoundException` | `404`    | Сущность не найдена    |
| `ConflictException` | `409`    | Конфликт бизнес-логики |

Ошибки валидации автоматически обрабатываются FastAPI/Pydantic и возвращают:

```http
422 Unprocessable Entity
```

---

## Тестирование

### Запуск тестов

```bash
docker compose exec app pytest -v
```

---

### Что покрыто тестами

* создание подразделений
* создание сотрудников
* валидация входных данных
* уникальность имён
* защита от циклов
* перемещение подразделений
* каскадное удаление
* удаление с переносом (`reassign`)

---

### Тестовая база данных

Тесты используют отдельную БД:

```text
org_structure_test
```

Миграции применяются автоматически через Alembic.

Между тестами таблицы очищаются через `TRUNCATE`.


---

## Переменные окружения

| Переменная          | Назначение              | Значение по умолчанию                                                |
| ------------------- | ----------------------- | -------------------------------------------------------------------- |
| `POSTGRES_USER`     | Пользователь PostgreSQL | `org_user`                                                           |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL       | `org_pass`                                                           |
| `POSTGRES_DB`       | Основная БД             | `org_structure`                                                      |
| `DATABASE_URL`      | URL подключения         | `postgresql+psycopg2://org_user:org_pass@db:5432/org_structure`      |
| `TEST_DATABASE_URL` | URL тестовой БД         | `postgresql+psycopg2://org_user:org_pass@db:5432/org_structure_test` |

---

## Healthcheck

```http
GET /health
```

Ответ:

```json
{
  "status": "ok"
}
```

---

## Запуск миграций вручную

```bash
docker compose exec app alembic upgrade head
```

Создание новой миграции:

```bash
docker compose exec app alembic revision --autogenerate -m "message"
```

---

## Автор

@mageri9

```
```
