import React, { createContext, useState, useCallback, useContext } from 'react';

export const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const login = useCallback(async (credentials) => {
  setIsLoading(true);
  setError('');
  try {
    const response = await fetch('http://localhost:8000/api/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error('Invalid username or password');
    }

    const data = await response.json();
    setUser(data.user);
    localStorage.setItem('pharmacy_user', JSON.stringify(data.user));
  } catch (err) {
    setError(err.message);
  } finally {
    setIsLoading(false);
  }
}, []);
  

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem('pharmacy_user');
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, error, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
