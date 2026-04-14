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

    if (question.type === 'multiple' && Array.isArray(value) && value.length > 0) {
      payload.push({
        question_id: question.id,
        option_ids: value.map((item) => Number(item))
      })
    }
  }

  return payload
}

export default function SurveyTakePage() {
  const { shareKey = '', sessionId = '' } = useParams()
  const normalizedShareKey = shareKey.trim().toUpperCase()
  const isGeneratedTest = Boolean(sessionId)
  const [answers, setAnswers] = useState({})
  const [submitMessage, setSubmitMessage] = useState('')
  const [submitError, setSubmitError] = useState('')
  const [submissionResult, setSubmissionResult] = useState(null)

  const contentQuery = useQuery({
    queryKey: isGeneratedTest
      ? ['generated-test-session', sessionId]
      : ['survey-by-key', normalizedShareKey],
    queryFn: () =>
      isGeneratedTest
        ? apiRequest(`/tests/sessions/${sessionId}`, { auth: true })
        : apiRequest(`/surveys/access/${normalizedShareKey}`, { auth: true }),
    enabled: isGeneratedTest ? Boolean(sessionId) : Boolean(normalizedShareKey)
  })

  const questions = contentQuery.data?.questions ?? []
  const title = contentQuery.data?.title || (isGeneratedTest ? 'Тренировочный тест' : 'Опрос')
  const resultSummary = submissionResult || contentQuery.data?.submission || null

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
      apiRequest(
        isGeneratedTest ? `/tests/sessions/${sessionId}/submit` : `/surveys/access/${normalizedShareKey}/responses`,
        {
          method: 'POST',
          auth: true,
          body: JSON.stringify(payload)
        }
      ),
    onSuccess: (data) => {
      setSubmitError('')
      setSubmissionResult(data.submission || null)
      setSubmitMessage(data.message || (isGeneratedTest ? 'Тест успешно отправлен.' : 'Опрос успешно отправлен.'))
    },
    onError: (error) => {
      setSubmissionResult(null)
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
    setSubmissionResult(null)
  }

  if (contentQuery.isLoading) {
    return (
      <div className="survey-take-page">
        <div className="survey-take-shell">
          <div className="survey-loading-card">
            {isGeneratedTest ? `Загружаем тест #${sessionId}...` : `Загружаем опрос по ключу ${normalizedShareKey}...`}
          </div>
        </div>
      </div>
    )
  }

  if (contentQuery.isError) {
    return (
      <div className="survey-take-page">
        <div className="survey-take-shell">
          <div className="survey-error-card">
            <h1>{isGeneratedTest ? 'Тест не найден' : 'Опрос не найден'}</h1>
            <p>{contentQuery.error.message}</p>
            <Link className="secondary link-button" to="/">
              Вернуться на главную
            </Link>
          </div>
        </div>
      </div>
    )
  }

  const content = contentQuery.data

  return (
    <div className="survey-take-page">
      <div className="survey-take-shell">
        <header className="survey-take-header">
          <div>
            <p className="eyebrow">{isGeneratedTest ? 'Прохождение теста' : 'Прохождение опроса'}</p>
            <h1>{title}</h1>
            <p className="survey-take-description">
              {content.description || 'Описание не указано. Просто ответьте на вопросы и отправьте форму.'}
            </p>
          </div>
          <div className="survey-meta-card">
            <div className="survey-meta-row">
              <span>Предмет</span>
              <strong>{content.subject}</strong>
            </div>
            {!isGeneratedTest && content.share_key && (
              <div className="survey-meta-row">
                <span>Ключ</span>
                <strong>{content.share_key}</strong>
              </div>
            )}
            {isGeneratedTest && (
              <div className="survey-meta-row">
                <span>Сессия</span>
                <strong>#{content.id}</strong>
              </div>
            )}
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
                <span className="survey-question-number">
                  {isGeneratedTest && question.exam_task_number
                    ? `Задание ${question.exam_task_number}`
                    : `Вопрос ${question.sequence}`}
                </span>
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
            <button
              className="primary generator-submit"
              type="submit"
              disabled={submitMutation.isPending || Boolean(submitMessage)}
            >
              {submitMutation.isPending
                ? 'Отправляем...'
                : isGeneratedTest
                  ? 'Отправить тест'
                  : 'Отправить опрос'}
            </button>
          </div>

          {submitMessage && <div className="auth-message success">{submitMessage}</div>}
          {submitError && <div className="auth-message error">{submitError}</div>}
        </form>

        {isGeneratedTest && resultSummary && (
          <section className="survey-results-card">
            <div className="builder-card-header">
              <div>
                <h3>Разбор результата</h3>
                <p>
                  Верно решено {resultSummary.score} из {resultSummary.total_questions}.
                </p>
              </div>
            </div>

            <div className="survey-results-list">
              {resultSummary.breakdown.map((item) => (
                <article
                  key={item.question_id}
                  className={`survey-result-item${item.is_correct ? ' correct' : ' incorrect'}`}
                >
                  <div className="survey-result-head">
                    <span>
                      Задание {item.exam_task_number || item.sequence}
                    </span>
                    <strong>{item.is_correct ? 'Верно' : item.is_answered ? 'Неверно' : 'Нет ответа'}</strong>
                  </div>
                  <p>{item.text}</p>
                  <div className="survey-result-meta">
                    <span>Ваш ответ</span>
                    <strong>
                      {Array.isArray(item.user_answer)
                        ? item.user_answer.join(', ') || 'Нет ответа'
                        : item.user_answer || 'Нет ответа'}
                    </strong>
                  </div>
                  <div className="survey-result-meta">
                    <span>Правильный ответ</span>
                    <strong>
                      {Array.isArray(item.correct_answer)
                        ? item.correct_answer.join(', ')
                        : item.correct_answer || 'Не указан'}
                    </strong>
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}

        <div className="survey-take-footer">
          <Link className="secondary link-button" to="/">
            На главную
          </Link>
        </div>
      </div>
    </div>
  )
}
