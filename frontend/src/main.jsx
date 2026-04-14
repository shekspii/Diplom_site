import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './app/App.jsx'
import Login from './app/Login.jsx'
import Register from './app/Register.jsx'
import Profile from './app/Profile.jsx'
import AdminPage from './app/AdminPage.jsx'
import SurveyBuilderPage from './app/SurveyBuilderPage.jsx'
import SurveyTakePage from './app/SurveyTakePage.jsx'
import './styles/global.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false
    }
  }
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/surveys/manage" element={<SurveyBuilderPage />} />
          <Route path="/survey/access/:shareKey" element={<SurveyTakePage />} />
          <Route path="/tests/sessions/:sessionId" element={<SurveyTakePage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
)
