import React, { useState, useEffect, useCallback } from 'react';
import API from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { CheckCircle, XCircle, LogOut, AlertTriangle, BookOpen } from 'lucide-react';

const TADashboard = () => {
  const [courses, setCourses] = useState<any[]>([]);
  const [pendingReviews, setPendingReviews] = useState<any[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [view, setView] = useState<'courses' | 'review'>('courses');
  const [overrideScore, setOverrideScore] = useState('');
  const [comment, setComment] = useState('');
  const [overriding, setOverriding] = useState(false);
  const [loading, setLoading] = useState(false);
  const { logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    fetchCourses();
    fetchPendingReviews();
  }, []);

  const fetchCourses = async () => {
    const res = await API.get('/courses/my-courses');
    setCourses(res.data);
  };

  const fetchPendingReviews = async () => {
    const res = await API.get('/grade/pending-reviews');
    setPendingReviews(res.data);
  };

  const current = pendingReviews[currentIndex];

  const handleApprove = useCallback(async () => {
    if (!current) return;
    setLoading(true);
    await API.post(`/grade/review/${current.ai_grade_id}?action=approve`);
    await fetchPendingReviews();
    setCurrentIndex(prev => Math.min(prev, pendingReviews.length - 2));
    setLoading(false);
  }, [current, pendingReviews]);

  const handleOverride = useCallback(async () => {
    if (!current || !overrideScore) return;
    setLoading(true);
    await API.post(`/grade/review/${current.ai_grade_id}?action=override&override_score=${overrideScore}&comment=${comment}`);
    await fetchPendingReviews();
    setCurrentIndex(prev => Math.min(prev, pendingReviews.length - 2));
    setOverrideScore('');
    setComment('');
    setOverriding(false);
    setLoading(false);
  }, [current, overrideScore, comment, pendingReviews]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (view !== 'review') return;
      if (e.key === 'a' || e.key === 'A') handleApprove();
      if (e.key === 'o' || e.key === 'O') setOverriding(true);
      if (e.key === 'ArrowRight') setCurrentIndex(prev => Math.min(prev + 1, pendingReviews.length - 1));
      if (e.key === 'ArrowLeft') setCurrentIndex(prev => Math.max(prev - 1, 0));
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [view, handleApprove, handleOverride, pendingReviews]);

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <nav className="bg-gray-900 border-b border-gray-800 px-8 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold">GradeOps <span className="text-green-400 text-sm font-normal ml-2">TA</span></h1>
        <div className="flex items-center gap-4">
          {view === 'review' && (
            <span className="text-gray-400 text-xs">
              Press <kbd className="bg-gray-700 px-2 py-0.5 rounded text-xs">A</kbd> approve ·
              <kbd className="bg-gray-700 px-2 py-0.5 rounded text-xs ml-1">O</kbd> override ·
              <kbd className="bg-gray-700 px-2 py-0.5 rounded text-xs ml-1">← →</kbd> navigate
            </span>
          )}
          <button onClick={() => { logout(); navigate('/'); }} className="flex items-center gap-2 text-gray-400 hover:text-white text-sm">
            <LogOut size={16} /> Logout
          </button>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-8 py-8">
        {view === 'courses' && (
          <div>
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold">My Courses</h2>
              {pendingReviews.length > 0 && (
                <button onClick={() => setView('review')} className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg text-sm flex items-center gap-2">
                  <AlertTriangle size={16} /> Review Queue ({pendingReviews.length})
                </button>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {courses.map(course => (
                <div key={course.course_id} className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                  <div className="flex items-center gap-3 mb-2">
                    <BookOpen size={20} className="text-green-400" />
                    <span className="text-xs bg-green-900 text-green-300 px-2 py-1 rounded">{course.code}</span>
                  </div>
                  <h3 className="font-semibold text-lg">{course.name}</h3>
                </div>
              ))}
              {courses.length === 0 && <p className="text-gray-500 text-sm">No courses assigned yet. Ask your instructor to assign you.</p>}
            </div>

            {pendingReviews.length === 0 && (
              <div className="mt-8 bg-gray-900 rounded-2xl border border-gray-800 p-12 text-center">
                <CheckCircle size={48} className="text-green-500 mx-auto mb-4" />
                <h2 className="text-xl font-semibold mb-2">All caught up!</h2>
                <p className="text-gray-400 text-sm">No papers pending review right now.</p>
              </div>
            )}
          </div>
        )}

        {view === 'review' && (
          <div>
            <div className="flex justify-between items-center mb-6">
              <div>
                <button onClick={() => setView('courses')} className="text-gray-400 text-sm hover:text-white mb-1 block">← Back</button>
                <h2 className="text-2xl font-bold">Review Queue</h2>
              </div>
              <p className="text-gray-400 text-sm">{currentIndex + 1} of {pendingReviews.length}</p>
            </div>

            {current ? (
              <div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <p className="font-semibold">{current.student_name}</p>
                        <p className="text-gray-400 text-xs">{current.student_id}</p>
                      </div>
                      {current.needs_urgent_review && (
                        <span className="bg-red-900 text-red-300 text-xs px-2 py-1 rounded-full flex items-center gap-1">
                          <AlertTriangle size={10} /> Urgent
                        </span>
                      )}
                    </div>
                    <div className="bg-gray-800 rounded-lg p-4 mb-4">
                      <p className="text-gray-400 text-xs mb-2">Question:</p>
                      <p className="text-sm">{current.question}</p>
                    </div>
                    <div className="bg-gray-800 rounded-lg p-4">
                      <p className="text-gray-400 text-xs mb-2">Student Answer:</p>
                      <p className="text-sm text-gray-200">{current.extracted_answer}</p>
                    </div>
                  </div>

                  <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-4">
                      <p className="font-semibold">AI Grade</p>
                      <div className="text-right">
                        <p className="text-3xl font-bold text-blue-400">{current.ai_score}<span className="text-gray-500 text-lg">/{current.max_marks}</span></p>
                        <p className="text-gray-400 text-xs">Confidence: {Math.round(current.confidence * 100)}%</p>
                      </div>
                    </div>

                    <div className="bg-gray-800 rounded-lg p-4 mb-6">
                      <p className="text-gray-400 text-xs mb-2">Justification:</p>
                      <p className="text-sm text-gray-200">{current.justification}</p>
                    </div>

                    {!overriding ? (
                      <div className="flex gap-3">
                        <button onClick={handleApprove} disabled={loading}
                          className="flex-1 bg-green-600 hover:bg-green-700 py-3 rounded-xl font-semibold flex items-center justify-center gap-2 transition disabled:opacity-50">
                          <CheckCircle size={18} /> Approve (A)
                        </button>
                        <button onClick={() => setOverriding(true)}
                          className="flex-1 bg-yellow-600 hover:bg-yellow-700 py-3 rounded-xl font-semibold flex items-center justify-center gap-2 transition">
                          <XCircle size={18} /> Override (O)
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        <input type="number" value={overrideScore} onChange={e => setOverrideScore(e.target.value)}
                          className="w-full bg-gray-800 rounded-lg px-4 py-2 border border-yellow-600 focus:outline-none text-sm"
                          placeholder={`New score (max ${current.max_marks})`} />
                        <textarea value={comment} onChange={e => setComment(e.target.value)}
                          className="w-full bg-gray-800 rounded-lg px-4 py-2 border border-gray-700 focus:outline-none text-sm"
                          placeholder="Comment (optional)" rows={2} />
                        <div className="flex gap-3">
                          <button onClick={handleOverride} disabled={loading}
                            className="flex-1 bg-yellow-600 hover:bg-yellow-700 py-2 rounded-lg text-sm font-semibold">
                            Confirm Override
                          </button>
                          <button onClick={() => setOverriding(false)} className="flex-1 bg-gray-700 hover:bg-gray-600 py-2 rounded-lg text-sm">
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex justify-between mt-4">
                  <button onClick={() => setCurrentIndex(prev => Math.max(prev - 1, 0))} disabled={currentIndex === 0}
                    className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm disabled:opacity-30">← Previous</button>
                  <button onClick={() => setCurrentIndex(prev => Math.min(prev + 1, pendingReviews.length - 1))} disabled={currentIndex === pendingReviews.length - 1}
                    className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm disabled:opacity-30">Next →</button>
                </div>
              </div>
            ) : (
              <div className="bg-gray-900 rounded-2xl border border-gray-800 p-12 text-center">
                <CheckCircle size={48} className="text-green-500 mx-auto mb-4" />
                <h2 className="text-xl font-semibold">All reviews complete!</h2>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TADashboard;
