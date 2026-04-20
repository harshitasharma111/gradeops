import React, { useState, useEffect } from 'react';
import API from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, LogOut, Loader } from 'lucide-react';

const InstructorDashboard = () => {
  const [exams, setExams] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [grading, setGrading] = useState<number | null>(null);
  const [studentName, setStudentName] = useState('');
  const [studentId, setStudentId] = useState('');
  const [course, setCourse] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const { logout } = useAuth();
  const navigate = useNavigate();

  const fetchExams = async () => {
    const res = await API.get('/exams/list');
    setExams(res.data);
  };

  useEffect(() => {
    fetchExams();
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('student_name', studentName);
    formData.append('student_id', studentId);
    formData.append('course', course);
    formData.append('file', file);
    try {
      await API.post('/exams/upload', formData);
      await fetchExams();
      setStudentName('');
      setStudentId('');
      setCourse('');
      setFile(null);
    } catch (err) {
      alert('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleGrade = async (examId: number) => {
    setGrading(examId);
    try {
      await API.post(`/exams/ocr/${examId}`);
      await fetchExams();
    } catch (err) {
      alert('Grading failed');
    } finally {
      setGrading(null);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const statusColor: any = {
    uploaded: 'bg-yellow-500',
    processing: 'bg-blue-500',
    graded: 'bg-green-500',
    reviewed: 'bg-purple-500',
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <nav className="bg-gray-900 border-b border-gray-800 px-8 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold">GradeOps <span className="text-blue-400 text-sm font-normal ml-2">Instructor</span></h1>
        <button onClick={handleLogout} className="flex items-center gap-2 text-gray-400 hover:text-white transition">
          <LogOut size={16} /> Logout
        </button>
      </nav>

      <div className="max-w-6xl mx-auto px-8 py-10 grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800 h-fit">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><Upload size={18} /> Upload Exam</h2>
          <form onSubmit={handleUpload} className="space-y-3">
            <input
              type="text"
              placeholder="Student Name"
              value={studentName}
              onChange={(e) => setStudentName(e.target.value)}
              className="w-full bg-gray-800 rounded-lg px-4 py-2 border border-gray-700 text-sm focus:outline-none focus:border-blue-500"
              required
            />
            <input
              type="text"
              placeholder="Student ID"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              className="w-full bg-gray-800 rounded-lg px-4 py-2 border border-gray-700 text-sm focus:outline-none focus:border-blue-500"
              required
            />
            <input
              type="text"
              placeholder="Course (e.g. Math101)"
              value={course}
              onChange={(e) => setCourse(e.target.value)}
              className="w-full bg-gray-800 rounded-lg px-4 py-2 border border-gray-700 text-sm focus:outline-none focus:border-blue-500"
              required
            />
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full text-sm text-gray-400"
              required
            />
            <button
              type="submit"
              disabled={uploading}
              className="w-full bg-blue-600 hover:bg-blue-700 py-2 rounded-lg text-sm font-semibold transition disabled:opacity-50"
            >
              {uploading ? 'Uploading...' : 'Upload PDF'}
            </button>
          </form>
        </div>

        <div className="lg:col-span-2">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><FileText size={18} /> Uploaded Exams</h2>
          <div className="space-y-3">
            {exams.length === 0 && <p className="text-gray-500 text-sm">No exams uploaded yet.</p>}
            {exams.map((exam) => (
              <div key={exam.exam_id} className="bg-gray-900 rounded-xl p-4 border border-gray-800 flex items-center justify-between">
                <div>
                  <p className="font-medium">{exam.student_name}</p>
                  <p className="text-gray-400 text-sm">{exam.course} • {exam.student_id}</p>
                  <p className="text-gray-500 text-xs mt-1">{new Date(exam.uploaded_at).toLocaleString()}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2 py-1 rounded-full text-white ${statusColor[exam.status]}`}>
                    {exam.status}
                  </span>
                  {exam.status === 'uploaded' && (
                    <button
                      onClick={() => handleGrade(exam.exam_id)}
                      disabled={grading === exam.exam_id}
                      className="bg-green-600 hover:bg-green-700 text-white text-xs px-3 py-1 rounded-lg transition disabled:opacity-50 flex items-center gap-1"
                    >
                      {grading === exam.exam_id ? <><Loader size={12} className="animate-spin" /> Grading...</> : 'Run OCR & Grade'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default InstructorDashboard;
