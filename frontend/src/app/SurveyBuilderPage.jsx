import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { apiRequest, getAccessToken } from './api.js'
import { SUBJECT_OPTIONS } from './subjects.js'

const EMPTY_SURVEY = {
  title: '',
  subject: '',
  description: ''
}

const EMPTY_QUESTION = {
  text: '',
  type: 'single'
}

const NEW_SURVEY_ID = 'new'

function normalizeQuestionDrafts(questions) {
  return Object.fromEntries(
    questions.map((question) => [
      question.id,
      {
        text: question.text,
        type: question.type
      }
    ])
  )
}

function getAvailableSubjects(currentSubject) {
  if (currentSubject && !SUBJECT_OPTIONS.includes(currentSubject)) {
    return [currentSubject, ...SUBJECT_OPTIONS]
  }

  return SUBJECT_OPTIONS
}

export default function SurveyBuilderPage() {
  const queryClient = useQueryClient()
  const token = getAccessToken()
  const [selectedSurveyId, setSelectedSurveyId] = useState(null)
  const [isCreatingSurvey, setIsCreatingSurvey] = useState(false)
  const [surveyForm, setSurveyForm] = useState(EMPTY_SURVEY)
  const [newQuestion, setNewQuestion] = useState(EMPTY_QUESTION)
  const [questionDrafts, setQuestionDrafts] = useState({})
  const [optionDrafts, setOptionDrafts] = useState({})
  const [feedback, setFeedback] = useState('')
  const [errorMessage, setErrorMessage] = useState('')

  const isLocalDraft = selectedSurveyId === NEW_SURVEY_ID

  const meQuery = useQuery({
    queryKey: ['me'],
    queryFn: () => apiRequest('/auth/me', { auth: true }),
    enabled: Boolean(token)
  })

  const surveysQuery = useQuery({
    queryKey: ['my-surveys'],
    queryFn: () => apiRequest('/surveys/?filter=my&per_page=50', { auth: true }),
    enabled: Boolean(token)
  })

  const selectedSurveyQuery = useQuery({
    queryKey: ['survey', selectedSurveyId],
    queryFn: () => apiRequest(`/surveys/${selectedSurveyId}`, { auth: true }),
    enabled: Boolean(selectedSurveyId && selectedSurveyId !== NEW_SURVEY_ID && token)
  })

  const questionsQuery = useQuery({
    queryKey: ['survey-questions', selectedSurveyId],
    queryFn: () => apiRequest(`/questions/${selectedSurveyId}`, { auth: true }),
    enabled: Boolean(selectedSurveyId && selectedSurveyId !== NEW_SURVEY_ID && token)
  })

  const optionsQuery = useQuery({
    queryKey: ['survey-options', selectedSurveyId, questionsQuery.data],
    queryFn: async () => {
      const optionRequests = (questionsQuery.data || [])
        .filter((question) => question.type !== 'text')
        .map(async (question) => {
          const options = await apiRequest(`/questions/${question.id}/options`, { auth: true })
          return [question.id, options]
        })

      return Object.fromEntries(await Promise.all(optionRequests))
    },
    enabled: Boolean(
      selectedSurveyId &&
      selectedSurveyId !== NEW_SURVEY_ID &&
      token &&
      questionsQuery.data &&
      questionsQuery.data.length > 0
    )
  })

  const surveyList = surveysQuery.data?.surveys || []
  const questions = isLocalDraft ? [] : (questionsQuery.data || [])
  const optionMap = optionsQuery.data || {}
  const selectedSurveyStatus = isLocalDraft ? 'draft' : (selectedSurveyQuery.data?.status || 'draft')
  const isDraftSurvey = selectedSurveyStatus === 'draft'

  const canCreateOptions = useMemo(
    () => questions.some((question) => question.type !== 'text'),
    [questions]
  )
  const availableSubjects = useMemo(
    () => getAvailableSubjects(surveyForm.subject),
    [surveyForm.subject]
  )

  useEffect(() => {
    if (isCreatingSurvey) {
      return
    }

    if (!selectedSurveyId && surveyList.length > 0) {
      setSelectedSurveyId(surveyList[0].id)
    }
  }, [isCreatingSurvey, selectedSurveyId, surveyList])

  useEffect(() => {
    if (isLocalDraft) {
      setSurveyForm(EMPTY_SURVEY)
      setQuestionDrafts({})
      setOptionDrafts({})
      setNewQuestion(EMPTY_QUESTION)
      return
    }

    if (selectedSurveyQuery.data) {
      setSurveyForm({
        title: selectedSurveyQuery.data.title || '',
        subject: selectedSurveyQuery.data.subject || '',
        description: selectedSurveyQuery.data.description || ''
      })
    }
  }, [isLocalDraft, selectedSurveyQuery.data])

  useEffect(() => {
    if (questionsQuery.data && !isLocalDraft) {
      setQuestionDrafts(normalizeQuestionDrafts(questionsQuery.data))
    }
  }, [isLocalDraft, questionsQuery.data])

  const resetLocalDraft = () => {
    setIsCreatingSurvey(false)
    setSelectedSurveyId(surveyList[0]?.id || null)
    setSurveyForm(EMPTY_SURVEY)
    setQuestionDrafts({})
    setOptionDrafts({})
    setNewQuestion(EMPTY_QUESTION)
  }

  const showSuccess = (message) => {
    setFeedback(message)
    setErrorMessage('')
  }

  const showError = (error, fallbackMessage) => {
    setFeedback('')
    setErrorMessage(error?.message || fallbackMessage)
  }

  const invalidateSurveyData = async (surveyId = selectedSurveyId) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['my-surveys'] }),
      queryClient.invalidateQueries({ queryKey: ['survey', surveyId] }),
      queryClient.invalidateQueries({ queryKey: ['survey-questions', surveyId] }),
      queryClient.invalidateQueries({ queryKey: ['survey-options', surveyId] })
    ])
  }

  const createSurveyMutation = useMutation({
    mutationFn: (payload) =>
      apiRequest('/surveys/', {
        method: 'POST',
        auth: true,
        body: JSON.stringify(payload)
      }),
    onSuccess: async (data) => {
      showSuccess('Опрос сохранён.')
      setIsCreatingSurvey(false)
      await queryClient.invalidateQueries({ queryKey: ['my-surveys'] })
      setSelectedSurveyId(data.id)
    },
    onError: (error) => showError(error, 'Не удалось сохранить опрос.')
  })

  const saveSurveyMutation = useMutation({
    mutationFn: () =>
      apiRequest(`/surveys/${selectedSurveyId}`, {
        method: 'PUT',
        auth: true,
        body: JSON.stringify(surveyForm)
      }),
    onSuccess: async () => {
      showSuccess('Изменения опроса сохранены.')
      await invalidateSurveyData()
    },
    onError: (error) => showError(error, 'Не удалось сохранить изменения опроса.')
  })

  const deleteSurveyMutation = useMutation({
    mutationFn: (surveyId) =>
      apiRequest(`/surveys/${surveyId}`, {
        method: 'DELETE',
        auth: true
      }),
    onSuccess: async (_, deletedSurveyId) => {
      showSuccess('Опрос удалён.')
      const nextSurvey = surveyList.find((survey) => survey.id !== deletedSurveyId)
      await queryClient.invalidateQueries({ queryKey: ['my-surveys'] })
      setSelectedSurveyId(nextSurvey?.id || null)
      setSurveyForm(EMPTY_SURVEY)
      setQuestionDrafts({})
      setOptionDrafts({})
      setNewQuestion(EMPTY_QUESTION)
    },
    onError: (error) => showError(error, 'Не удалось удалить опрос.')
  })

  const publishSurveyMutation = useMutation({
    mutationFn: () =>
      apiRequest(`/surveys/${selectedSurveyId}/publish`, {
        method: 'POST',
        auth: true
      }),
    onSuccess: async () => {
      showSuccess('Опрос опубликован.')
      await invalidateSurveyData()
    },
    onError: (error) => showError(error, 'Не удалось опубликовать опрос.')
  })

  const closeSurveyMutation = useMutation({
    mutationFn: () =>
      apiRequest(`/surveys/${selectedSurveyId}/close`, {
        method: 'POST',
        auth: true
      }),
    onSuccess: async () => {
      showSuccess('Опрос закрыт.')
      await invalidateSurveyData()
    },
    onError: (error) => showError(error, 'Не удалось закрыть опрос.')
  })

  const addQuestionMutation = useMutation({
    mutationFn: () =>
      apiRequest(`/questions/${selectedSurveyId}`, {
        method: 'POST',
        auth: true,
        body: JSON.stringify({
          ...newQuestion,
          sequence: questions.length + 1
        })
      }),
    onSuccess: async () => {
      showSuccess('Вопрос добавлен.')
      setNewQuestion((current) => ({
        text: '',
        type: current.type
      }))
      await invalidateSurveyData()
    },
    onError: (error) => showError(error, 'Не удалось добавить вопрос.')
  })

  const updateQuestionMutation = useMutation({
    mutationFn: ({ questionId, payload }) =>
      apiRequest(`/questions/${questionId}`, {
        method: 'PUT',
        auth: true,
        body: JSON.stringify(payload)
      }),
    onSuccess: async () => {
      showSuccess('Вопрос обновлён.')
      await invalidateSurveyData()
    },
    onError: (error) => showError(error, 'Не удалось обновить вопрос.')
  })

  const deleteQuestionMutation = useMutation({
    mutationFn: (questionId) =>
      apiRequest(`/questions/${questionId}`, {
        method: 'DELETE',
        auth: true
      }),
    onSuccess: async () => {
      showSuccess('Вопрос удалён.')
      await invalidateSurveyData()
    },
    onError: (error) => showError(error, 'Не удалось удалить вопрос.')
  })

  const addOptionMutation = useMutation({
    mutationFn: ({ questionId, payload }) =>
      apiRequest(`/questions/${questionId}/options`, {
        method: 'POST',
        auth: true,
        body: JSON.stringify(payload)
      }),
    onSuccess: async (_, variables) => {
      showSuccess('Вариант ответа добавлен.')
      setOptionDrafts((current) => ({
        ...current,
        [variables.questionId]: {
          text: ''
        }
      }))
      await invalidateSurveyData()
    },
    onError: (error) => showError(error, 'Не удалось добавить вариант ответа.')
  })

  if (!token) {
    return (
      <div className="builder-page">
        <div className="builder-guard">
          <h1>Конструктор опросов</h1>
          <p>Эта страница доступна только авторизованным пользователям.</p>
          <div className="builder-guard-actions">
            <Link to="/login" className="primary link-button">Войти</Link>
            <Link to="/" className="secondary link-button">На главную</Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="builder-page">
      <div className="builder-shell">
        <aside className="builder-sidebar">
          <div className="builder-sidebar-header">
            <div>
              <span className="brand">
                <span className="brand-dot" />
                TaskMixer
              </span>
              <h1>Конструктор опросов</h1>
            </div>
            <button
              className="primary"
              type="button"
                onClick={() => {
                  setIsCreatingSurvey(true)
                  setSelectedSurveyId(NEW_SURVEY_ID)
                  setFeedback('')
                  setErrorMessage('')
                }}
              disabled={createSurveyMutation.isPending}
            >
              Новый опрос
            </button>
          </div>

          <div className="builder-meta">
            <span>{meQuery.data?.email || 'Авторизованный пользователь'}</span>
            <Link to="/profile" className="link-button ghost">К профилю</Link>
          </div>

          <div className="builder-list">
            {surveyList.map((survey) => (
              <button
                key={survey.id}
                className={`builder-list-item${selectedSurveyId === survey.id ? ' active' : ''}`}
                type="button"
                onClick={() => {
                  setIsCreatingSurvey(false)
                  setSelectedSurveyId(survey.id)
                  setFeedback('')
                  setErrorMessage('')
                }}
              >
                <strong>{survey.title}</strong>
                <small>{survey.subject || 'Без предмета'}</small>
                <span>{survey.status}</span>
              </button>
            ))}

            {isCreatingSurvey && (
              <button
                className={`builder-list-item${selectedSurveyId === NEW_SURVEY_ID ? ' active' : ''}`}
                type="button"
                onClick={() => setSelectedSurveyId(NEW_SURVEY_ID)}
              >
                <strong>Новый опрос</strong>
                <span>локальный черновик</span>
              </button>
            )}

            {surveysQuery.error && (
              <div className="auth-message error">
                {surveysQuery.error.message}
              </div>
            )}

            {!surveysQuery.isLoading && !surveysQuery.error && !surveyList.length && !isCreatingSurvey && (
              <div className="builder-empty">
                У вас пока нет опросов. Создайте первый черновик.
              </div>
            )}
          </div>
        </aside>

        <main className="builder-main">
          <div className="builder-toolbar">
            <div>
              <h2>Редактор опроса</h2>
              <p>Создавайте, редактируйте и публикуйте свои опросы в одном рабочем пространстве.</p>
            </div>
            {feedback && <div className="auth-message success">{feedback}</div>}
          </div>
          {errorMessage && <div className="auth-message error">{errorMessage}</div>}

          {selectedSurveyId ? (
            <>
              <section className="builder-card">
                <div className="builder-card-header">
                  <div>
                    <h3>Основная информация</h3>
                    <p>Задайте название, предмет, описание и управляйте статусом текущего опроса.</p>
                  </div>
                  <div className="builder-status">
                    <span>Статус: {selectedSurveyStatus}</span>
                    <span>Предмет: {surveyForm.subject.trim() || 'не выбран'}</span>
                    <span>
                      Ключ доступа: {isLocalDraft ? 'появится после сохранения' : (selectedSurveyQuery.data?.share_key || '—')}
                    </span>
                  </div>
                </div>

                <div className="builder-form-grid">
                  <label>
                    Название
                    <input
                      value={surveyForm.title}
                      onChange={(event) => setSurveyForm((current) => ({ ...current, title: event.target.value }))}
                      placeholder="Введите название опроса"
                    />
                  </label>
                  <label>
                    Предмет
                    <select
                      value={surveyForm.subject}
                      onChange={(event) => setSurveyForm((current) => ({ ...current, subject: event.target.value }))}
                    >
                      <option value="" disabled>Выберите предмет</option>
                      {availableSubjects.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="builder-textarea-wrap">
                    Описание
                    <textarea
                      value={surveyForm.description}
                      onChange={(event) => setSurveyForm((current) => ({ ...current, description: event.target.value }))}
                      placeholder="Кратко опишите цель опроса"
                    />
                  </label>
                </div>

                <div className="builder-actions-row">
                  <button
                    className="primary"
                    type="button"
                    onClick={() => {
                      if (isLocalDraft) {
                        createSurveyMutation.mutate({
                          title: surveyForm.title,
                          subject: surveyForm.subject,
                          description: surveyForm.description
                        })
                      } else {
                        saveSurveyMutation.mutate()
                      }
                    }}
                    disabled={
                      !surveyForm.title.trim() ||
                      !surveyForm.subject.trim() ||
                      !isDraftSurvey ||
                      createSurveyMutation.isPending ||
                      saveSurveyMutation.isPending
                    }
                  >
                    Сохранить опрос
                  </button>
                  <button
                    className="secondary"
                    type="button"
                    onClick={() => publishSurveyMutation.mutate()}
                    disabled={isLocalDraft || !isDraftSurvey || publishSurveyMutation.isPending}
                  >
                    Опубликовать
                  </button>
                  <button
                    className="ghost"
                    type="button"
                    onClick={() => {
                      if (isLocalDraft) {
                        resetLocalDraft()
                      } else {
                        deleteSurveyMutation.mutate(selectedSurveyId)
                      }
                    }}
                    disabled={deleteSurveyMutation.isPending}
                  >
                    {isLocalDraft ? 'Отменить' : 'Удалить'}
                  </button>
                  <button
                    className="ghost"
                    type="button"
                    onClick={() => closeSurveyMutation.mutate()}
                    disabled={isLocalDraft || selectedSurveyStatus !== 'published' || closeSurveyMutation.isPending}
                  >
                    Закрыть
                  </button>
                </div>
              </section>

              <section className="builder-card">
                <div className="builder-card-header">
                  <div>
                    <h3>Добавить вопрос</h3>
                    <p>Добавляйте вопросы и настраивайте порядок их показа в опросе.</p>
                  </div>
                </div>

                <div className="builder-question-form">
                  <label className="builder-textarea-wrap">
                    Текст вопроса
                    <textarea
                      value={newQuestion.text}
                      onChange={(event) => setNewQuestion((current) => ({ ...current, text: event.target.value }))}
                      placeholder="Напишите вопрос"
                    />
                  </label>
                  <label>
                    Тип вопроса
                    <select
                      value={newQuestion.type}
                      onChange={(event) => setNewQuestion((current) => ({ ...current, type: event.target.value }))}
                    >
                      <option value="single">Один вариант</option>
                      <option value="multiple">Несколько вариантов</option>
                      <option value="text">Текстовый ответ</option>
                    </select>
                  </label>
                  <button
                    className="primary"
                    type="button"
                    onClick={() => addQuestionMutation.mutate()}
                    disabled={isLocalDraft || !isDraftSurvey || addQuestionMutation.isPending}
                  >
                    Добавить вопрос
                  </button>
                </div>
              </section>

              <section className="builder-card">
                <div className="builder-card-header">
                  <div>
                    <h3>Вопросы опроса</h3>
                    <p>Редактируйте уже созданные вопросы и дополняйте их вариантами ответа.</p>
                  </div>
                  {canCreateOptions && (
                    <span className="builder-hint">
                      Для вопросов с выбором можно добавлять новые варианты ответа.
                    </span>
                  )}
                </div>

                <div className="builder-question-list">
                  {questions.map((question) => {
                    const draft = questionDrafts[question.id] || question
                    const optionDraft = optionDrafts[question.id] || { text: '' }
                    const options = optionMap[question.id] || []

                    return (
                      <article key={question.id} className="builder-question-card">
                        <div className="builder-question-grid">
                          <label className="builder-textarea-wrap">
                            Текст вопроса
                            <textarea
                              value={draft.text}
                              onChange={(event) =>
                                setQuestionDrafts((current) => ({
                                  ...current,
                                  [question.id]: {
                                    ...draft,
                                    text: event.target.value
                                  }
                                }))
                              }
                            />
                          </label>
                          <label>
                            Тип
                            <select
                              value={draft.type}
                              onChange={(event) =>
                                setQuestionDrafts((current) => ({
                                  ...current,
                                  [question.id]: {
                                    ...draft,
                                    type: event.target.value
                                  }
                                }))
                              }
                            >
                              <option value="single">Один вариант</option>
                              <option value="multiple">Несколько вариантов</option>
                              <option value="text">Текстовый ответ</option>
                            </select>
                          </label>
                        </div>

                        <div className="builder-actions-row">
                          <button
                            className="primary"
                            type="button"
                            onClick={() =>
                              updateQuestionMutation.mutate({
                                questionId: question.id,
                                payload: draft
                              })
                            }
                            disabled={isLocalDraft || !isDraftSurvey || updateQuestionMutation.isPending}
                          >
                            Сохранить вопрос
                          </button>
                          <button
                            className="ghost"
                            type="button"
                            onClick={() => deleteQuestionMutation.mutate(question.id)}
                            disabled={isLocalDraft || !isDraftSurvey || deleteQuestionMutation.isPending}
                          >
                            Удалить
                          </button>
                        </div>

                        {draft.type !== 'text' && (
                          <div className="builder-options-box">
                            <div className="builder-options-list">
                              {options.map((option) => (
                                <div key={option.id} className="builder-option-item">
                                  <span>#{option.position}</span>
                                  <strong>{option.text}</strong>
                                </div>
                              ))}
                              {!options.length && (
                                <div className="builder-empty">
                                  Для этого вопроса пока нет вариантов ответа.
                                </div>
                              )}
                            </div>

                            <div className="builder-option-form">
                              <input
                                value={optionDraft.text}
                                placeholder="Текст варианта"
                                onChange={(event) =>
                                  setOptionDrafts((current) => ({
                                    ...current,
                                    [question.id]: {
                                      text: event.target.value
                                    }
                                  }))
                                }
                              />
                              <button
                                className="secondary"
                                type="button"
                                onClick={() =>
                                  addOptionMutation.mutate({
                                    questionId: question.id,
                                    payload: {
                                      text: optionDraft.text,
                                      position: options.length + 1
                                    }
                                  })
                                }
                                disabled={isLocalDraft || !isDraftSurvey || addOptionMutation.isPending}
                              >
                                Добавить вариант
                              </button>
                            </div>
                          </div>
                        )}
                      </article>
                    )
                  })}

                  {!questions.length && (
                    <div className="builder-empty">
                      {isLocalDraft
                        ? 'Сначала сохраните опрос, затем можно будет добавлять вопросы.'
                        : 'В этом опросе пока нет вопросов.'}
                    </div>
                  )}
                </div>
              </section>
            </>
          ) : (
            <div className="builder-empty builder-empty-large">
              Выберите опрос слева или создайте новый черновик.
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
