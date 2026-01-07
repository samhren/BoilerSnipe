import { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';
import { useUmami } from '@danielgtmn/umami-react';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const { track } = useUmami();

  /* Helper to identify user in Umami with retry */
  const identifyUser = (userData, retries = 5) => {
    if (!userData?.email) return;

    if (window.umami && window.umami.identify) {
      console.log('Umami identified user:', userData.email);
      window.umami.identify({ id: userData.email });
    } else if (retries > 0) {
      console.log(`Umami not ready, retrying identification (${retries} retries left)...`);
      setTimeout(() => identifyUser(userData, retries - 1), 1000);
    } else {
      console.warn('Umami failed to load for identification.');
    }
  };

  useEffect(() => {
    // Check if user is logged in on mount
    const token = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');

    if (token && storedUser) {
      const parsedUser = JSON.parse(storedUser);
      setUser(parsedUser);
      identifyUser(parsedUser);

      // Verify token is still valid
      authAPI.getCurrentUser()
        .then(response => {
          setUser(response.data);
          localStorage.setItem('user', JSON.stringify(response.data));
          identifyUser(response.data);
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
      identifyUser(userData);

      track('Login', { method: 'email' });

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
      identifyUser(userData);

      track('Login', { method: 'google' });

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
      track('Register', { email: userData.email });

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
    track('Logout');
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
