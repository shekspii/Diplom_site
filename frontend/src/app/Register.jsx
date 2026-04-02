import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { apiRequest } from './api.js'

export default function Register() {
  const navigate = useNavigate()
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')

  const handleSubmit = async (event) => {
    event.preventDefault()
    setStatus('loading')
    setError('')

    const formData = new FormData(event.currentTarget)
    const payload = {
      email: formData.get('email'),
      password: formData.get('password')
    }

    try {
      await apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify(payload)
      })
      setStatus('success')
      window.setTimeout(() => navigate('/login'), 800)
    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-topbar">
          <Link to="/" className="link-button ghost">На главную</Link>
        </div>
        <div className="auth-header">
          <span className="brand">
            <span className="brand-dot" />
            ExamForge
          </span>
          <h1>Регистрация</h1>
          <p>
            Создайте аккаунт, чтобы сохранять результаты и формировать
            персональные тренировки.
          </p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Имя
            <input name="name" type="text" placeholder="Ирина" required />
          </label>
          <label>
            Email
            <input name="email" type="email" placeholder="student@mail.ru" required />
          </label>
          <label>
            Пароль
            <input name="password" type="password" placeholder="••••••••" required />
          </label>
          <button className="primary" type="submit" disabled={status === 'loading'}>
            {status === 'loading' ? 'Создаем...' : 'Создать аккаунт'}
          </button>
          {status === 'success' && (
            <div className="auth-message success">Регистрация успешна. Теперь можно войти.</div>
          )}
          {error && <div className="auth-message error">{error}</div>}
        </form>

        <div className="auth-footer">
          <span>Уже есть аккаунт?</span>
          <Link to="/login">Войти</Link>
        </div>
      </div>
    </div>
  )
}
