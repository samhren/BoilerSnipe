import { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in on mount
    const token = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');

    if (token && storedUser) {
      const parsedUser = JSON.parse(storedUser);
      setUser(parsedUser);

      // Verify token is still valid
      authAPI.getCurrentUser()
        .then(response => {
          setUser(response.data);
          localStorage.setItem('user', JSON.stringify(response.data));
        })
        .catch(() => {
          logout();
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    try {
      const response = await authAPI.login({ email, password });
      const { access_token } = response.data;

      localStorage.setItem('token', access_token);

      // Get user info
      const userResponse = await authAPI.getCurrentUser();
      const userData = userResponse.data;

      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));


      return { success: true };
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Login failed';
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  const googleLogin = async (token) => {
    try {
      const response = await authAPI.googleLogin(token);
      const { access_token } = response.data;

      localStorage.setItem('token', access_token);

      // Get user info
      const userResponse = await authAPI.getCurrentUser();
      const userData = userResponse.data;

      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));


      return { success: true };
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Google login failed';
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  const register = async (userData) => {
    try {
      await authAPI.register(userData);

      // Auto-login after registration
      return await login(userData.email, userData.password);
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Registration failed';
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, googleLogin, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
