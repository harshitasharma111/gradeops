import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { CheckCircle, XCircle, LogOut, AlertTriangle } from 'lucide-react';

const TADashboard = () => {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <nav className="bg-gray-900 border-b border-gray-800 px-8 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold">GradeOps <span className="text-green-400 text-sm font-normal ml-2">TA Review</span></h1>
        <div className="flex items-center gap-4">
          <span className="text-gray-400 text-sm">Press <kbd className="bg-gray-700 px-2 py-1 rounded text-xs">A</kbd> to approve · <kbd className="bg-gray-700 px-2 py-1 rounded text-xs">O</kbd> to override</span>
          <button onClick={handleLogout} className="flex items-center gap-2 text-gray-400 hover:text-white transition">
            <LogOut size={16} /> Logout
          </button>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-8 py-10">
        <div className="bg-gray-900 rounded-2xl border border-gray-800 p-12 text-center">
          <CheckCircle size={48} className="text-green-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">No papers pending review</h2>
          <p className="text-gray-400 text-sm">All AI-graded exams will appear here for your approval.</p>
        </div>
      </div>
    </div>
  );
};

export default TADashboard;
