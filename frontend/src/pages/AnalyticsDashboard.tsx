import React, { useState, useEffect } from 'react';
import API from '../services/api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, ScatterChart, Scatter, ZAxis, LineChart, Line, Legend
} from 'recharts';

interface AnalyticsProps {
  analytics: any;
  examId: number;
  onBack: () => void;
}

const CLUSTER_BG: any = {
  0: 'bg-blue-900 text-blue-300',
  1: 'bg-green-900 text-green-300',
  2: 'bg-yellow-900 text-yellow-300',
  3: 'bg-red-900 text-red-300'
};

const AnalyticsDashboard: React.FC<AnalyticsProps> = ({ analytics, examId, onBack }) => {
  const [clusters, setClusters] = useState<any>(null);
  const [correlations, setCorrelations] = useState<any>(null);
  const [calibration, setCalibration] = useState<any>(null);
  const [rubricOpt, setRubricOpt] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'clusters' | 'correlations' | 'calibration' | 'rubric'>('overview');
  const [loadingInsights, setLoadingInsights] = useState(false);

  useEffect(() => { fetchInsights(); }, [examId]);

  const fetchInsights = async () => {
    setLoadingInsights(true);
    try {
      const [clusterRes, corrRes, calibRes, rubricRes] = await Promise.all([
        API.get(`/insights/exam/${examId}/clusters?n_clusters=2`).catch(() => null),
        API.get(`/insights/exam/${examId}/correlations`).catch(() => null),
        API.get(`/insights/exam/${examId}/calibration`).catch(() => null),
        API.get(`/insights/exam/${examId}/rubric-optimization`).catch(() => null),
      ]);
      if (clusterRes) setClusters(clusterRes.data);
      if (corrRes) setCorrelations(corrRes.data);
      if (calibRes) setCalibration(calibRes.data);
      if (rubricRes) setRubricOpt(rubricRes.data);
    } catch (err) {
      console.log('Some insights not available');
    } finally {
      setLoadingInsights(false);
    }
  };

  if (!analytics) return null;

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

  const difficultyData = analytics.question_analytics.map((q: any, i: number) => ({
    name: `Q${i + 1}`, avg_score: q.avg_score, max_marks: q.max_marks,
    difficulty: q.difficulty_index, override_rate: q.override_rate
  }));

  const passFailData = [
    { name: 'Pass', value: analytics.class_statistics.pass_rate },
    { name: 'Fail', value: parseFloat((100 - analytics.class_statistics.pass_rate).toFixed(2)) }
  ];

  const tabs = [
    { key: 'overview', label: 'Overview' },
    { key: 'clusters', label: 'K-Means Clustering' },
    { key: 'correlations', label: 'Correlation Analysis' },
    { key: 'calibration', label: 'Confidence Calibration' },
    { key: 'rubric', label: 'Rubric Optimization' },
  ];

  return (
    <div>
      <button onClick={onBack} className="text-gray-400 text-sm hover:text-white mb-4 block">← Back</button>
      <h2 className="text-2xl font-bold mb-1">Analytics — {analytics.exam_title}</h2>
      <p className="text-gray-400 text-sm mb-6">pandas · numpy · scikit-learn · sentence-transformers · scipy · {analytics.class_statistics.total_students} students</p>

      <div className="flex gap-2 mb-8 flex-wrap">
        {tabs.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key as any)}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition ${activeTab === tab.key ? 'bg-blue-600 text-white' : 'bg-gray-900 border border-gray-800 text-gray-400 hover:text-white'}`}>
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div>
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
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h3 className="font-semibold mb-1">Pass / Fail Breakdown</h3>
              <p className="text-gray-400 text-xs mb-4">Based on 40% passing threshold</p>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={passFailData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} dataKey="value" label={({ name, value }) => `${name}: ${value}%`}>
                    <Cell fill="#10b981" /><Cell fill="#ef4444" />
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
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
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h3 className="font-semibold mb-1">Question Difficulty Index</h3>
              <p className="text-gray-400 text-xs mb-4">1.0 = easy · 0.0 = very hard</p>
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
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h3 className="font-semibold mb-4">Student Score Breakdown</h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-800">
                  <th className="text-left py-2 pr-4">Student</th>
                  <th className="text-left py-2 pr-4">ID</th>
                  <th className="text-left py-2 pr-4">Total</th>
                  <th className="text-left py-2 pr-4">Max</th>
                  <th className="text-left py-2">%</th>
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
                      <span className={`px-2 py-0.5 rounded-full text-xs ${s.percentage >= 40 ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>{s.percentage}%</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'clusters' && (
        <div>
          {loadingInsights ? <p className="text-gray-400">Loading...</p> : clusters && !clusters.error ? (
            <div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                {Object.entries(clusters.cluster_summary).map(([key, val]: any) => (
                  <div key={key} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                    <div className="flex items-center justify-between mb-2">
                      <span className={`text-xs px-2 py-1 rounded-full ${CLUSTER_BG[parseInt(key)]}`}>Cluster {parseInt(key) + 1}</span>
                      <span className="text-gray-400 text-sm">{val.count} answers</span>
                    </div>
                    <p className="font-semibold">{val.quality_label}</p>
                    <p className="text-gray-400 text-sm">Avg: {val.avg_percentage}%</p>
                    <div className="mt-3 bg-gray-800 rounded-full h-2">
                      <div className="h-2 rounded-full bg-blue-500" style={{ width: `${val.avg_percentage}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                <h3 className="font-semibold mb-1">Answer Clusters</h3>
                <p className="text-gray-400 text-xs mb-4">K-Means using sentence-transformers embeddings</p>
                <div className="space-y-3">
                  {clusters.results.map((r: any, i: number) => (
                    <div key={i} className="bg-gray-800 rounded-lg p-4 flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-xs px-2 py-0.5 rounded-full ${CLUSTER_BG[r.cluster]}`}>Cluster {r.cluster + 1}</span>
                          <span className="text-gray-400 text-xs">{r.student_name}</span>
                        </div>
                        <p className="text-sm text-gray-300">{r.answer_preview}...</p>
                      </div>
                      <div className="text-right ml-4">
                        <p className="font-bold text-blue-400">{r.score}/{r.max_marks}</p>
                        <p className="text-gray-500 text-xs">{r.percentage}%</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
              <p className="text-gray-400">Not enough graded answers for clustering yet.</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'correlations' && (
        <div>
          {loadingInsights ? <p className="text-gray-400">Loading...</p> : correlations && !correlations.error && correlations.correlation_analysis.length > 0 ? (
            <div className="space-y-6">
              {correlations.correlation_analysis.map((c: any, i: number) => (
                <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                  <h3 className="font-semibold mb-3">{c.question_text}...</h3>
                  <div className="flex gap-4 mb-4">
                    <div className="bg-gray-800 rounded-lg px-3 py-2 text-center">
                      <p className="text-blue-400 font-bold">{c.word_length_correlation}</p>
                      <p className="text-gray-500 text-xs">Pearson r</p>
                    </div>
                    <div className="bg-gray-800 rounded-lg px-3 py-2 text-center">
                      <p className="text-green-400 font-bold">{c.word_length_p_value}</p>
                      <p className="text-gray-500 text-xs">p-value</p>
                    </div>
                    <div className="bg-gray-800 rounded-lg px-3 py-2 text-center">
                      <p className={`font-bold ${c.interpretation === 'Strong positive' ? 'text-green-400' : 'text-yellow-400'}`}>{c.interpretation}</p>
                      <p className="text-gray-500 text-xs">Interpretation</p>
                    </div>
                  </div>
                  <ResponsiveContainer width="100%" height={220}>
                    <ScatterChart>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="word_count" name="Word Count" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                      <YAxis dataKey="score_percentage" name="Score %" domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 11 }} />
                      <ZAxis range={[60, 60]} />
                      <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} />
                      <Scatter data={c.scatter_data} fill="#3b82f6" />
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
              <p className="text-gray-400">Not enough data for correlation analysis.</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'calibration' && (
        <div>
          {loadingInsights ? <p className="text-gray-400">Loading...</p> : calibration && !calibration.error ? (
            <div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                {[
                  { label: 'Total Reviewed', value: calibration.total_reviewed, color: 'text-blue-400' },
                  { label: 'Approval Rate', value: `${Math.round(calibration.overall_approval_rate * 100)}%`, color: 'text-green-400' },
                  { label: 'Avg AI Confidence', value: `${Math.round(calibration.avg_ai_confidence * 100)}%`, color: 'text-yellow-400' },
                  { label: 'Interpretation', value: calibration.interpretation, color: calibration.interpretation === 'Well calibrated' ? 'text-green-400' : 'text-red-400' },
                ].map((stat, i) => (
                  <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
                    <p className={`text-xl font-bold ${stat.color}`}>{stat.value}</p>
                    <p className="text-gray-400 text-sm mt-1">{stat.label}</p>
                  </div>
                ))}
              </div>
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-4">
                <h3 className="font-semibold mb-1">Calibration Curve</h3>
                <p className="text-gray-400 text-xs mb-4">Blue = actual approval rate · Gray = perfect calibration line. Closer they are = better calibrated AI.</p>
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={calibration.calibration_curve}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="confidence_bin" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                    <YAxis domain={[0, 1]} tick={{ fill: '#9ca3af', fontSize: 11 }} />
                    <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} />
                    <Legend />
                    <Line type="monotone" dataKey="approval_rate" stroke="#3b82f6" strokeWidth={2} dot={{ fill: '#3b82f6', r: 5 }} name="Actual Approval Rate" />
                    <Line type="monotone" dataKey="avg_confidence" stroke="#6b7280" strokeWidth={2} strokeDasharray="5 5" dot={false} name="AI Confidence" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-900 border border-red-800 rounded-xl p-4">
                  <p className="text-red-400 font-semibold">{calibration.overconfident_count} Overconfident Grades</p>
                  <p className="text-gray-400 text-xs mt-1">AI was confident but TA overrode the grade</p>
                </div>
                <div className="bg-gray-900 border border-yellow-800 rounded-xl p-4">
                  <p className="text-yellow-400 font-semibold">{calibration.underconfident_count} Underconfident Grades</p>
                  <p className="text-gray-400 text-xs mt-1">AI was unsure but TA approved the grade</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
              <p className="text-gray-400">Not enough reviewed grades for calibration analysis.</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'rubric' && (
        <div>
          {loadingInsights ? <p className="text-gray-400">Loading...</p> : rubricOpt ? (
            <div>
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-blue-400">{rubricOpt.total_questions_analyzed}</p>
                  <p className="text-gray-400 text-sm">Questions Analyzed</p>
                </div>
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-red-400">{rubricOpt.questions_needing_attention}</p>
                  <p className="text-gray-400 text-sm">Need Attention</p>
                </div>
              </div>
              {rubricOpt.suggestions.length === 0 ? (
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
                  <p className="text-green-400 font-semibold">All rubric conditions look well balanced!</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {rubricOpt.suggestions.map((q: any, i: number) => (
                    <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                      <h3 className="font-semibold mb-3">{q.question_text}</h3>
                      <div className="space-y-3">
                        {q.suggestions.map((s: any, j: number) => (
                          <div key={j} className={`rounded-lg p-4 border ${s.severity === 'high' ? 'border-red-800 bg-red-950' : 'border-yellow-800 bg-yellow-950'}`}>
                            <div className="flex items-center justify-between mb-1">
                              <p className="text-sm font-medium">"{s.condition}"</p>
                              <span className={`text-xs px-2 py-0.5 rounded-full ${s.severity === 'high' ? 'bg-red-900 text-red-300' : 'bg-yellow-900 text-yellow-300'}`}>{s.flag}</span>
                            </div>
                            <p className="text-gray-400 text-xs">Satisfaction rate: {Math.round(s.satisfaction_rate * 100)}% · {s.marks} marks</p>
                            <p className="text-gray-300 text-xs mt-2">💡 {s.suggestion}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
              <p className="text-gray-400">No rubric data available.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AnalyticsDashboard;
