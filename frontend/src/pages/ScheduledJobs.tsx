import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import {
  Clock, Plus, Trash2, Loader2, ServerCrash, RefreshCw,
  Play, Pause, Calendar, CheckCircle, XCircle
} from 'lucide-react';

interface ScheduledJob {
  id: string;
  queue_id: string;
  name: string | null;
  payload: Record<string, unknown>;
  cron_expression: string;
  next_run_at: string;
  last_run_at: string | null;
  is_active: boolean;
  created_at: string;
}

interface Queue {
  id: string;
  name: string;
}

interface CreateForm {
  queue_id: string;
  name: string;
  cron_expression: string;
  payload_str: string;
}

const CRON_PRESETS = [
  { label: 'Every minute', value: '* * * * *' },
  { label: 'Every 5 minutes', value: '*/5 * * * *' },
  { label: 'Every hour', value: '0 * * * *' },
  { label: 'Daily at midnight', value: '0 0 * * *' },
  { label: 'Every Monday', value: '0 9 * * 1' },
  { label: 'First of month', value: '0 0 1 * *' },
];

function formatNextRun(ts: string): string {
  const d = new Date(ts);
  const diff = d.getTime() - Date.now();
  if (diff < 0) return 'Due now';
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `in ${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `in ${hrs}h`;
  return `in ${Math.floor(hrs / 24)}d`;
}

function CreateModal({ queues, onClose, onSuccess }: {
  queues: Queue[];
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState<CreateForm>({
    queue_id: queues[0]?.id ?? '',
    name: '',
    cron_expression: '0 * * * *',
    payload_str: '{\n  "task": "example"\n}',
  });
  const [payloadError, setPayloadError] = useState('');
  const [customCron, setCustomCron] = useState(false);

  const mutation = useMutation({
    mutationFn: async () => {
      let payload: Record<string, unknown>;
      try {
        payload = JSON.parse(form.payload_str);
        setPayloadError('');
      } catch {
        setPayloadError('Invalid JSON payload');
        throw new Error('Invalid JSON');
      }
      await apiClient.post('/scheduled-jobs/', {
        queue_id: form.queue_id,
        name: form.name || undefined,
        cron_expression: form.cron_expression,
        payload,
      });
    },
    onSuccess: () => { onSuccess(); onClose(); },
  });

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
        <div className="flex justify-between items-center p-6 border-b border-slate-100">
          <div>
            <h3 className="text-lg font-semibold text-slate-800">New Recurring Job</h3>
            <p className="text-xs text-slate-400 mt-0.5">Dispatched automatically on a cron schedule</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl">✕</button>
        </div>

        <div className="p-6 space-y-5">
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Queue</label>
            <select
              value={form.queue_id}
              onChange={e => setForm({ ...form, queue_id: e.target.value })}
              className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
            >
              {queues.map(q => <option key={q.id} value={q.id}>{q.name}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Name (optional)</label>
            <input
              type="text"
              placeholder="e.g. Daily Cleanup"
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Schedule</label>
            <div className="flex flex-wrap gap-2 mb-2">
              {CRON_PRESETS.map(p => (
                <button
                  key={p.value}
                  onClick={() => { setForm({ ...form, cron_expression: p.value }); setCustomCron(false); }}
                  className={`px-2.5 py-1 rounded-full text-xs font-medium border transition ${
                    form.cron_expression === p.value && !customCron
                      ? 'bg-violet-600 text-white border-violet-600'
                      : 'border-slate-200 text-slate-600 hover:border-violet-400'
                  }`}
                >
                  {p.label}
                </button>
              ))}
              <button
                onClick={() => setCustomCron(true)}
                className={`px-2.5 py-1 rounded-full text-xs font-medium border transition ${
                  customCron ? 'bg-violet-600 text-white border-violet-600' : 'border-slate-200 text-slate-600 hover:border-violet-400'
                }`}
              >
                Custom
              </button>
            </div>
            {customCron && (
              <input
                type="text"
                placeholder="* * * * * (minute hour day month weekday)"
                value={form.cron_expression}
                onChange={e => setForm({ ...form, cron_expression: e.target.value })}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-violet-500"
              />
            )}
            <p className="text-xs text-slate-400 mt-1">Expression: <code className="bg-slate-100 px-1 rounded">{form.cron_expression}</code></p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Payload (JSON)</label>
            <textarea
              rows={5}
              value={form.payload_str}
              onChange={e => setForm({ ...form, payload_str: e.target.value })}
              className={`w-full font-mono text-xs border rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-violet-500 ${payloadError ? 'border-red-400' : 'border-slate-200'}`}
            />
            {payloadError && <p className="text-red-500 text-xs mt-1">{payloadError}</p>}
          </div>
        </div>

        {mutation.isError && (
          <div className="px-6 pb-2">
            <p className="text-red-500 text-xs">Failed to create job — check cron expression and JSON payload.</p>
          </div>
        )}

        <div className="flex justify-end gap-3 px-6 pb-6">
          <button onClick={onClose} className="px-4 py-2 text-sm text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition">Cancel</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={!form.queue_id || mutation.isPending}
            className="px-4 py-2 text-sm text-white bg-violet-600 rounded-lg hover:bg-violet-700 transition disabled:opacity-50"
          >
            {mutation.isPending ? 'Creating…' : 'Create Recurring Job'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ScheduledJobs() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);

  const { data: jobs, isLoading, isError, refetch } = useQuery<ScheduledJob[]>({
    queryKey: ['scheduled-jobs'],
    queryFn: async () => (await apiClient.get('/scheduled-jobs/')).data,
    refetchInterval: 30_000,
  });

  const { data: queues } = useQuery<Queue[]>({
    queryKey: ['queues'],
    queryFn: async () => (await apiClient.get('/queues/')).data,
  });

  const toggleMutation = useMutation({
    mutationFn: async ({ id, is_active }: { id: string; is_active: boolean }) => {
      await apiClient.patch(`/scheduled-jobs/${id}`, { is_active: !is_active });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scheduled-jobs'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => apiClient.delete(`/scheduled-jobs/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scheduled-jobs'] }),
  });

  const activeCount = jobs?.filter(j => j.is_active).length ?? 0;
  const inactiveCount = jobs?.filter(j => !j.is_active).length ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-semibold text-slate-800">Recurring Jobs</h2>
          <p className="text-sm text-slate-500 mt-1">Cron-based job templates dispatched automatically by the scheduler.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => refetch()} className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-lg text-sm hover:bg-slate-50 transition shadow-sm">
            <RefreshCw size={14} /> Refresh
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg text-sm hover:bg-violet-700 transition shadow"
          >
            <Plus size={14} /> New Recurring Job
          </button>
        </div>
      </div>

      {/* Summary */}
      {!isLoading && !isError && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex items-center gap-3">
            <div className="p-2 bg-violet-100 rounded-lg"><Calendar className="text-violet-600" size={18} /></div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{jobs?.length ?? 0}</p>
              <p className="text-xs text-slate-500 uppercase tracking-wider">Total Scheduled</p>
            </div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex items-center gap-3">
            <div className="p-2 bg-emerald-100 rounded-lg"><CheckCircle className="text-emerald-600" size={18} /></div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{activeCount}</p>
              <p className="text-xs text-slate-500 uppercase tracking-wider">Active</p>
            </div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex items-center gap-3">
            <div className="p-2 bg-slate-100 rounded-lg"><XCircle className="text-slate-400" size={18} /></div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{inactiveCount}</p>
              <p className="text-xs text-slate-500 uppercase tracking-wider">Paused</p>
            </div>
          </div>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="bg-white rounded-xl border border-slate-200 p-16 flex flex-col items-center gap-4">
          <Loader2 className="animate-spin text-violet-500" size={36} />
          <p className="text-slate-500 text-sm">Loading recurring jobs…</p>
        </div>
      )}

      {/* Error */}
      {isError && !isLoading && (
        <div className="bg-white rounded-xl border border-red-100 p-16 flex flex-col items-center gap-4">
          <ServerCrash className="text-red-400" size={40} />
          <p className="text-slate-700 font-medium">Failed to load recurring jobs</p>
          <button onClick={() => refetch()} className="px-4 py-2 bg-violet-600 text-white rounded-lg text-sm">Try Again</button>
        </div>
      )}

      {/* Table */}
      {!isLoading && !isError && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Name / Expression</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Next Run</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Last Run</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-200">
              {jobs && jobs.length > 0 ? (
                jobs.map(job => (
                  <tr key={job.id} className="hover:bg-slate-50 transition">
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-slate-900">{job.name ?? <span className="text-slate-400 italic">Unnamed</span>}</div>
                      <div className="font-mono text-xs text-violet-700 mt-0.5 bg-violet-50 inline-block px-1.5 py-0.5 rounded">{job.cron_expression}</div>
                    </td>
                    <td className="px-6 py-4">
                      {job.is_active ? (
                        <span className="px-2.5 py-0.5 inline-flex text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800">Active</span>
                      ) : (
                        <span className="px-2.5 py-0.5 inline-flex text-xs font-semibold rounded-full bg-slate-100 text-slate-600">Paused</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-700">
                      <div className="flex items-center gap-1.5">
                        <Clock size={13} className="text-slate-400" />
                        <span>{formatNextRun(job.next_run_at)}</span>
                      </div>
                      <div className="text-xs text-slate-400 mt-0.5">{new Date(job.next_run_at).toLocaleString()}</div>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-500">
                      {job.last_run_at ? new Date(job.last_run_at).toLocaleString() : <span className="text-slate-300">Never</span>}
                    </td>
                    <td className="px-6 py-4 text-right space-x-3">
                      <button
                        onClick={() => toggleMutation.mutate({ id: job.id, is_active: job.is_active })}
                        className={`transition ${job.is_active ? 'text-slate-400 hover:text-amber-600' : 'text-slate-400 hover:text-emerald-600'}`}
                        title={job.is_active ? 'Pause' : 'Resume'}
                      >
                        {job.is_active ? <Pause size={16} /> : <Play size={16} />}
                      </button>
                      <button
                        onClick={() => { if (confirm('Delete this recurring job definition?')) deleteMutation.mutate(job.id); }}
                        className="text-slate-400 hover:text-red-600 transition"
                        title="Delete"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-6 py-16 text-center">
                    <div className="flex flex-col items-center gap-3 text-slate-400">
                      <Calendar size={36} className="text-slate-300" />
                      <p className="font-medium text-slate-500">No recurring jobs yet</p>
                      <p className="text-sm">Create a cron job to run automatically on a schedule.</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal */}
      {showCreate && queues && (
        <CreateModal
          queues={queues}
          onClose={() => setShowCreate(false)}
          onSuccess={() => queryClient.invalidateQueries({ queryKey: ['scheduled-jobs'] })}
        />
      )}
    </div>
  );
}
