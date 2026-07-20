import { createContext, useState, useEffect, useContext, useRef, useCallback } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [isAuthenticated, setIsAuthenticated] = useState(!!token);
  const navigate = useNavigate();

  // Use ref to avoid stale closure in axios interceptor
  const logoutRef = useRef();

  const logout = useCallback(() => {
    setToken(null);
    navigate('/login');
  }, [navigate]);

  logoutRef.current = logout;

  // Setup axios interceptor to attach token to all requests
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      localStorage.setItem('token', token);
      setIsAuthenticated(true);
    } else {
      delete axios.defaults.headers.common['Authorization'];
      localStorage.removeItem('token');
      setIsAuthenticated(false);
    }
  }, [token]);

  // Handle global 401 errors (token expired or invalid)
  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response && error.response.status === 401) {
          logoutRef.current();
        }
        return Promise.reject(error);
      }
    );
    return () => axios.interceptors.response.eject(interceptor);
  }, []);

  const login = async (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const response = await axios.post(`${API_URL}/auth/login`, formData);
    setToken(response.data.access_token);
    navigate('/');
  };

  const register = async (username, password) => {
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    await axios.post(`${API_URL}/auth/register`, { username, password });
    await login(username, password); // auto-login after register
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);

