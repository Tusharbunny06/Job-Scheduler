import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Activity, LayoutDashboard, Settings, Layers, Menu, Server, LogOut, Briefcase, Cpu, CalendarClock } from 'lucide-react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import Login from './pages/Login';
import Projects from './pages/Projects';
import Queues from './pages/Queues';
import Jobs from './pages/Jobs';
import Workers from './pages/Workers';
import ScheduledJobs from './pages/ScheduledJobs';
import SettingsPage from './pages/Settings';
import { getDashboardMetrics, getThroughput } from './api/metrics';

const queryClient = new QueryClient();

function Sidebar() {
  const location = useLocation();
  const isActive = (path: string) => location.pathname === path;

  return (
    <aside className="w-64 bg-slate-900 text-white flex flex-col">
      <div className="p-6 text-2xl font-bold tracking-tight bg-slate-950 flex items-center gap-3">
        <Activity className="text-blue-500" /> Job Scheduler
      </div>
      <nav className="flex-1 px-4 py-6 space-y-2">
        <Link to="/" className={`flex items-center gap-3 px-4 py-3 rounded-lg transition ${isActive('/') ? 'bg-blue-600 shadow-sm' : 'text-slate-300 hover:bg-slate-800'}`}>
          <LayoutDashboard size={20} /> Dashboard
        </Link>
        <Link to="/projects" className={`flex items-center gap-3 px-4 py-3 rounded-lg transition ${isActive('/projects') ? 'bg-blue-600 shadow-sm' : 'text-slate-300 hover:bg-slate-800'}`}>
          <Briefcase size={20} /> Projects
        </Link>
        <Link to="/queues" className={`flex items-center gap-3 px-4 py-3 rounded-lg transition ${isActive('/queues') ? 'bg-blue-600 shadow-sm' : 'text-slate-300 hover:bg-slate-800'}`}>
          <Layers size={20} /> Queues
        </Link>
        <Link to="/jobs" className={`flex items-center gap-3 px-4 py-3 rounded-lg transition ${isActive('/jobs') ? 'bg-blue-600 shadow-sm' : 'text-slate-300 hover:bg-slate-800'}`}>
          <Server size={20} /> Jobs Explorer
        </Link>
        <Link to="/scheduled-jobs" className={`flex items-center gap-3 px-4 py-3 rounded-lg transition ${isActive('/scheduled-jobs') ? 'bg-blue-600 shadow-sm' : 'text-slate-300 hover:bg-slate-800'}`}>
          <CalendarClock size={20} /> Scheduled Jobs
        </Link>
        <Link to="/workers" className={`flex items-center gap-3 px-4 py-3 rounded-lg transition ${isActive('/workers') ? 'bg-blue-600 shadow-sm' : 'text-slate-300 hover:bg-slate-800'}`}>
          <Cpu size={20} /> Worker Nodes
        </Link>
        <Link to="/settings" className={`flex items-center gap-3 px-4 py-3 rounded-lg transition ${isActive('/settings') ? 'bg-blue-600 shadow-sm' : 'text-slate-300 hover:bg-slate-800'}`}>
          <Settings size={20} /> Settings
        </Link>
      </nav>
      <div className="p-4 border-t border-slate-800">
        <button onClick={() => { localStorage.removeItem('token'); window.location.href = '/login'; }} className="flex items-center gap-3 px-4 py-3 w-full text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition">
          <LogOut size={20} /> Sign Out
        </button>
      </div>
    </aside>
  );
}

function MainLayout() {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar />
      <main className="flex-1 flex flex-col h-full overflow-hidden">
        <header className="h-16 bg-white border-b border-slate-200 flex items-center px-6 justify-between shadow-sm z-10">
          <div className="flex items-center gap-4">
            <button className="text-slate-500 hover:text-slate-700 lg:hidden"><Menu /></button>
            <h1 className="text-xl font-semibold text-slate-800">Overview</h1>
          </div>
          <div className="flex items-center gap-4">
            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-medium">AD</div>
          </div>
        </header>
        <div className="flex-1 overflow-auto p-8">
          <Routes>
            <Route path="/" element={<DashboardHome />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/queues" element={<Queues />} />
            <Route path="/jobs" element={<Jobs />} />
            <Route path="/scheduled-jobs" element={<ScheduledJobs />} />
            <Route path="/workers" element={<Workers />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={<MainLayout />} />
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}

function DashboardHome() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: getDashboardMetrics,
    refetchInterval: 5000
  });

  const { data: throughput } = useQuery({
    queryKey: ['throughput'],
    queryFn: getThroughput,
    refetchInterval: 60000
  });

  // Prepare recharts data
  const chartData = throughput?.map(t => ({
    time: t.hour.split('T')[1]?.substring(0, 5) || t.hour, // Extract HH:MM
    completed: t.completed
  })) || [];

  return (
    <div className="space-y-6">
      {/* Top row cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <MetricCard title="Active Workers" value={isLoading ? "..." : data?.active_workers?.toString() || "0"} subtitle="Live instances" />
        <MetricCard title="Jobs Queued" value={isLoading ? "..." : data?.jobs_queued?.toString() || "0"} subtitle="Awaiting execution" />
        <MetricCard title="Failure Rate" value={isLoading ? "..." : data?.failure_rate || "0%"} subtitle="System wide" />
        <MetricCard title="Avg Execution" value={isLoading ? "..." : `${data?.avg_execution_seconds || 0}s`} subtitle="Time to complete" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Throughput Chart */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-semibold text-slate-800">System Throughput</h2>
            <span className="text-sm text-slate-500 font-medium bg-slate-100 px-3 py-1 rounded-full">{data?.completed_last_hour || 0} jobs/hr</span>
          </div>

          <div className="flex-1 w-full min-h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorCompleted" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} />
                <Tooltip 
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)' }}
                  labelStyle={{ color: '#64748b', fontWeight: 500 }}
                  itemStyle={{ color: '#0f172a', fontWeight: 600 }}
                />
                <Area type="monotone" dataKey="completed" name="Completed Jobs" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorCompleted)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* System Health Panel */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-lg font-semibold mb-6 text-slate-800">System Health</h2>

          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-600">Scheduler / Background Worker</span>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                <span className="text-sm font-medium text-emerald-700">Online</span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-5 border-t border-slate-100">
              <span className="text-sm font-medium text-slate-600">Running Jobs</span>
              <span className="text-sm font-bold text-slate-900">{data?.jobs_running || 0}</span>
            </div>

            <div className="flex items-center justify-between pt-5 border-t border-slate-100">
              <span className="text-sm font-medium text-slate-600">Total Executions</span>
              <span className="text-sm font-bold text-slate-900">{data?.total_executions || 0}</span>
            </div>

            <div className="flex items-center justify-between pt-5 border-t border-slate-100">
              <span className="text-sm font-medium text-slate-600">Dead Letter Queue</span>
              {data && data.dlq_count > 0 ? (
                <span className="text-sm font-bold text-rose-600 px-3 py-1 bg-rose-50 rounded-full border border-rose-200">{data.dlq_count} permanently failed</span>
              ) : (
                <span className="text-sm font-medium text-emerald-600">Empty</span>
              )}
            </div>
            
            <div className="flex items-center justify-between pt-5 border-t border-slate-100">
              <span className="text-sm font-medium text-slate-600">Database Connection</span>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-emerald-700">Healthy</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ title, value, subtitle }: { title: string, value: string, subtitle: string }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 hover:shadow-md transition cursor-default">
      <h3 className="text-sm font-semibold text-slate-500 tracking-wide">{title}</h3>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-3xl font-extrabold text-slate-800">{value}</span>
      </div>
      <p className="mt-1 text-sm font-medium text-slate-400">{subtitle}</p>
    </div>
  );
}
