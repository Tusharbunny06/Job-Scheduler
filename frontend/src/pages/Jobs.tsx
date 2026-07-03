import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import {
  RefreshCw, AlertCircle, CheckCircle, Clock, Loader2,
  ServerCrash, Plus, X, ChevronDown, FileText,
} from 'lucide-react';

interface Job {
  id: string;
  queue_id: string;
  payload: any;
  status: string;
  created_at: string;
  scheduled_at?: string;
  max_retries: number;
  current_retries: number;
}

interface Queue {
  id: string;
  name: string;
}

interface JobLog {
  id: string;
  message: string;
  timestamp: string;
}

const STATUS_OPTIONS = ['all', 'queued', 'running', 'completed', 'failed', 'dlq'];

const STATUS_COLORS: Record<string, string> = {
  all: 'bg-slate-100 text-slate-700',
  queued: 'bg-amber-100 text-amber-800',
  running: 'bg-blue-100 text-blue-800',
  completed: 'bg-emerald-100 text-emerald-800',
  failed: 'bg-red-100 text-red-800',
  dlq: 'bg-rose-900 text-white',
};

function getStatusBadge(status: string) {
  const base = 'px-2.5 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full';
  return `${base} ${STATUS_COLORS[status] || 'bg-slate-100 text-slate-700'}`;
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'completed': return <CheckCircle className="text-emerald-500" size={15} />;
    case 'failed': return <AlertCircle className="text-red-500" size={15} />;
    case 'dlq': return <AlertCircle className="text-rose-600" size={15} />;
    case 'running': return <RefreshCw className="text-blue-500 animate-spin" size={15} />;
    default: return <Clock className="text-slate-400" size={15} />;
  }
}

// ── Create Job Modal ────────────────────────────────────────────────────────

function CreateJobModal({ queues, onClose, onSuccess }: {
  queues: Queue[];
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [queueId, setQueueId] = useState(queues[0]?.id ?? '');
  const [payloadStr, setPayloadStr] = useState('{\n  "task": "example"\n}');
  const [scheduledAt, setScheduledAt] = useState('');
  const [payloadError, setPayloadError] = useState('');

  const mutation = useMutation({
    mutationFn: async () => {
      let payload: any;
      try {
        payload = JSON.parse(payloadStr);
        setPayloadError('');
      } catch {
        setPayloadError('Invalid JSON');
        throw new Error('Invalid JSON');
      }
      await apiClient.post('/jobs/', {
        queue_id: queueId,
        payload,
        scheduled_at: scheduledAt || null,
      });
    },
    onSuccess: () => {
      onSuccess();
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6">
        <div className="flex justify-between items-center mb-5">
          <h3 className="text-lg font-semibold text-slate-800">Create Job</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X size={20} /></button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Queue</label>
            <select
              value={queueId}
              onChange={e => setQueueId(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {queues.map(q => <option key={q.id} value={q.id}>{q.name}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">
              Payload (JSON)
            </label>
            <textarea
              value={payloadStr}
              onChange={e => setPayloadStr(e.target.value)}
              rows={6}
              className={`w-full font-mono text-sm border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 ${payloadError ? 'border-red-400' : 'border-slate-300'}`}
            />
            {payloadError && <p className="text-red-500 text-xs mt-1">{payloadError}</p>}
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">
              Schedule At (optional)
            </label>
            <input
              type="datetime-local"
              value={scheduledAt}
              onChange={e => setScheduledAt(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {mutation.isError && (
          <p className="text-red-500 text-xs mt-3">Failed to create job. Check JSON and try again.</p>
        )}

        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg text-sm hover:bg-slate-200 transition">
            Cancel
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={!queueId || mutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition disabled:opacity-50"
          >
            {mutation.isPending ? 'Creating…' : 'Create Job'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Job Details Modal (Replaces Logs Modal) ───────────────────────────────────

interface JobExecution {
  id: string;
  worker_id: string | null;
  status: string;
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
}

function JobDetailsModal({ job, onClose }: { job: Job; onClose: () => void }) {
  const queryClient = useQueryClient();

  const { data: logs, isLoading: logsLoading } = useQuery<JobLog[]>({
    queryKey: ['job-logs', job.id],
    queryFn: async () => (await apiClient.get(`/jobs/${job.id}/logs`)).data,
  });

  const { data: executions, isLoading: execLoading } = useQuery<JobExecution[]>({
    queryKey: ['job-executions', job.id],
    queryFn: async () => (await apiClient.get(`/jobs/${job.id}/executions`)).data,
  });

  const retryMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post(`/jobs/${job.id}/retry`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      onClose(); // close modal on retry
    },
  });

  const timelineSteps = ['queued', 'claimed', 'running', job.status === 'dlq' ? 'dlq' : (job.status === 'failed' ? 'failed' : 'completed')];
  const currentIndex = timelineSteps.indexOf(job.status);
  
  // Basic status ordering for the timeline (very simplified)
  const isPastOrCurrent = (step: string) => {
    if (job.status === 'completed' || job.status === 'dlq' || job.status === 'failed') return true;
    if (job.status === 'running' && (step === 'queued' || step === 'claimed' || step === 'running')) return true;
    if (job.status === 'claimed' && (step === 'queued' || step === 'claimed')) return true;
    if (job.status === 'queued' && step === 'queued') return true;
    return false;
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex justify-end z-50">
      <div className="bg-white shadow-2xl w-full max-w-3xl h-full flex flex-col animate-slide-in-right">
        
        {/* Header */}
        <div className="p-6 border-b border-slate-200 flex justify-between items-start bg-slate-50">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h3 className="text-xl font-bold text-slate-800">Job Details</h3>
              <span className={getStatusBadge(job.status)}>{job.status}</span>
            </div>
            <p className="text-sm text-slate-500 font-mono">{job.id}</p>
          </div>
          <div className="flex items-center gap-3">
            {(job.status === 'failed' || job.status === 'dlq') && (
              <button 
                onClick={() => retryMutation.mutate()}
                disabled={retryMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
              >
                {retryMutation.isPending ? 'Retrying...' : 'Retry Job'}
              </button>
            )}
            <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-200 rounded-full transition"><X size={24} /></button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-8">
          
          {/* Lifecycle Timeline */}
          <div>
            <h4 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-4">Lifecycle Timeline</h4>
            <div className="flex items-center">
              {timelineSteps.map((step, index) => {
                const active = isPastOrCurrent(step);
                return (
                  <div key={step} className="flex items-center flex-1 last:flex-none">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${active ? 'bg-blue-600 text-white ring-4 ring-blue-100' : 'bg-slate-100 text-slate-400'}`}>
                      {index + 1}
                    </div>
                    <div className="ml-3 mr-4">
                      <p className={`text-sm font-medium capitalize ${active ? 'text-slate-800' : 'text-slate-400'}`}>{step}</p>
                    </div>
                    {index < timelineSteps.length - 1 && (
                      <div className={`flex-1 h-0.5 mx-2 ${active ? 'bg-blue-600' : 'bg-slate-200'}`} />
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6">
            {/* Payload */}
            <div>
              <h4 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-2">Payload</h4>
              <div className="bg-slate-50 rounded-lg p-4 border border-slate-200 h-40 overflow-auto">
                <pre className="text-xs text-slate-700 font-mono">
                  {JSON.stringify(job.payload, null, 2)}
                </pre>
              </div>
            </div>

            {/* Execution History */}
            <div>
              <h4 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-2">Execution History ({job.current_retries}/{job.max_retries} Retries)</h4>
              <div className="bg-white rounded-lg border border-slate-200 h-40 overflow-auto">
                {execLoading ? (
                  <p className="p-4 text-sm text-slate-500">Loading executions...</p>
                ) : executions?.length === 0 ? (
                  <p className="p-4 text-sm text-slate-500">No execution attempts yet.</p>
                ) : (
                  <ul className="divide-y divide-slate-100">
                    {executions?.map((exec, i) => (
                      <li key={exec.id} className="p-3 hover:bg-slate-50">
                        <div className="flex justify-between items-center mb-1">
                          <span className={`text-xs font-bold uppercase ${exec.status === 'completed' ? 'text-emerald-600' : 'text-red-600'}`}>
                            Attempt {executions.length - i}
                          </span>
                          <span className="text-xs text-slate-400 font-mono">
                            {new Date(exec.started_at).toLocaleTimeString()}
                          </span>
                        </div>
                        {exec.error_message && (
                          <p className="text-xs text-red-500 truncate mt-1 bg-red-50 p-1 rounded border border-red-100">{exec.error_message}</p>
                        )}
                        <p className="text-xs text-slate-500 font-mono mt-1">Worker: {exec.worker_id?.substring(0, 8) || 'None'}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>

          {/* Granular Logs */}
          <div>
            <h4 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-2">Live Logs</h4>
            <div className="bg-slate-950 rounded-lg p-4 font-mono text-xs text-slate-200 h-64 overflow-y-auto space-y-1">
              {logsLoading && <p className="text-slate-500">Fetching live logs…</p>}
              {logs && logs.length === 0 && <p className="text-slate-500">No log entries found.</p>}
              {logs?.map(log => (
                <div key={log.id} className="flex gap-3">
                  <span className="text-slate-500 shrink-0">{new Date(log.timestamp).toLocaleTimeString()}</span>
                  <span className={log.message.toLowerCase().includes('error') || log.message.toLowerCase().includes('fail') ? 'text-red-400' : 'text-emerald-300'}>
                    {log.message}
                  </span>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

// ── Main Jobs Page ───────────────────────────────────────────────────────────

export default function Jobs() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('all');
  const [showCreate, setShowCreate] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  const { data: jobs, isLoading, isError, refetch } = useQuery<Job[]>({
    queryKey: ['jobs', statusFilter],
    queryFn: async () => {
      const params = statusFilter !== 'all' ? { status: statusFilter } : {};
      const response = await apiClient.get('/jobs/', { params });
      return response.data;
    },
    retry: 1,
    refetchInterval: 5_000, // Auto-poll every 5 seconds
  });

  const { data: queues } = useQuery<Queue[]>({
    queryKey: ['queues'],
    queryFn: async () => (await apiClient.get('/queues/')).data,
  });

  const retryMutation = useMutation({
    mutationFn: async (jobId: string) => {
      await apiClient.post(`/jobs/${jobId}/retry`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] }),
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-semibold text-slate-800">Job Explorer</h2>
          <p className="text-sm text-slate-500 mt-1">Monitor and manage all scheduled jobs. Click a job for details.</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded-lg shadow-sm hover:bg-slate-50 transition text-sm"
          >
            <RefreshCw size={15} /> Refresh
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg shadow hover:bg-blue-700 transition text-sm"
          >
            <Plus size={15} /> Create Job
          </button>
        </div>
      </div>

      {/* Status Filter Tabs */}
      <div className="flex gap-2 flex-wrap">
        {STATUS_OPTIONS.map(s => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-4 py-2 rounded-lg text-sm font-semibold capitalize transition border ${
              statusFilter === s
                ? 'border-blue-500 bg-blue-50 text-blue-700 shadow-sm'
                : 'border-slate-200 bg-white text-slate-600 hover:border-slate-400 hover:bg-slate-50'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-16 flex flex-col items-center justify-center gap-4">
          <Loader2 className="animate-spin text-blue-500" size={36} />
          <p className="text-slate-500 text-sm font-medium">Loading jobs…</p>
        </div>
      )}

      {/* Error */}
      {isError && !isLoading && (
        <div className="bg-white rounded-xl shadow-sm border border-red-100 p-16 flex flex-col items-center justify-center gap-4">
          <ServerCrash className="text-red-400" size={40} />
          <p className="text-slate-700 font-medium">Failed to load jobs</p>
          <p className="text-slate-500 text-sm">Could not reach the backend. Is the server running?</p>
          <button onClick={() => refetch()} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition">
            Try Again
          </button>
        </div>
      )}

      {/* Jobs Table */}
      {!isLoading && !isError && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">ID / Payload</th>
                <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Queue</th>
                <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Retries</th>
                <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Created</th>
                <th className="px-6 py-4 text-right text-xs font-bold text-slate-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-100">
              {jobs && jobs.length > 0 ? (
                jobs.map(job => (
                  <tr 
                    key={job.id} 
                    onClick={() => setSelectedJob(job)}
                    className="hover:bg-blue-50/50 transition cursor-pointer group"
                  >
                    <td className="px-6 py-4 text-sm text-slate-900">
                      <div className="font-mono text-xs text-slate-400 mb-1 group-hover:text-blue-500 transition-colors">{job.id.substring(0, 8)}…</div>
                      <div className="truncate max-w-xs text-slate-700 text-xs font-mono bg-slate-50 px-2 py-1 rounded border border-slate-100">{JSON.stringify(job.payload)}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 font-mono bg-slate-50/50">
                      {job.queue_id?.substring(0, 8)}…
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(job.status)}
                        <span className={getStatusBadge(job.status)}>{job.status}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 font-medium">
                      {job.current_retries} / {job.max_retries}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                      {new Date(job.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-3">
                      <button
                        onClick={(e) => { e.stopPropagation(); setSelectedJob(job); }}
                        className="text-blue-600 hover:text-blue-800 transition font-semibold"
                        title="View Details"
                      >
                        Details
                      </button>
                      {(job.status === 'failed' || job.status === 'dlq') && (
                        <button
                          onClick={(e) => { e.stopPropagation(); retryMutation.mutate(job.id); }}
                          disabled={retryMutation.isPending}
                          className="text-slate-600 hover:text-slate-900 font-medium transition disabled:opacity-50"
                        >
                          Retry
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-6 py-20 text-center">
                    <div className="flex flex-col items-center gap-4 text-slate-400">
                      <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-2">
                        <Clock size={32} className="text-slate-300" />
                      </div>
                      <p className="font-semibold text-slate-600 text-lg">No jobs found</p>
                      <p className="text-sm text-slate-500 max-w-sm mx-auto">
                        {statusFilter !== 'all' ? `There are currently no ${statusFilter} jobs matching this criteria.` : 'Get started by creating your first background job.'}
                      </p>
                      {statusFilter !== 'all' && (
                        <button onClick={() => setStatusFilter('all')} className="mt-4 text-blue-600 font-medium hover:underline">
                          View all jobs
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Modals */}
      {showCreate && queues && (
        <CreateJobModal
          queues={queues}
          onClose={() => setShowCreate(false)}
          onSuccess={() => queryClient.invalidateQueries({ queryKey: ['jobs'] })}
        />
      )}
      {selectedJob && (
        <JobDetailsModal job={selectedJob} onClose={() => setSelectedJob(null)} />
      )}
    </div>
  );
}
