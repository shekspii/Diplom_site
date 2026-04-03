# Exam Randomizer — платформа генерации тренировочных экзаменационных тестов
Проект представляет собой веб-сервис, который позволяет пользователям проходить тренировочные тесты, сформированные из базы экзаменационных заданий.

Пользователь может выбрать предмет и количество вопросов, после чего система автоматически формирует случайный набор заданий, максимально приближённый к реальному экзамену.

## Используемый стек технологий

### Backend:
-	Python
-	Flask
-	PostgreSQL
-	SQLAlchemy

### Frontend:
-	React
-	JavaScript
-	HTML
-	CSS
-	Axios

### Инструменты разработки:
-	Git
-	GitHub
-	pip
-	npm

## Архитектура проекта

Проект реализован с использованием слоистой архитектуры (Layered Architecture), которая разделяет приложение на следующие уровни:
-	слой пользовательского интерфейса;
-	слой API;
-	слой бизнес-логики;
-	слой работы с данными.

### Предполагаемая структура проекта:
```
.
├── README.md
├── backend
│   ├── app.py
│   ├── config.py
│   ├── extensions.py
│   ├── migrations
│   ├── models.py
│   ├── myenv
│   ├── postman
│   ├── requirements.txt
│   ├── routes
│   ├── seed.py
│   └── tests
└── frontend
    ├── dist
    ├── index.html
    ├── package.json
    ├── src
    │   ├── app
    │   │   ├── AdminPage.jsx
    │   │   ├── App.jsx
    │   │   ├── Login.jsx
    │   │   ├── Profile.jsx
    │   │   ├── Register.jsx
    │   │   ├── SurveyBuilderPage.jsx
    │   │   ├── SurveyTakePage.jsx
    │   │   ├── api.js
    │   │   └── subjects.js
    │   ├── assets
    │   ├── components
    │   ├── main.jsx
    │   └── styles
    │       └── global.css
    └── vite.config.js
```

