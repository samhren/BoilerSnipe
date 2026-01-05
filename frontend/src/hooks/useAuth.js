import { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';
import { identifyUser, resetUser, trackEvent, EVENTS } from './usePostHog';

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
      // Identify user in PostHog on app load
      identifyUser(parsedUser.id?.toString() || parsedUser.email, {
        email: parsedUser.email,
      });
      // Verify token is still valid
      authAPI.getCurrentUser()
        .then(response => {
          setUser(response.data);
          localStorage.setItem('user', JSON.stringify(response.data));
          identifyUser(response.data.id?.toString() || response.data.email, {
            email: response.data.email,
          });
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
    trackEvent(EVENTS.LOGIN_ATTEMPTED, { email_domain: email.split('@')[1] });
    try {
      const response = await authAPI.login({ email, password });
      const { access_token } = response.data;

      localStorage.setItem('token', access_token);

      // Get user info
      const userResponse = await authAPI.getCurrentUser();
      const userData = userResponse.data;

      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));

      // Identify user in PostHog
      identifyUser(userData.id?.toString() || userData.email, {
        email: userData.email,
      });
      trackEvent(EVENTS.LOGIN_SUCCESS, { email_domain: email.split('@')[1] });

      return { success: true };
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Login failed';
      trackEvent(EVENTS.LOGIN_FAILED, {
        email_domain: email.split('@')[1],
        error: errorMessage,
      });
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  const register = async (userData) => {
    trackEvent(EVENTS.REGISTER_ATTEMPTED, { email_domain: userData.email.split('@')[1] });
    try {
      await authAPI.register(userData);
      trackEvent(EVENTS.REGISTER_SUCCESS, { email_domain: userData.email.split('@')[1] });

      // Auto-login after registration
      return await login(userData.email, userData.password);
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Registration failed';
      trackEvent(EVENTS.REGISTER_FAILED, {
        email_domain: userData.email.split('@')[1],
        error: errorMessage,
      });
      return {
        success: false,
        error: errorMessage
      };
    }
  };

  const logout = () => {
    trackEvent(EVENTS.LOGOUT);
    resetUser();
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
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
