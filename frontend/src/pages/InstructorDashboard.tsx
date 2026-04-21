import React, { useState, useEffect } from 'react';
import API from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Upload, BookOpen, LogOut, Plus, ChevronRight, BarChart2 } from 'lucide-react';
import AnalyticsDashboard from './AnalyticsDashboard';

const InstructorDashboard = () => {
  const [view, setView] = useState<'courses' | 'create-course' | 'course-detail' | 'create-exam' | 'exam-detail' | 'analytics'>('courses');
  const [courses, setCourses] = useState<any[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<any>(null);
  const [selectedExam, setSelectedExam] = useState<any>(null);
  const [exams, setExams] = useState<any[]>([]);
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [courseName, setCourseName] = useState('');
  const [courseCode, setCourseCode] = useState('');
  const [examTitle, setExamTitle] = useState('');
  const [questions, setQuestions] = useState([{ question_text: '', max_marks: 10, order_number: 1, rubric_conditions: [{ condition_text: '', marks: 5 }] }]);
  const [uploadStudent, setUploadStudent] = useState({ name: '', id: '' });
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const { logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => { fetchCourses(); }, []);

  const fetchCourses = async () => { const res = await API.get('/courses/my-courses'); setCourses(res.data); };
  const fetchExams = async (courseId: number) => { const res = await API.get(`/exams/course/${courseId}`); setExams(res.data); };
  const fetchSubmissions = async (examId: number) => { const res = await API.get(`/exams/${examId}/submissions`); setSubmissions(res.data); };
  const fetchAnalytics = async (examId: number) => { const res = await API.get(`/analytics/exam/${examId}`); setAnalytics(res.data); };

  const handleCreateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    await API.post('/courses/create', { name: courseName, code: courseCode });
    await fetchCourses();
    setCourseName(''); setCourseCode('');
    setView('courses');
  };

  const handleCreateExam = async (e: React.FormEvent) => {
    e.preventDefault();
    await API.post('/exams/create', { title: examTitle, course_id: selectedCourse.course_id, questions });
    await fetchExams(selectedCourse.course_id);
    setView('course-detail');
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;
    setLoading(true);
    const formData = new FormData();
    formData.append('student_name', uploadStudent.name);
    formData.append('student_id', uploadStudent.id);
    formData.append('file', uploadFile);
    await API.post(`/exams/${selectedExam.exam_id}/upload-submission`, formData);
    await fetchSubmissions(selectedExam.exam_id);
    setUploadStudent({ name: '', id: '' });
    setUploadFile(null);
    setLoading(false);
  };

  const handleProcess = async (submissionId: number) => { await API.post(`/exams/submissions/${submissionId}/process`); await fetchSubmissions(selectedExam.exam_id); };
  const handleGrade = async (submissionId: number) => { await API.post(`/grade/submission/${submissionId}`); await fetchSubmissions(selectedExam.exam_id); };
  const addQuestion = () => setQuestions([...questions, { question_text: '', max_marks: 10, order_number: questions.length + 1, rubric_conditions: [{ condition_text: '', marks: 5 }] }]);
  const addCondition = (qIndex: number) => { const updated = [...questions]; updated[qIndex].rubric_conditions.push({ condition_text: '', marks: 2 }); setQuestions(updated); };

  const statusColor: any = { uploaded: 'bg-yellow-500', processing: 'bg-blue-500', graded: 'bg-green-500', reviewed: 'bg-purple-500' };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <nav className="bg-gray-900 border-b border-gray-800 px-8 py-4 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold">GradeOps</h1>
          <span className="text-blue-400 text-sm">Instructor</span>
          {selectedCourse && <><ChevronRight size={14} className="text-gray-600" /><span className="text-gray-300 text-sm">{selectedCourse.name}</span></>}
          {selectedExam && <><ChevronRight size={14} className="text-gray-600" /><span className="text-gray-300 text-sm">{selectedExam.title}</span></>}
        </div>
        <button onClick={() => { logout(); navigate('/'); }} className="flex items-center gap-2 text-gray-400 hover:text-white transition text-sm"><LogOut size={16} /> Logout</button>
      </nav>

      <div className="max-w-6xl mx-auto px-8 py-8">

        {view === 'courses' && (
          <div>
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold">My Courses</h2>
              <button onClick={() => setView('create-course')} className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-sm flex items-center gap-2"><Plus size={16} /> New Course</button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {courses.map(course => (
                <div key={course.course_id} onClick={() => { setSelectedCourse(course); fetchExams(course.course_id); setView('course-detail'); }}
                  className="bg-gray-900 border border-gray-800 rounded-xl p-6 cursor-pointer hover:border-blue-500 transition">
                  <div className="flex items-center gap-3 mb-2"><BookOpen size={20} className="text-blue-400" /><span className="text-xs bg-blue-900 text-blue-300 px-2 py-1 rounded">{course.code}</span></div>
                  <h3 className="font-semibold text-lg">{course.name}</h3>
                  <p className="text-gray-400 text-sm mt-1">Click to manage</p>
                </div>
              ))}
              {courses.length === 0 && <p className="text-gray-500 text-sm">No courses yet. Create your first course.</p>}
            </div>
          </div>
        )}

        {view === 'create-course' && (
          <div className="max-w-md">
            <h2 className="text-2xl font-bold mb-6">Create Course</h2>
            <form onSubmit={handleCreateCourse} className="space-y-4 bg-gray-900 p-6 rounded-xl border border-gray-800">
              <div><label className="text-gray-300 text-sm mb-1 block">Course Name</label>
                <input value={courseName} onChange={e => setCourseName(e.target.value)} className="w-full bg-gray-800 rounded-lg px-4 py-2 border border-gray-700 text-sm focus:outline-none focus:border-blue-500" placeholder="Data Structures" required /></div>
              <div><label className="text-gray-300 text-sm mb-1 block">Course Code</label>
                <input value={courseCode} onChange={e => setCourseCode(e.target.value)} className="w-full bg-gray-800 rounded-lg px-4 py-2 border border-gray-700 text-sm focus:outline-none focus:border-blue-500" placeholder="CS101" required /></div>
              <div className="flex gap-3">
                <button type="submit" className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-sm">Create</button>
                <button type="button" onClick={() => setView('courses')} className="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded-lg text-sm">Cancel</button>
              </div>
            </form>
          </div>
        )}

        {view === 'course-detail' && selectedCourse && (
          <div>
            <div className="flex justify-between items-center mb-6">
              <div>
                <button onClick={() => { setView('courses'); setSelectedCourse(null); }} className="text-gray-400 text-sm hover:text-white mb-2 block">← Back to courses</button>
                <h2 className="text-2xl font-bold">{selectedCourse.name} <span className="text-gray-500 text-lg font-normal">({selectedCourse.code})</span></h2>
              </div>
              <button onClick={() => setView('create-exam')} className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-sm flex items-center gap-2"><Plus size={16} /> New Exam</button>
            </div>
            <div className="space-y-3">
              {exams.map(exam => (
                <div key={exam.exam_id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold">{exam.title}</h3>
                    <p className="text-gray-400 text-sm">{exam.question_count} questions · {exam.submission_count} submissions</p>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => { setSelectedExam(exam); fetchSubmissions(exam.exam_id); setView('exam-detail'); }} className="bg-gray-700 hover:bg-gray-600 px-3 py-1 rounded-lg text-sm">Manage</button>
                    <button onClick={() => { setSelectedExam(exam); fetchAnalytics(exam.exam_id); setView('analytics'); }} className="bg-purple-700 hover:bg-purple-600 px-3 py-1 rounded-lg text-sm flex items-center gap-1"><BarChart2 size={14} /> Analytics</button>
                  </div>
                </div>
              ))}
              {exams.length === 0 && <p className="text-gray-500 text-sm">No exams yet.</p>}
            </div>
          </div>
        )}

        {view === 'create-exam' && (
          <div>
            <button onClick={() => setView('course-detail')} className="text-gray-400 text-sm hover:text-white mb-4 block">← Back</button>
            <h2 className="text-2xl font-bold mb-6">Create Exam</h2>
            <form onSubmit={handleCreateExam} className="space-y-6">
              <input value={examTitle} onChange={e => setExamTitle(e.target.value)} className="w-full bg-gray-800 rounded-lg px-4 py-3 border border-gray-700 focus:outline-none focus:border-blue-500" placeholder="Exam Title" required />
              {questions.map((q, qi) => (
                <div key={qi} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                  <h3 className="font-medium mb-3">Question {qi + 1}</h3>
                  <textarea value={q.question_text} onChange={e => { const u = [...questions]; u[qi].question_text = e.target.value; setQuestions(u); }}
                    className="w-full bg-gray-800 rounded-lg px-4 py-2 border border-gray-700 text-sm focus:outline-none focus:border-blue-500 mb-2" placeholder="Question text" rows={2} required />
                  <input type="number" value={q.max_marks} onChange={e => { const u = [...questions]; u[qi].max_marks = parseInt(e.target.value); setQuestions(u); }}
                    className="bg-gray-800 rounded-lg px-3 py-2 border border-gray-700 text-sm w-32 mb-3" placeholder="Max marks" />
                  <p className="text-gray-400 text-xs mb-2">Rubric Conditions:</p>
                  {q.rubric_conditions.map((rc, ri) => (
                    <div key={ri} className="flex gap-2 mb-2">
                      <input value={rc.condition_text} onChange={e => { const u = [...questions]; u[qi].rubric_conditions[ri].condition_text = e.target.value; setQuestions(u); }}
                        className="flex-1 bg-gray-800 rounded-lg px-3 py-2 border border-gray-700 text-sm focus:outline-none focus:border-blue-500" placeholder="Condition" required />
                      <input type="number" value={rc.marks} onChange={e => { const u = [...questions]; u[qi].rubric_conditions[ri].marks = parseInt(e.target.value); setQuestions(u); }}
                        className="bg-gray-800 rounded-lg px-3 py-2 border border-gray-700 text-sm w-20" />
                    </div>
                  ))}
                  <button type="button" onClick={() => addCondition(qi)} className="text-blue-400 text-xs hover:text-blue-300">+ Add condition</button>
                </div>
              ))}
              <div className="flex gap-3">
                <button type="button" onClick={addQuestion} className="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded-lg text-sm flex items-center gap-2"><Plus size={14} /> Add Question</button>
                <button type="submit" className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-sm">Create Exam</button>
              </div>
            </form>
          </div>
        )}

        {view === 'exam-detail' && selectedExam && (
          <div>
            <button onClick={() => { setView('course-detail'); setSelectedExam(null); }} className="text-gray-400 text-sm hover:text-white mb-4 block">← Back</button>
            <h2 className="text-2xl font-bold mb-6">{selectedExam.title}</h2>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <h3 className="font-medium mb-4 flex items-center gap-2"><Upload size={16} /> Upload Submission</h3>
                <form onSubmit={handleUpload} className="space-y-3">
                  <input value={uploadStudent.name} onChange={e => setUploadStudent({ ...uploadStudent, name: e.target.value })}
                    className="w-full bg-gray-800 rounded-lg px-3 py-2 border border-gray-700 text-sm focus:outline-none focus:border-blue-500" placeholder="Student Name" required />
                  <input value={uploadStudent.id} onChange={e => setUploadStudent({ ...uploadStudent, id: e.target.value })}
                    className="w-full bg-gray-800 rounded-lg px-3 py-2 border border-gray-700 text-sm focus:outline-none focus:border-blue-500" placeholder="Student ID" required />
                  <input type="file" accept=".pdf" onChange={e => setUploadFile(e.target.files?.[0] || null)} className="w-full text-sm text-gray-400" required />
                  <button type="submit" disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700 py-2 rounded-lg text-sm disabled:opacity-50">{loading ? 'Uploading...' : 'Upload PDF'}</button>
                </form>
              </div>
              <div className="lg:col-span-2">
                <h3 className="font-medium mb-4">Submissions ({submissions.length})</h3>
                <div className="space-y-3">
                  {submissions.map(s => (
                    <div key={s.submission_id} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center justify-between">
                      <div><p className="font-medium text-sm">{s.student_name}</p><p className="text-gray-400 text-xs">{s.student_id}</p></div>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-2 py-1 rounded-full text-white ${statusColor[s.status]}`}>{s.status}</span>
                        {s.status === 'uploaded' && <button onClick={() => handleProcess(s.submission_id)} className="bg-yellow-600 hover:bg-yellow-700 text-xs px-3 py-1 rounded-lg">Run OCR</button>}
                        {s.status === 'graded' && <button onClick={() => handleGrade(s.submission_id)} className="bg-green-600 hover:bg-green-700 text-xs px-3 py-1 rounded-lg">Grade</button>}
                      </div>
                    </div>
                  ))}
                  {submissions.length === 0 && <p className="text-gray-500 text-sm">No submissions yet.</p>}
                </div>
              </div>
            </div>
          </div>
        )}

        {view === 'analytics' && analytics && (
          <AnalyticsDashboard analytics={analytics} onBack={() => setView('course-detail')} />
        )}

      </div>
    </div>
  );
};

export default InstructorDashboard;
