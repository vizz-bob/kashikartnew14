import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [isAdmin, setIsAdmin] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadAuth = () => {
      const initAdmin = JSON.parse(localStorage.getItem('is_superuser') || 'false');
      const profileEmail = localStorage.getItem('profileEmail');
      setIsAdmin(initAdmin);
      if (profileEmail) {
        setUser({
          name: localStorage.getItem('profileName') || '',
          email: profileEmail,
        });
      } else {
        setUser(null);
      }
    };
    loadAuth();
    setLoading(false);
  }, []);

  useEffect(() => {
    const handleStorageChange = (e) => {
      if (e.key === 'is_superuser') {
        setIsAdmin(JSON.parse(e.newValue || 'false'));
      }
      if (e.key === 'profileEmail') {
        const email = e.newValue;
        if (email) {
          setUser({
            name: localStorage.getItem('profileName') || '',
            email,
          });
        } else {
          setUser(null);
        }
      }
    };

    const handleAuthUpdated = () => {
      const admin = JSON.parse(localStorage.getItem('is_superuser') || 'false');
      const email = localStorage.getItem('profileEmail');
      setIsAdmin(admin);
      if (email) {
        setUser({
          name: localStorage.getItem('profileName') || '',
          email,
        });
      }
    };

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('authUpdated', handleAuthUpdated);
    window.addEventListener('profileInfoUpdated', handleAuthUpdated);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('authUpdated', handleAuthUpdated);
      window.removeEventListener('profileInfoUpdated', handleAuthUpdated);
    };
  }, []);

  return (
    <AuthContext.Provider value={{ isAdmin, user, loading, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

// AuthContext exported for components
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

