import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { apiRequest } from './api.js'

export default function Login() {
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
      const data = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify(payload)
      })
      localStorage.setItem('access_token', data.access_token)
      setStatus('success')
      navigate(data.user?.role === 'admin' ? '/admin' : '/profile')
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
          <h1>Вход в кабинет</h1>
          <p>
            Возвращайтесь к тренировкам: отслеживайте прогресс и создавайте
            новые тесты.
          </p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Email
            <input name="email" type="email" placeholder="student@mail.ru" required />
          </label>
          <label>
            Пароль
            <input name="password" type="password" placeholder="••••••••" required />
          </label>
          <button className="primary" type="submit" disabled={status === 'loading'}>
            {status === 'loading' ? 'Входим...' : 'Войти'}
          </button>
          {status === 'success' && (
            <div className="auth-message success">Вход выполнен. Можно перейти к тестам.</div>
          )}
          {error && <div className="auth-message error">{error}</div>}
        </form>

        <div className="auth-footer">
          <span>Еще нет аккаунта?</span>
          <Link to="/register">Создать</Link>
        </div>
      </div>
    </div>
  )
}
