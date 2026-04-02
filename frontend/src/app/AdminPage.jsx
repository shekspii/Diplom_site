import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { apiRequest, clearAccessToken, getAccessToken } from './api.js'
import { SUBJECT_OPTIONS } from './subjects.js'

const EMPTY_OPTION = { text: '', is_correct: false }

const EMPTY_FORM = {
  subject: SUBJECT_OPTIONS[0],
  text: '',
  type: 'single',
  options: [{ ...EMPTY_OPTION }, { ...EMPTY_OPTION }]
}

function normalizeFormForType(type, options) {
  if (type === 'text') {
    return []
  }

  if (options.length >= 2) {
    return options
  }

  return [{ ...EMPTY_OPTION }, { ...EMPTY_OPTION }]
}

export default function AdminPage() {
  const queryClient = useQueryClient()
  const token = getAccessToken()
  const [bankForm, setBankForm] = useState(EMPTY_FORM)
  const [feedback, setFeedback] = useState('')
  const [errorMessage, setErrorMessage] = useState('')

  const meQuery = useQuery({
    queryKey: ['me'],
    queryFn: () => apiRequest('/auth/me', { auth: true }),
    enabled: Boolean(token)
  })

  const overviewQuery = useQuery({
    queryKey: ['admin-overview'],
    queryFn: () => apiRequest('/admin/overview', { auth: true }),
    enabled: Boolean(token && meQuery.data?.role === 'admin')
  })

  const bankQuery = useQuery({
    queryKey: ['admin-question-bank'],
    queryFn: () => apiRequest('/admin/question-bank', { auth: true }),
    enabled: Boolean(token && meQuery.data?.role === 'admin')
  })

  const sortedBankItems = useMemo(
    () => bankQuery.data?.items || [],
    [bankQuery.data]
  )

  const createBankQuestionMutation = useMutation({
    mutationFn: (payload) =>
      apiRequest('/admin/question-bank', {
        method: 'POST',
        auth: true,
        body: JSON.stringify(payload)
      }),
    onSuccess: async () => {
      setFeedback('Вопрос банка сохранён.')
      setErrorMessage('')
      setBankForm(EMPTY_FORM)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['admin-overview'] }),
        queryClient.invalidateQueries({ queryKey: ['admin-question-bank'] })
      ])
    },
    onError: (error) => {
      setFeedback('')
      setErrorMessage(error.message || 'Не удалось сохранить вопрос банка.')
    }
  })

  const handleLogout = () => {
    clearAccessToken()
    window.location.href = '/'
  }

  const handleTypeChange = (nextType) => {
    setBankForm((current) => ({
      ...current,
      type: nextType,
      options: normalizeFormForType(nextType, current.options)
    }))
  }

  const handleOptionChange = (index, field, value) => {
    setBankForm((current) => ({
      ...current,
      options: current.options.map((option, optionIndex) => {
        if (optionIndex !== index) {
          return option
        }

        return {
          ...option,
          [field]: value
        }
      })
    }))
  }

  const addOptionRow = () => {
    setBankForm((current) => ({
      ...current,
      options: [...current.options, { ...EMPTY_OPTION }]
    }))
  }

  const removeOptionRow = (index) => {
    setBankForm((current) => ({
      ...current,
      options: current.options.filter((_, optionIndex) => optionIndex !== index)
    }))
  }

  const handleSubmit = () => {
    createBankQuestionMutation.mutate({
      subject: bankForm.subject,
      text: bankForm.text,
      type: bankForm.type,
      options: bankForm.type === 'text' ? [] : bankForm.options
    })
  }

  if (!token) {
    return (
      <div className="builder-page">
        <div className="builder-guard">
          <h1>Админ-панель</h1>
          <p>Для доступа к панели администратора нужно войти в систему.</p>
          <div className="builder-guard-actions">
            <Link to="/login" className="primary link-button">Войти</Link>
            <Link to="/" className="secondary link-button">На главную</Link>
          </div>
        </div>
      </div>
    )
  }

  if (meQuery.isLoading) {
    return (
      <div className="builder-page">
        <div className="builder-guard">
          <h1>Админ-панель</h1>
          <p>Проверяем права доступа...</p>
        </div>
      </div>
    )
  }

  if (meQuery.error) {
    return (
      <div className="builder-page">
        <div className="builder-guard">
          <h1>Админ-панель</h1>
          <p>{meQuery.error.message}</p>
          <div className="builder-guard-actions">
            <Link to="/login" className="primary link-button">Войти заново</Link>
            <Link to="/" className="secondary link-button">На главную</Link>
          </div>
        </div>
      </div>
    )
  }

  if (meQuery.data?.role !== 'admin') {
    return (
      <div className="builder-page">
        <div className="builder-guard">
          <h1>Админ-панель</h1>
          <p>У вашей учетной записи нет прав администратора.</p>
          <div className="builder-guard-actions">
            <Link to="/profile" className="primary link-button">Личный кабинет</Link>
            <Link to="/" className="secondary link-button">На главную</Link>
          </div>
        </div>
      </div>
    )
  }

  const stats = overviewQuery.data?.stats
  const recentSurveys = overviewQuery.data?.recent_surveys || []
  const recentUsers = overviewQuery.data?.recent_users || []

  return (
    <div className="builder-page">
      <div className="admin-shell">
        <aside className="builder-sidebar">
          <div className="builder-sidebar-header">
            <div>
              <span className="brand">
                <span className="brand-dot" />
                TaskMixer
              </span>
              <h1>Админ-панель</h1>
            </div>
          </div>

          <div className="builder-meta admin-meta">
            <span>{meQuery.data.email}</span>
            <span className="admin-role-badge">admin</span>
          </div>

          <div className="admin-actions">
            <Link to="/" className="link-button secondary">На главную</Link>
            <Link to="/surveys/manage" className="link-button ghost">Конструктор</Link>
            <button className="ghost" type="button" onClick={handleLogout}>Выйти</button>
          </div>
        </aside>

        <main className="builder-main">
          <div className="builder-toolbar">
            <div>
              <h2>Обзор системы</h2>
              <p>Администратор может контролировать платформу и наполнять банк вопросов для генерации тестов по предметам.</p>
            </div>
          </div>

          {feedback && <div className="auth-message success">{feedback}</div>}
          {errorMessage && <div className="auth-message error">{errorMessage}</div>}

          {overviewQuery.isLoading && (
            <div className="auth-message">Загружаем данные админ-панели...</div>
          )}

          {overviewQuery.error && (
            <div className="auth-message error">{overviewQuery.error.message}</div>
          )}

          {stats && (
            <>
              <section className="builder-card">
                <div className="builder-card-header">
                  <div>
                    <h3>Основные метрики</h3>
                    <p>Сводка по пользователям, опросам, ответам и тестовой инфраструктуре.</p>
                  </div>
                </div>

                <div className="admin-stats-grid">
                  <div className="admin-stat-card">
                    <span>Пользователи</span>
                    <strong>{stats.users_count}</strong>
                  </div>
                  <div className="admin-stat-card">
                    <span>Администраторы</span>
                    <strong>{stats.admins_count}</strong>
                  </div>
                  <div className="admin-stat-card">
                    <span>Опросы</span>
                    <strong>{stats.surveys_count}</strong>
                  </div>
                  <div className="admin-stat-card">
                    <span>Опубликованные опросы</span>
                    <strong>{stats.published_surveys_count}</strong>
                  </div>
                  <div className="admin-stat-card">
                    <span>Ответы</span>
                    <strong>{stats.responses_count}</strong>
                  </div>
                  <div className="admin-stat-card">
                    <span>Вопросы банка</span>
                    <strong>{stats.bank_questions_count}</strong>
                  </div>
                  <div className="admin-stat-card">
                    <span>Активные вопросы банка</span>
                    <strong>{stats.active_bank_questions_count}</strong>
                  </div>
                  <div className="admin-stat-card">
                    <span>Тестовые сессии</span>
                    <strong>{stats.test_sessions_count}</strong>
                  </div>
                </div>
              </section>

              <section className="builder-card">
                <div className="builder-card-header">
                  <div>
                    <h3>Добавить вопрос в банк</h3>
                    <p>Эти вопросы не связаны с пользовательскими опросами и будут использоваться при генерации тестов с главной страницы.</p>
                  </div>
                </div>

                <div className="builder-form-grid">
                  <label>
                    Предмет
                    <select
                      value={bankForm.subject}
                      onChange={(event) => setBankForm((current) => ({ ...current, subject: event.target.value }))}
                    >
                      {SUBJECT_OPTIONS.map((subject) => (
                        <option key={subject} value={subject}>
                          {subject}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="builder-textarea-wrap">
                    Текст вопроса
                    <textarea
                      value={bankForm.text}
                      onChange={(event) => setBankForm((current) => ({ ...current, text: event.target.value }))}
                      placeholder="Введите формулировку вопроса"
                    />
                  </label>

                  <label>
                    Тип вопроса
                    <select
                      value={bankForm.type}
                      onChange={(event) => handleTypeChange(event.target.value)}
                    >
                      <option value="single">Один правильный ответ</option>
                      <option value="multiple">Несколько правильных ответов</option>
                      <option value="text">Текстовый ответ</option>
                    </select>
                  </label>
                </div>

                {bankForm.type !== 'text' && (
                  <div className="admin-options-editor">
                    <div className="builder-card-header">
                      <div>
                        <h3>Варианты ответа</h3>
                        <p>Отметьте правильные ответы. Для одиночного выбора должен быть отмечен ровно один вариант.</p>
                      </div>
                    </div>

                    <div className="admin-option-list">
                      {bankForm.options.map((option, index) => (
                        <div key={`${index}-${bankForm.type}`} className="admin-option-row">
                          <input
                            type="text"
                            value={option.text}
                            placeholder={`Вариант ${index + 1}`}
                            onChange={(event) => handleOptionChange(index, 'text', event.target.value)}
                          />
                          <label className="admin-checkbox">
                            <input
                              type="checkbox"
                              checked={option.is_correct}
                              onChange={(event) => handleOptionChange(index, 'is_correct', event.target.checked)}
                            />
                            <span>Правильный</span>
                          </label>
                          <button
                            className="ghost"
                            type="button"
                            onClick={() => removeOptionRow(index)}
                            disabled={bankForm.options.length <= 2}
                          >
                            Удалить
                          </button>
                        </div>
                      ))}
                    </div>

                    <button className="secondary" type="button" onClick={addOptionRow}>
                      Добавить вариант
                    </button>
                  </div>
                )}

                <div className="builder-actions-row">
                  <button
                    className="primary"
                    type="button"
                    onClick={handleSubmit}
                    disabled={createBankQuestionMutation.isPending || !bankForm.text.trim()}
                  >
                    Сохранить вопрос банка
                  </button>
                </div>
              </section>

              <section className="admin-columns">
                <div className="builder-card">
                  <div className="builder-card-header">
                    <div>
                      <h3>Последние опросы</h3>
                      <p>Новые пользовательские опросы и их текущий статус.</p>
                    </div>
                  </div>

                  <div className="admin-list">
                    {recentSurveys.map((survey) => (
                      <div key={survey.id} className="admin-list-item">
                        <div>
                          <strong>{survey.title}</strong>
                          <span>{survey.subject}</span>
                        </div>
                        <div className="admin-list-meta">
                          <span>{survey.status}</span>
                          <span>{survey.share_key}</span>
                        </div>
                      </div>
                    ))}
                    {!recentSurveys.length && (
                      <div className="builder-empty">Пока нет опросов.</div>
                    )}
                  </div>
                </div>

                <div className="builder-card">
                  <div className="builder-card-header">
                    <div>
                      <h3>Последние пользователи</h3>
                      <p>Новые аккаунты и их роль в системе.</p>
                    </div>
                  </div>

                  <div className="admin-list">
                    {recentUsers.map((user) => (
                      <div key={user.id} className="admin-list-item">
                        <div>
                          <strong>{user.email}</strong>
                          <span>ID: {user.id}</span>
                        </div>
                        <div className="admin-list-meta">
                          <span>{user.role}</span>
                        </div>
                      </div>
                    ))}
                    {!recentUsers.length && (
                      <div className="builder-empty">Пока нет пользователей.</div>
                    )}
                  </div>
                </div>
              </section>

              <section className="builder-card">
                <div className="builder-card-header">
                  <div>
                    <h3>Банк вопросов</h3>
                    <p>Список вопросов, которые администратор уже добавил для генерации тестов по предметам.</p>
                  </div>
                </div>

                {bankQuery.isLoading && (
                  <div className="auth-message">Загружаем банк вопросов...</div>
                )}

                {bankQuery.error && (
                  <div className="auth-message error">{bankQuery.error.message}</div>
                )}

                {!bankQuery.isLoading && !bankQuery.error && (
                  <div className="admin-bank-list">
                    {sortedBankItems.map((item) => (
                      <article key={item.id} className="admin-bank-card">
                        <div className="admin-bank-head">
                          <div>
                            <strong>{item.subject}</strong>
                            <span>{item.type}</span>
                          </div>
                          <span>{item.is_active ? 'active' : 'inactive'}</span>
                        </div>
                        <p>{item.text}</p>
                        {item.options.length > 0 && (
                          <div className="admin-bank-options">
                            {item.options.map((option) => (
                              <div key={option.id} className="admin-bank-option">
                                <span>#{option.position}</span>
                                <strong>{option.text}</strong>
                                <span>{option.is_correct ? 'correct' : 'option'}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </article>
                    ))}

                    {!sortedBankItems.length && (
                      <div className="builder-empty">Банк вопросов пока пуст.</div>
                    )}
                  </div>
                )}
              </section>
            </>
          )}
        </main>
      </div>
    </div>
  )
}
