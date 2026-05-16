import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  AUTH_TOKEN_STORAGE_KEY,
  getAuthToken,
  getCurrentUser,
  logoutUser,
} from "../api/authApi";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const clearSession = useCallback(() => {
    logoutUser();
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const token = getAuthToken();
    if (!token) {
      setUser(null);
      return null;
    }

    try {
      const current = await getCurrentUser();
      setUser(current);
      return current;
    } catch {
      clearSession();
      return null;
    }
  }, [clearSession]);

  const login = useCallback(
    async (token) => {
      const trimmed = String(token ?? "").trim();
      if (!trimmed) {
        throw new Error("Token is required.");
      }

      if (typeof localStorage !== "undefined") {
        localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, trimmed);
      }

      try {
        const current = await getCurrentUser();
        setUser(current);
        return current;
      } catch (err) {
        clearSession();
        throw err;
      }
    },
    [clearSession]
  );

  const logout = useCallback(() => {
    clearSession();
  }, [clearSession]);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      setLoading(true);
      const token = getAuthToken();

      if (!token) {
        if (!cancelled) {
          setUser(null);
          setLoading(false);
        }
        return;
      }

      try {
        const current = await getCurrentUser();
        if (!cancelled) {
          setUser(current);
        }
      } catch {
        if (!cancelled) {
          clearSession();
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    init();

    return () => {
      cancelled = true;
    };
  }, [clearSession]);

  const isAuthenticated = user !== null;

  const value = useMemo(
    () => ({
      user,
      isAuthenticated,
      loading,
      login,
      logout,
      refreshUser,
    }),
    [user, isAuthenticated, loading, login, logout, refreshUser]
  );

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
