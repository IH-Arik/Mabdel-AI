import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import { useAuthStore } from './store/useAuthStore';
import { useEffect } from 'react';

// Real Pages
import Dashboard from './pages/Dashboard';
import Conversations from './pages/Conversations';
import Calls from './pages/Calls';
import AIWorkflow from './pages/AIWorkflow';
import Contacts from './pages/Contacts';
import BulkMessaging from './pages/BulkMessaging';
import Invoices from './pages/Invoices';
import Settings from './pages/Settings';
import LoginPage from './pages/Login';
import Calendar from './pages/Calendar';
import Documents from './pages/Documents';
import Integrations from './pages/Integrations';
import Notifications from './pages/Notifications';
import AdminPanel from './pages/AdminPanel';

function App() {
  const { isAuthenticated, checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={!isAuthenticated ? <LoginPage /> : <Navigate to="/" />} />
        <Route element={isAuthenticated ? <MainLayout /> : <Navigate to="/login" />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/conversations" element={<Conversations />} />
          <Route path="/calls" element={<Calls />} />
          <Route path="/ai-workflow" element={<AIWorkflow />} />
          <Route path="/contacts" element={<Contacts />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/bulk-messaging" element={<BulkMessaging />} />
          <Route path="/invoices" element={<Invoices />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/integrations" element={<Integrations />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/admin" element={<AdminPanel />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
