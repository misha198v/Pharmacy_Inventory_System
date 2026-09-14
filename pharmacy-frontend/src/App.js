import React, { Suspense, lazy } from 'react';
import LoadingSpinner from './components/Common/LoadingSpinner';

const Dashboard = lazy(() => import('./components/Dashboard/Dashboard'));
const LoginForm = lazy(() => import('./components/Auth/LoginForm'));

export default function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      {user ? <Dashboard /> : <LoginForm />}
    </Suspense>
  );
}