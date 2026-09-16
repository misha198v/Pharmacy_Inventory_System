import React, { Suspense, lazy } from 'react';
import LoadingSpinner from './components/Common/LoadingSpinner';
import { AuthProvider, useAuth } from './context/AuthContext';

const Dashboard = lazy(() => import('./components/Dashboard/Dashboard'));
const LoginForm = lazy(() => import('./components/Auth/LoginForm'));

function AppContent() {
  const { user } = useAuth();

  return (
    <Suspense fallback={<LoadingSpinner />}>
      {user ? <Dashboard /> : <LoginForm />}
    </Suspense>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}