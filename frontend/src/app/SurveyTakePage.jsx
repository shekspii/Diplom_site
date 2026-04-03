import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { apiRequest } from './api.js'

function buildInitialAnswers(questions) {
  return questions.reduce((accumulator, question) => {
    if (question.type === 'multiple') {
      accumulator[question.id] = []
      return accumulator
    }

    accumulator[question.id] = ''
    return accumulator
  }, {})
}

function buildAnswersPayload(questions, answers) {
  const payload = []

  for (const question of questions) {
    const value = answers[question.id]

    if (question.type === 'text') {
      const normalized = typeof value === 'string' ? value.trim() : ''
      if (normalized) {
        payload.push({
          question_id: question.id,
          text_answer: normalized
        })
      }
      continue
    }

    if (question.type === 'single') {
      if (value) {
        payload.push({
          question_id: question.id,
          option_ids: [Number(value)]
        })
      }
      continue
    }

    if (question.type === 'multiple') {
      if (Array.isArray(value) && value.length > 0) {
        payload.push({
          question_id: question.id,
          option_ids: value.map((item) => Number(item))
        })
      }
    }
  }

  return payload
}

export default function SurveyTakePage() {
  const { shareKey = '' } = useParams()
  const normalizedShareKey = shareKey.trim().toUpperCase()
  const [answers, setAnswers] = useState({})
  const [submitMessage, setSubmitMessage] = useState('')
  const [submitError, setSubmitError] = useState('')

  const surveyQuery = useQuery({
    queryKey: ['survey-by-key', normalizedShareKey],
    queryFn: () => apiRequest(`/surveys/access/${normalizedShareKey}`, { auth: true }),
    enabled: Boolean(normalizedShareKey)
  })

  const questions = surveyQuery.data?.questions ?? []

  const completionStats = useMemo(() => {
    let answeredCount = 0

    for (const question of questions) {
      const value = answers[question.id]

      if (question.type === 'text' && typeof value === 'string' && value.trim()) {
        answeredCount += 1
      }

      if (question.type === 'single' && value) {
        answeredCount += 1
      }

      if (question.type === 'multiple' && Array.isArray(value) && value.length > 0) {
        answeredCount += 1
      }
    }

    return {
      answeredCount,
      totalCount: questions.length
    }
  }, [answers, questions])

  const submitMutation = useMutation({
    mutationFn: (payload) =>
      apiRequest(`/surveys/access/${normalizedShareKey}/responses`, {
        method: 'POST',
        auth: true,
        body: JSON.stringify(payload)
      }),
    onSuccess: (data) => {
      setSubmitError('')
      setSubmitMessage(data.message || 'Опрос успешно отправлен.')
    },
    onError: (error) => {
      setSubmitMessage('')
      setSubmitError(error.message)
    }
  })

  const handleTextChange = (questionId, value) => {
    setAnswers((current) => ({
      ...current,
      [questionId]: value
    }))
  }

  const handleSingleChange = (questionId, optionId) => {
    setAnswers((current) => ({
      ...current,
      [questionId]: String(optionId)
    }))
  }

  const handleMultipleChange = (questionId, optionId, checked) => {
    setAnswers((current) => {
      const currentValues = Array.isArray(current[questionId]) ? current[questionId] : []
      const nextValues = checked
        ? [...currentValues, String(optionId)]
        : currentValues.filter((value) => value !== String(optionId))

      return {
        ...current,
        [questionId]: nextValues
      }
    })
  }

  const handleSubmit = (event) => {
    event.preventDefault()

    const payload = buildAnswersPayload(questions, answers)
    if (payload.length === 0) {
      setSubmitMessage('')
      setSubmitError('Заполните хотя бы один ответ перед отправкой.')
      return
    }

    setSubmitError('')
    setSubmitMessage('')
    submitMutation.mutate({ answers: payload })
  }

  const handleReset = () => {
    setAnswers(buildInitialAnswers(questions))
    setSubmitError('')
    setSubmitMessage('')
  }

  if (surveyQuery.isLoading) {
    return (
      <div className="survey-take-page">
        <div className="survey-take-shell">
          <div className="survey-loading-card">Загружаем опрос по ключу {normalizedShareKey}...</div>
        </div>
      </div>
    )
  }

  if (surveyQuery.isError) {
    return (
      <div className="survey-take-page">
        <div className="survey-take-shell">
          <div className="survey-error-card">
            <h1>Опрос не найден</h1>
            <p>{surveyQuery.error.message}</p>
            <Link className="secondary link-button" to="/">
              Вернуться на главную
            </Link>
          </div>
        </div>
      </div>
    )
  }

  const survey = surveyQuery.data

  return (
    <div className="survey-take-page">
      <div className="survey-take-shell">
        <header className="survey-take-header">
          <div>
            <p className="eyebrow">Прохождение опроса</p>
            <h1>{survey.title}</h1>
            <p className="survey-take-description">
              {survey.description || 'Описание опроса не указано. Просто ответьте на вопросы и отправьте форму.'}
            </p>
          </div>
          <div className="survey-meta-card">
            <div className="survey-meta-row">
              <span>Предмет</span>
              <strong>{survey.subject}</strong>
            </div>
            <div className="survey-meta-row">
              <span>Ключ</span>
              <strong>{survey.share_key}</strong>
            </div>
            <div className="survey-meta-row">
              <span>Вопросов</span>
              <strong>{questions.length}</strong>
            </div>
            <div className="survey-meta-row">
              <span>Заполнено</span>
              <strong>
                {completionStats.answeredCount} из {completionStats.totalCount}
              </strong>
            </div>
          </div>
        </header>

        <form className="survey-form-card" onSubmit={handleSubmit}>
          {questions.map((question) => (
            <section key={question.id} className="survey-question-block">
              <div className="survey-question-head">
                <span className="survey-question-number">Вопрос {question.sequence}</span>
                <h2>{question.text}</h2>
              </div>

              {question.type === 'text' && (
                <textarea
                  className="survey-textarea"
                  value={answers[question.id] ?? ''}
                  onChange={(event) => handleTextChange(question.id, event.target.value)}
                  placeholder="Введите ваш ответ"
                  rows={4}
                  disabled={submitMutation.isPending || Boolean(submitMessage)}
                />
              )}

              {question.type === 'single' && (
                <div className="survey-option-list">
                  {question.options.map((option) => (
                    <label key={option.id} className="survey-option-card">
                      <input
                        type="radio"
                        name={`question-${question.id}`}
                        value={option.id}
                        checked={String(answers[question.id] ?? '') === String(option.id)}
                        onChange={() => handleSingleChange(question.id, option.id)}
                        disabled={submitMutation.isPending || Boolean(submitMessage)}
                      />
                      <span>{option.text}</span>
                    </label>
                  ))}
                </div>
              )}

              {question.type === 'multiple' && (
                <div className="survey-option-list">
                  {question.options.map((option) => (
                    <label key={option.id} className="survey-option-card">
                      <input
                        type="checkbox"
                        value={option.id}
                        checked={Array.isArray(answers[question.id]) && answers[question.id].includes(String(option.id))}
                        onChange={(event) =>
                          handleMultipleChange(question.id, option.id, event.target.checked)
                        }
                        disabled={submitMutation.isPending || Boolean(submitMessage)}
                      />
                      <span>{option.text}</span>
                    </label>
                  ))}
                </div>
              )}
            </section>
          ))}

          <div className="survey-form-actions">
            <button
              className="ghost nav-button"
              type="button"
              onClick={handleReset}
              disabled={submitMutation.isPending}
            >
              Сбросить ответы
            </button>
            <button className="primary generator-submit" type="submit" disabled={submitMutation.isPending || Boolean(submitMessage)}>
              {submitMutation.isPending ? 'Отправляем...' : 'Отправить опрос'}
            </button>
          </div>

          {submitMessage && <div className="auth-message success">{submitMessage}</div>}
          {submitError && <div className="auth-message error">{submitError}</div>}
        </form>

        <div className="survey-take-footer">
          <Link className="secondary link-button" to="/">
            На главную
          </Link>
        </div>
      </div>
    </div>
  )
}
