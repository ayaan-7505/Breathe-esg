import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { authAPI } from '../api/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('breathe_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('breathe_token'));
  const [loading, setLoading] = useState(false);

  const isAuthenticated = !!token && !!user;

  const login = useCallback(async (email, password) => {
    setLoading(true);
    try {
      const data = await authAPI.login(email, password);
      const authToken = data.token || data.access;
      const userData = data.user || { email, name: email.split('@')[0] };

      localStorage.setItem('breathe_token', authToken);
      localStorage.setItem('breathe_user', JSON.stringify(userData));
      if (data.tenant_id) {
        localStorage.setItem('breathe_tenant_id', data.tenant_id);
      }

      setToken(authToken);
      setUser(userData);
      return { success: true };
    } catch (error) {
      const message = error.response?.data?.detail ||
                      error.response?.data?.message ||
                      'Invalid credentials. Please try again.';
      return { success: false, error: message };
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await authAPI.logout();
    } catch {
      // ignore logout errors
    }
    localStorage.removeItem('breathe_token');
    localStorage.removeItem('breathe_user');
    localStorage.removeItem('breathe_tenant_id');
    setToken(null);
    setUser(null);
  }, []);

  const value = {
    user,
    token,
    isAuthenticated,
    loading,
    login,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
