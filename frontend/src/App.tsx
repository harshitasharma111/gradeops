import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import InstructorDashboard from './pages/InstructorDashboard';
import TADashboard from './pages/TADashboard';

const ProtectedRoute = ({ children, role }: { children: React.ReactNode, role: string }) => {
  const { token, role: userRole } = useAuth();
  if (!token) return <Navigate to="/" />;
  if (userRole !== role) return <Navigate to="/" />;
  return <>{children}</>;
};

const App = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/instructor" element={
            <ProtectedRoute role="instructor">
              <InstructorDashboard />
            </ProtectedRoute>
          } />
          <Route path="/ta" element={
            <ProtectedRoute role="ta">
              <TADashboard />
            </ProtectedRoute>
          } />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
