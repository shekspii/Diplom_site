import { useState } from 'react'
import { Link } from 'react-router-dom'
import { clearAccessToken, getAccessToken } from './api.js'
import { SUBJECT_OPTIONS } from './subjects.js'

const highlights = [
  {
    title: 'Вы выбираете сценарий',
    text: 'Предмет и количество заданий задают траекторию тренировки прямо на главной странице.'
  },
  {
    title: 'Каждый вариант новый',
    text: 'Генератор случайно подбирает задания из базы, чтобы тесты не повторялись.'
  },
  {
    title: 'Подготовка ближе к экзамену',
    text: 'Ученик тренируется в формате, который помогает привыкнуть к реальному КИМ.'
  }
]

const features = [
  {
    title: 'Предметные наборы',
    text: 'Информатика, профильная математика, русский язык и другие дисциплины в одном интерфейсе.'
  },
  {
    title: 'Гибкая длина теста',
    text: 'Можно собрать короткую тренировку на 10 заданий или полноценный вариант для глубокой практики.'
  },
  {
    title: 'Случайная генерация',
    text: 'Сервис берёт задания из банка КИМ и формирует уникальный тест по выбранным параметрам.'
  },
  {
    title: 'Основа для аналитики',
    text: 'После генерации можно расширить платформу разбором ошибок, прогрессом и рекомендациями.'
  }
]

const timeline = [
  {
    step: '01',
    title: 'Выбор предмета',
    text: 'Пользователь указывает дисциплину, по которой хочет тренироваться.'
  },
  {
    step: '02',
    title: 'Настройка объема',
    text: 'На главной задаётся количество заданий под быструю или длинную сессию.'
  },
  {
    step: '03',
    title: 'Генерация варианта',
    text: 'Платформа собирает новый тест из базы экзаменационных заданий.'
  },
  {
    step: '04',
    title: 'Прохождение и разбор',
    text: 'Пользователь решает задачи и получает основу для дальнейшей подготовки.'
  }
]

const heroImage =
  'https://images.unsplash.com/photo-1513258496099-48168024aec0?auto=format&fit=crop&w=1200&q=80'
const visionImage =
  'https://images.unsplash.com/photo-1455390582262-044cdead277a?auto=format&fit=crop&w=1200&q=80'

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(Boolean(getAccessToken()))
  const [subject, setSubject] = useState(SUBJECT_OPTIONS[0])
  const [questionCount, setQuestionCount] = useState(20)
  const [surveyKey, setSurveyKey] = useState('')
  const [keyMessage, setKeyMessage] = useState('')
  const [keyError, setKeyError] = useState('')

  const estimatedMinutes = Math.max(20, questionCount * 3)
  const intensityLabel =
    questionCount <= 12 ? 'Быстрая тренировка' : questionCount <= 22 ? 'Стандартный вариант' : 'Глубокая практика'

  const handleLogout = () => {
    clearAccessToken()
    setIsAuthenticated(false)
  }

  const handleSurveyKeySubmit = (event) => {
    event.preventDefault()

    const normalizedKey = surveyKey.trim().toUpperCase()
    setSurveyKey(normalizedKey)

    if (!normalizedKey) {
      setKeyMessage('')
      setKeyError('Введите уникальный ключ опроса.')
      return
    }

    setKeyError('')
    setKeyMessage(`Ключ ${normalizedKey} сохранён. Переход к опросу подключим следующим шагом.`)
  }

  return (
    <div className="page">
      <header className="hero">
        <nav className="nav">
          <div className="brand">
            <span className="brand-dot" />
            TaskMixer
          </div>
          <div className="nav-links">
            <a href="#vision">Идея</a>
            <a href="#stack">Возможности</a>
            <a href="#flow">Путь ученика</a>
            {isAuthenticated ? (
              <>
                <Link className="ghost link-button" to="/profile">Личный кабинет</Link>
                <button className="ghost nav-button" type="button" onClick={handleLogout}>Выйти</button>
              </>
            ) : (
              <Link className="ghost link-button" to="/login">Войти</Link>
            )}
          </div>
        </nav>

        <div className="hero-grid">
          <div className="hero-copy">
            <p className="eyebrow">Генератор экзаменационных тренировок</p>
            <h1>
              Соберите свой вариант прямо на главной:
            </h1>
            <p className="lead">
              Платформа для подготовки к экзаменам на основе случайно формируемых
              тестов из банка заданий КИМ. Один экран, несколько вводных, новый
              тренировочный вариант за секунды.
            </p>
            <div className="hero-actions">
              <a className="secondary link-button" href="#stack">Как это работает</a>
            </div>
            <div className="hero-stats">
              <div>
                <span className="stat-value">{SUBJECT_OPTIONS.length}</span>
                <span className="stat-label">доступных предметов</span>
              </div>
              <div>
                <span className="stat-value">{questionCount}</span>
                <span className="stat-label">заданий в текущем варианте</span>
              </div>
              <div>
                <span className="stat-value">{estimatedMinutes} мин</span>
                <span className="stat-label">оценка времени на решение</span>
              </div>
            </div>

            
          </div>

          <div className="hero-panel">
            <div id="generator" className="panel-card generator-card">
              <div className="panel-header">
                <span className="panel-title">Параметры генерации</span>
                <span className="panel-pill">Онлайн</span>
              </div>

              <form className="generator-form">
                <label className="generator-label">
                  <span>Предмет</span>
                  <div className="select-shell">
                    <select value={subject} onChange={(event) => setSubject(event.target.value)}>
                      {SUBJECT_OPTIONS.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                    <span className="select-indicator" aria-hidden="true" />
                  </div>
                </label>

                <label className="generator-label">
                  <span>Количество заданий</span>
                  <div className="generator-range-wrap">
                    <input
                      type="range"
                      min="5"
                      max="30"
                      step="1"
                      value={questionCount}
                      onChange={(event) => setQuestionCount(Number(event.target.value))}
                    />
                    <div className="range-values">
                      <span>5</span>
                      <strong>{questionCount}</strong>
                      <span>30</span>
                    </div>
                  </div>
                </label>

                <div className="generator-preset-row">
                  {[10, 18, 25].map((count) => (
                    <button
                      key={count}
                      className={`preset-chip${questionCount === count ? ' active' : ''}`}
                      type="button"
                      onClick={() => setQuestionCount(count)}
                    >
                      {count} заданий
                    </button>
                  ))}
                </div>

                <button className="primary generator-submit" type="button">
                  Сгенерировать тест
                </button>
              </form>
            </div>

            <div className="panel-card mini access-card">
              <span className="panel-title">Чужой опрос по ключу</span>
              <form className="access-form" onSubmit={handleSurveyKeySubmit}>
                <label className="generator-label">
                  <span>Уникальный ключ опроса</span>
                  <input
                    type="text"
                    value={surveyKey}
                    onChange={(event) => setSurveyKey(event.target.value.toUpperCase())}
                    placeholder="Например, MATH7KQ2XZ"
                  />
                </label>
                <button className="secondary access-submit" type="submit">
                  Перейти к опросу
                </button>
              </form>
              {keyMessage && <div className="auth-message success">{keyMessage}</div>}
              {keyError && <div className="auth-message error">{keyError}</div>}
            </div>

            <div className="panel-card mini preview-card">
              <span className="panel-title">Превью варианта</span>
              <div className="preview-grid">
                <div className="preview-row">
                  <span>Предмет</span>
                  <strong>{subject}</strong>
                </div>
                <div className="preview-row">
                  <span>Формат</span>
                  <strong>{intensityLabel}</strong>
                </div>
                <div className="preview-row">
                  <span>Объем</span>
                  <strong>{questionCount} заданий</strong>
                </div>
                <div className="preview-row">
                  <span>Оценка времени</span>
                  <strong>{estimatedMinutes} минут</strong>
                </div>
              </div>
              <span className="panel-note">Новый набор заданий будет собран случайным образом из банка КИМ.</span>
            </div>
          </div>
        </div>
      </header>

      <section id="vision" className="section vision">
        <div className="section-head-grid">
          <div className="section-title">
            <h2>Главная работает как старт подготовки</h2>
            <p>
              Пользователь сразу видит главное действие сервиса: выбрать предмет,
              задать количество заданий и запустить генерацию экзаменационного теста.
            </p>
          </div>
        </div>
        <div className="highlight-grid">
          {highlights.map((item) => (
            <article key={item.title} className="highlight-card">
              <h3>{item.title}</h3>
              <p>{item.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="stack" className="section stack">
        <div className="section-title">
          <h2>Что даёт платформа</h2>
          <p>
            Интерфейс остаётся выразительным, но теперь главная страница не просто
            рассказывает о проекте, а помогает сразу начать тренировку.
          </p>
        </div>
        <div className="feature-grid">
          {features.map((item) => (
            <article key={item.title} className="feature-card">
              <div className="feature-dot" />
              <h3>{item.title}</h3>
              <p>{item.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="flow" className="section flow">
        <div className="section-title">
          <h2>Как выглядит сценарий</h2>
          <p>
            Взаимодействие построено вокруг простого пользовательского пути:
            настройка, генерация, решение, анализ.
          </p>
        </div>
        <div className="timeline">
          {timeline.map((item) => (
            <div key={item.step} className="timeline-step">
              <span className="step-number">{item.step}</span>
              <div>
                <h3>{item.title}</h3>
                <p>{item.text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="section cta">
        <div>
          <h2>Нужен быстрый старт перед экзаменом?</h2>
          <p>
            Откройте генератор, задайте предмет и объем теста, а система соберёт
            тренировочный вариант под ваш темп подготовки.
          </p>
        </div>
        <div className="cta-actions">
          <a className="primary link-button" href="#generator">Перейти к генератору</a>
          <a className="secondary link-button" href="/login">Личный кабинет</a>
        </div>
      </section>

      <footer className="footer">
        <div>
          <span className="brand">
            <span className="brand-dot" />
            TaskMixer
          </span>
          <p>Веб-платформа для генерации экзаменационных тренировочных тестов на основе заданий КИМ.</p>
        </div>
        <div className="footer-links">
          <a href="#vision">Идея</a>
          <a href="#stack">Возможности</a>
          <a href="#flow">Путь ученика</a>
          <a href="#generator">Генератор</a>
        </div>
      </footer>
    </div>
  )
}
