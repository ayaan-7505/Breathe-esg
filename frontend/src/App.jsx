import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import ToastContainer from './components/ToastContainer';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import IngestionPage from './pages/IngestionPage';
import IngestionDetailPage from './pages/IngestionDetailPage';
import AuditLogPage from './pages/AuditLogPage';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <ToastContainer />
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="ingestion" element={<IngestionPage />} />
              <Route path="ingestion/:jobId" element={<IngestionDetailPage />} />
              <Route path="audit" element={<AuditLogPage />} />
              <Route path="settings" element={<PlaceholderPage title="Settings" subtitle="Configuration options coming soon." />} />
              <Route path="help" element={<PlaceholderPage title="Help & Documentation" subtitle="Documentation and support resources." />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

function PlaceholderPage({ title, subtitle }) {
  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="empty-state">
        <h3>Under Construction</h3>
        <p>This section is being built. Check back soon for updates.</p>
      </div>
    </div>
  );
}
