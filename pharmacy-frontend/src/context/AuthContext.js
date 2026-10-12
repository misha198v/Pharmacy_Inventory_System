import React, { createContext, useState, useCallback, useContext } from 'react';
import { authService } from '../services/auth.service';

export const AuthContext = createContext();

// Runs once at startup: is someone already logged in?
function loadStoredUser() {
  try {
    return JSON.parse(localStorage.getItem('pharmacy_user'));
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(loadStoredUser);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const login = useCallback(async (credentials) => {
    setIsLoading(true);
    setError('');
    try {
      const response = await authService.login(credentials);
      const { user: userData, token } = response.data;
      const savedUser = { ...userData, token };
      setUser(savedUser);
      localStorage.setItem('pharmacy_user', JSON.stringify(savedUser));
    } catch (err) {
      setError(
        err.response?.data?.detail || 'Could not reach the server. Is Django running?'
      );
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