import { ReactNode, useEffect, useState } from 'react';
import { Navigate, useLocation, useNavigate, Outlet } from 'react-router-dom';
import { toast } from 'sonner';

type Props = { children?: ReactNode };

function AuthGuard(props: Props) {
  const location = useLocation();
  const navigate = useNavigate();

  const [status, setStatus] = useState<'checking' | 'ok' | 'bad-server'>('checking');

  useEffect(() => {
    let mounted = true;

    const server = localStorage.getItem('jarvis:selectedServer') || '';
    const token = localStorage.getItem('jarvis:token') || '';
    if (!server) {
      toast.error('No server selected. Redirecting to Services to choose one.');
      // navigate in microtask so it doesn't interrupt render
      setTimeout(() => navigate('/services', { replace: true, state: { from: location.pathname } }), 0);
      return;
    }
    if (!token) {
      toast.error('Please login to continue. Redirecting to Login.');
      // navigate in microtask so it doesn't interrupt render
      setTimeout(() => navigate('/login', { replace: true, state: { from: location.pathname } }), 0);
      return;
    }
    const checkServer = async () => {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 4000);

        const url = server.replace(/\/$/, '') + '/health';
        const res = await fetch(url);
        clearTimeout(timeout);

        if (!mounted) return;

        if (res.ok && res.status === 200) {
          setStatus('ok');
        } else {
          setStatus('bad-server');
        }
      } catch (err) {
        if (mounted) setStatus('bad-server');
      }
    };

    // Run check in background but don't block rendering (so /login can show immediately)
    checkServer();

    return () => {
      mounted = false;
    };
  }, [location.pathname, navigate]);

  // When server becomes unhealthy, notify user and kick them back to services
  useEffect(() => {
    if (status === 'bad-server') {
      toast.error('Selected server is unavailable or unhealthy. Redirecting to Services.');
      navigate('/services', { replace: true, state: { from: location.pathname } });
    }
  }, [status, navigate, location.pathname]);

  // At this point: server exists and health check is either pending or ok
  // If user is trying to access protected routes (not /login) and health check is still pending, show spinner
  const isLoginRoute = location.pathname === '/login';
  const isLoggedIn = localStorage.getItem('jarvis:token') !== null;

  if (!isLoginRoute && status === 'checking') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-jarvis-cyan/30 border-t-jarvis-cyan rounded-full animate-spin" aria-hidden="true" />
      </div>
    );
  }

  // If not logged in and not on /login page, redirect there
  if (!isLoggedIn && !isLoginRoute) {
    navigate('/login', { replace: true, state: { from: location.pathname } });
    return null;
  }

  // Allow rendering: either /login (even while checking), or protected routes when ok
  if (isLoginRoute || status === 'ok') {
    // Render nested routes via the router's <Outlet /> (children are undefined when using Route element)
    return <Outlet />;
  }

  // Fallback - render nothing
  return null;
}

export default AuthGuard;