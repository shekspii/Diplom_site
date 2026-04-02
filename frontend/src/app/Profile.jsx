import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { apiRequest, clearAccessToken } from './api.js'

export default function Profile() {
  const navigate = useNavigate()
  const { data, error, isLoading } = useQuery({
    queryKey: ['me'],
    queryFn: () => apiRequest('/auth/me', { auth: true })
  })

  useEffect(() => {
    if (data?.role === 'admin') {
      navigate('/admin', { replace: true })
    }
  }, [data, navigate])

  const handleLogout = () => {
    clearAccessToken()
    window.location.href = '/'
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
          <h1>Личный кабинет</h1>
          <p>Проверка авторизации и точка входа в тренировочные тесты.</p>
        </div>

        {isLoading && <div className="auth-message">Загружаем профиль...</div>}

        {error && (
          <div className="auth-message error">
            {error.message}
          </div>
        )}

        {data && (
          <div className="profile-card">
            <div className="profile-row">
              <span>ID</span>
              <strong>{data.id}</strong>
            </div>
            <div className="profile-row">
              <span>Email</span>
              <strong>{data.email}</strong>
            </div>
            <div className="profile-row">
              <span>Роль</span>
              <strong>{data.role}</strong>
            </div>
          </div>
        )}

        <div className="auth-footer auth-footer-actions">
          <Link to="/surveys/manage" className="link-button secondary">Мои опросы</Link>
          <Link to="/" className="link-button secondary">К тестам</Link>
          <button className="ghost" type="button" onClick={handleLogout}>Выйти</button>
        </div>
      </div>
    </div>
  )
}
