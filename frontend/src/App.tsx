import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { getToken } from './lib/api'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import SubscriptionsPage from './pages/SubscriptionsPage'
import ActionLogPage from './pages/ActionLogPage'
import SettingsPage from './pages/SettingsPage'
import PayPalApprovePage from './pages/paypal/PayPalApprovePage'
import PayPalReturnPage from './pages/paypal/PayPalReturnPage'
import PayPalCancelPage from './pages/paypal/PayPalCancelPage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  return getToken() ? <Layout>{children}</Layout> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      {/* PayPal approval loop routes - reachable with or without chrome */}
      <Route path="/paypal/approve/:actionId" element={<PayPalApprovePage />} />
      <Route path="/paypal/return" element={<PayPalReturnPage />} />
      <Route path="/paypal/cancel" element={<PayPalCancelPage />} />

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={
        <RequireAuth><DashboardPage /></RequireAuth>} />
      <Route path="/subscriptions" element={
        <RequireAuth><SubscriptionsPage /></RequireAuth>} />
      <Route path="/actions" element={
        <RequireAuth><ActionLogPage /></RequireAuth>} />
      <Route path="/settings" element={
        <RequireAuth><SettingsPage /></RequireAuth>} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
