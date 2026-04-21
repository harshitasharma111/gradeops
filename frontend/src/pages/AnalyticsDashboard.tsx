import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadialBarChart, RadialBar, Legend, PieChart, Pie, Cell
} from 'recharts';

interface AnalyticsProps {
  analytics: any;
  onBack: () => void;
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

const AnalyticsDashboard: React.FC<AnalyticsProps> = ({ analytics, onBack }) => {
  if (!analytics) return null;

  const difficultyData = analytics.question_analytics.map((q: any, i: number) => ({
    name: `Q${i + 1}`,
    avg_score: q.avg_score,
    max_marks: q.max_marks,
    difficulty: q.difficulty_index,
    override_rate: q.override_rate
  }));

  const scoreRanges = [
    { range: '0-20%', count: 0 },
    { range: '21-40%', count: 0 },
    { range: '41-60%', count: 0 },
    { range: '61-80%', count: 0 },
    { range: '81-100%', count: 0 },
  ];

  analytics.student_scores.forEach((s: any) => {
    const pct = s.percentage;
    if (pct <= 20) scoreRanges[0].count++;
    else if (pct <= 40) scoreRanges[1].count++;
    else if (pct <= 60) scoreRanges[2].count++;
    else if (pct <= 80) scoreRanges[3].count++;
    else scoreRanges[4].count++;
  });

  const classAvg = analytics.class_statistics.class_average;
  const radialData = [{ name: 'Class Average', value: classAvg, fill: '#3b82f6' }];

  const passFailData = [
    { name: 'Pass', value: analytics.class_statistics.pass_rate },
    { name: 'Fail', value: 100 - analytics.class_statistics.pass_rate }
  ];

  return (
    <div>
      <button onClick={onBack} className="text-gray-400 text-sm hover:text-white mb-4 block">← Back</button>
      <h2 className="text-2xl font-bold mb-2">Analytics — {analytics.exam_title}</h2>
      <p className="text-gray-400 text-sm mb-8">Powered by pandas + numpy · {analytics.class_statistics.total_students} students</p>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Total Students', value: analytics.class_statistics.total_students, color: 'text-blue-400' },
          { label: 'Class Average', value: `${analytics.class_statistics.class_average}%`, color: 'text-green-400' },
          { label: 'Std Deviation', value: `${analytics.class_statistics.class_std_dev}%`, color: 'text-yellow-400' },
          { label: 'Pass Rate', value: `${analytics.class_statistics.pass_rate}%`, color: 'text-purple-400' },
        ].map((stat, i) => (
          <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
            <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
            <p className="text-gray-400 text-sm mt-1">{stat.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">

        {/* Score Distribution */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="font-semibold mb-1">Score Distribution</h3>
          <p className="text-gray-400 text-xs mb-4">Number of students in each score range</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={scoreRanges}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="range" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} />
              <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Question Average Scores */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="font-semibold mb-1">Average Score per Question</h3>
          <p className="text-gray-400 text-xs mb-4">Identifies which questions students struggled with</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={difficultyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} />
              <Bar dataKey="avg_score" fill="#10b981" radius={[4, 4, 0, 0]} name="Avg Score" />
              <Bar dataKey="max_marks" fill="#374151" radius={[4, 4, 0, 0]} name="Max Marks" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Difficulty Index */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="font-semibold mb-1">Question Difficulty Index</h3>
          <p className="text-gray-400 text-xs mb-4">1.0 = easy, 0.0 = very hard</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={difficultyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis domain={[0, 1]} tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} />
              <Bar dataKey="difficulty" fill="#f59e0b" radius={[4, 4, 0, 0]} name="Difficulty Index" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Pass Fail Pie */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="font-semibold mb-1">Pass / Fail Breakdown</h3>
          <p className="text-gray-400 text-xs mb-4">Based on 40% passing threshold</p>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={passFailData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                dataKey="value"
                label={({ name, value }) => `${name}: ${value}%`}
              >
                <Cell fill="#10b981" />
                <Cell fill="#ef4444" />
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Override Rate */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
        <h3 className="font-semibold mb-1">AI Override Rate per Question</h3>
        <p className="text-gray-400 text-xs mb-4">High override rate means AI struggled with that question — rubric may need refinement</p>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={difficultyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} />
            <YAxis domain={[0, 1]} tick={{ fill: '#9ca3af', fontSize: 11 }} />
            <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} />
            <Bar dataKey="override_rate" fill="#8b5cf6" radius={[4, 4, 0, 0]} name="Override Rate" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Student Scores Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h3 className="font-semibold mb-4">Student Score Breakdown</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                <th className="text-left py-2 pr-4">Student</th>
                <th className="text-left py-2 pr-4">ID</th>
                <th className="text-left py-2 pr-4">Total Score</th>
                <th className="text-left py-2 pr-4">Max</th>
                <th className="text-left py-2">Percentage</th>
              </tr>
            </thead>
            <tbody>
              {analytics.student_scores.map((s: any, i: number) => (
                <tr key={i} className="border-b border-gray-800">
                  <td className="py-2 pr-4">{s.student_name}</td>
                  <td className="py-2 pr-4 text-gray-400">{s.student_id}</td>
                  <td className="py-2 pr-4">{s.total_score}</td>
                  <td className="py-2 pr-4 text-gray-400">{s.max_possible}</td>
                  <td className="py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${s.percentage >= 40 ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>
                      {s.percentage}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;
