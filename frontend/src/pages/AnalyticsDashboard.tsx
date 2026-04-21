import React, { useState, useEffect } from 'react';
import API from '../services/api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, ScatterChart, Scatter, ZAxis
} from 'recharts';

interface AnalyticsProps {
  analytics: any;
  examId: number;
  onBack: () => void;
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
const CLUSTER_COLORS: any = { 0: '#3b82f6', 1: '#10b981', 2: '#f59e0b', 3: '#ef4444' };
const CLUSTER_BG: any = { 0: 'bg-blue-900 text-blue-300', 1: 'bg-green-900 text-green-300', 2: 'bg-yellow-900 text-yellow-300', 3: 'bg-red-900 text-red-300' };

const AnalyticsDashboard: React.FC<AnalyticsProps> = ({ analytics, examId, onBack }) => {
  const [clusters, setClusters] = useState<any>(null);
  const [correlations, setCorrelations] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'clusters' | 'correlations'>('overview');
  const [loadingInsights, setLoadingInsights] = useState(false);

  useEffect(() => {
    fetchInsights();
  }, [examId]);

  const fetchInsights = async () => {
    setLoadingInsights(true);
    try {
      const [clusterRes, corrRes] = await Promise.all([
        API.get(`/insights/exam/${examId}/clusters?n_clusters=2`),
        API.get(`/insights/exam/${examId}/correlations`)
      ]);
      setClusters(clusterRes.data);
      setCorrelations(corrRes.data);
    } catch (err) {
      console.log('Insights not available yet');
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
    name: `Q${i + 1}`,
    avg_score: q.avg_score,
    max_marks: q.max_marks,
    difficulty: q.difficulty_index,
    override_rate: q.override_rate
  }));

  const passFailData = [
    { name: 'Pass', value: analytics.class_statistics.pass_rate },
    { name: 'Fail', value: parseFloat((100 - analytics.class_statistics.pass_rate).toFixed(2)) }
  ];

  return (
    <div>
      <button onClick={onBack} className="text-gray-400 text-sm hover:text-white mb-4 block">← Back</button>
      <h2 className="text-2xl font-bold mb-1">Analytics — {analytics.exam_title}</h2>
      <p className="text-gray-400 text-sm mb-6">Powered by pandas · numpy · scikit-learn · sentence-transformers · {analytics.class_statistics.total_students} students</p>

      {/* Tabs */}
      <div className="flex gap-2 mb-8 bg-gray-900 p-1 rounded-xl w-fit border border-gray-800">
        {['overview', 'clusters', 'correlations'].map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab as any)}
            className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition ${activeTab === tab ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}>
            {tab === 'clusters' ? 'K-Means Clustering' : tab === 'correlations' ? 'Correlation Analysis' : 'Overview'}
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
                    <Cell fill="#10b981" />
                    <Cell fill="#ef4444" />
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
      )}

      {activeTab === 'clusters' && (
        <div>
          {loadingInsights ? (
            <p className="text-gray-400">Loading cluster analysis...</p>
          ) : clusters && !clusters.error ? (
            <div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                {Object.entries(clusters.cluster_summary).map(([key, val]: any) => (
                  <div key={key} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                    <div className="flex items-center justify-between mb-2">
                      <span className={`text-xs px-2 py-1 rounded-full ${CLUSTER_BG[parseInt(key)]}`}>Cluster {parseInt(key) + 1}</span>
                      <span className="text-gray-400 text-sm">{val.count} students</span>
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
                <p className="text-gray-400 text-xs mb-4">K-Means clustering using sentence embeddings — groups answers by semantic similarity</p>
                <div className="space-y-3">
                  {clusters.results.map((r: any, i: number) => (
                    <div key={i} className="bg-gray-800 rounded-lg p-4 flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-xs px-2 py-0.5 rounded-full ${CLUSTER_BG[r.cluster]}`}>Cluster {r.cluster + 1}</span>
                          <span className="text-gray-400 text-xs">{r.student_name} · {r.student_id}</span>
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
          {loadingInsights ? (
            <p className="text-gray-400">Loading correlation analysis...</p>
          ) : correlations && !correlations.error && correlations.correlation_analysis.length > 0 ? (
            <div className="space-y-6">
              {correlations.correlation_analysis.map((c: any, i: number) => (
                <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                  <h3 className="font-semibold mb-1">{c.question_text}...</h3>
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
                      <p className={`font-bold ${c.interpretation === 'Strong positive' ? 'text-green-400' : c.interpretation === 'Moderate' ? 'text-yellow-400' : 'text-red-400'}`}>{c.interpretation}</p>
                      <p className="text-gray-500 text-xs">Interpretation</p>
                    </div>
                  </div>
                  <p className="text-gray-400 text-xs mb-3">Word count vs Score percentage — each dot is one student</p>
                  <ResponsiveContainer width="100%" height={220}>
                    <ScatterChart>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="word_count" name="Word Count" tick={{ fill: '#9ca3af', fontSize: 11 }} label={{ value: 'Word Count', position: 'bottom', fill: '#6b7280', fontSize: 11 }} />
                      <YAxis dataKey="score_percentage" name="Score %" domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 11 }} label={{ value: 'Score %', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 11 }} />
                      <ZAxis range={[60, 60]} />
                      <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                        formatter={(value: any, name: any) => [value, name === 'word_count' ? 'Words' : 'Score %']} />
                      <Scatter data={c.scatter_data} fill="#3b82f6" />
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
              <p className="text-gray-400">Not enough graded answers for correlation analysis yet.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AnalyticsDashboard;
