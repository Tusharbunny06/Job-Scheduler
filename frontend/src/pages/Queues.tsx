import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { Play, Pause, List, Loader2, ServerCrash, RefreshCw, Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';

interface Queue {
  id: string;
  name: string;
  is_paused: boolean;
  concurrency_limit: number;
}

interface QueueStats {
  queued: number;
  scheduled: number;
  claimed: number;
  running: number;
  completed: number;
  failed: number;
  dlq: number;
  total: number;
}

// ── Edit Queue Modal ───────────────────────────────────────────────────────────

function EditQueueModal({ queue, onClose, onSuccess }: { queue: Queue; onClose: () => void; onSuccess: () => void }) {
  const [concurrency, setConcurrency] = useState(queue.concurrency_limit || 5);
  const [priority, setPriority] = useState((queue as any).priority || 1);
  const [strategy, setStrategy] = useState((queue as any).retry_policy?.strategy || 'exponential_backoff');
  const [maxRetries, setMaxRetries] = useState((queue as any).retry_policy?.max_retries || 3);
  const [delay, setDelay] = useState((queue as any).retry_policy?.delay_seconds || 60);

  const editMutation = useMutation({
    mutationFn: async () => {
      await apiClient.patch(`/queues/${queue.id}`, {
        concurrency_limit: concurrency,
        priority: priority,
        retry_policy: {
          strategy,
          max_retries: maxRetries,
          delay_seconds: delay,
          backoff_multiplier: 2.0
        }
      });
    },
    onSuccess: () => {
      onSuccess();
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm p-6 animate-fade-in">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Configure Queue: {queue.name}</h3>
        
        <div className="space-y-4">
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Concurrency Limit</label>
              <input
                type="number" min={1} max={100}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={concurrency}
                onChange={e => setConcurrency(Number(e.target.value))}
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Priority</label>
              <input
                type="number" min={1} max={10}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={priority}
                onChange={e => setPriority(Number(e.target.value))}
              />
            </div>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-slate-700 mb-2 border-b pb-1">Retry Policy</h4>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Strategy</label>
                <select 
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={strategy}
                  onChange={e => setStrategy(e.target.value)}
                >
                  <option value="fixed_delay">Fixed Delay</option>
                  <option value="linear_backoff">Linear Backoff</option>
                  <option value="exponential_backoff">Exponential Backoff</option>
                </select>
              </div>
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Max Retries</label>
                  <input
                    type="number" min={0} max={10}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={maxRetries}
                    onChange={e => setMaxRetries(Number(e.target.value))}
                  />
                </div>
                <div className="flex-1">
                  <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Base Delay (s)</label>
                  <input
                    type="number" min={1}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={delay}
                    onChange={e => setDelay(Number(e.target.value))}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg text-sm hover:bg-slate-200 transition">Cancel</button>
          <button 
            onClick={() => editMutation.mutate()} 
            disabled={editMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition disabled:opacity-50"
          >
            {editMutation.isPending ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Create Queue Modal ───────────────────────────────────────────────────────

function CreateQueueModal({ projects, onClose, onSuccess }: { projects: any[]; onClose: () => void; onSuccess: () => void }) {
  const [name, setName] = useState('');
  const [concurrency, setConcurrency] = useState(5);
  const [priority, setPriority] = useState(1);
  const [strategy, setStrategy] = useState('exponential_backoff');
  const [maxRetries, setMaxRetries] = useState(3);
  const [delay, setDelay] = useState(60);

  const createMutation = useMutation({
    mutationFn: async () => {
      const projectId = projects?.[0]?.id;
      if (!projectId) throw new Error("No projects found");
      await apiClient.post('/queues/', { 
        project_id: projectId,
        name,
        concurrency_limit: concurrency,
        priority: priority,
        retry_policy: {
          strategy: strategy,
          max_retries: maxRetries,
          delay_seconds: delay,
          backoff_multiplier: 2.0
        }
      });
    },
    onSuccess: () => {
      onSuccess();
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto animate-fade-in">
        <h3 className="text-lg font-semibold text-slate-800 mb-6">Create New Queue</h3>
        
        <div className="space-y-6">
          {/* Basic Settings */}
          <div>
            <h4 className="text-sm font-semibold text-slate-700 mb-3 border-b pb-1">Basic Settings</h4>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Queue Name</label>
                <input
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g. video-processing"
                  value={name}
                  onChange={e => setName(e.target.value)}
                />
              </div>
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Concurrency Limit</label>
                  <input
                    type="number" min={1} max={100}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={concurrency}
                    onChange={e => setConcurrency(Number(e.target.value))}
                  />
                </div>
                <div className="flex-1">
                  <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Priority (1-10)</label>
                  <input
                    type="number" min={1} max={10}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={priority}
                    onChange={e => setPriority(Number(e.target.value))}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Retry Policy */}
          <div>
            <h4 className="text-sm font-semibold text-slate-700 mb-3 border-b pb-1">Retry Policy (Failure Handling)</h4>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Strategy</label>
                <select 
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={strategy}
                  onChange={e => setStrategy(e.target.value)}
                >
                  <option value="fixed_delay">Fixed Delay</option>
                  <option value="linear_backoff">Linear Backoff</option>
                  <option value="exponential_backoff">Exponential Backoff</option>
                </select>
              </div>
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Max Retries</label>
                  <input
                    type="number" min={0} max={10}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={maxRetries}
                    onChange={e => setMaxRetries(Number(e.target.value))}
                  />
                </div>
                <div className="flex-1">
                  <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Base Delay (seconds)</label>
                  <input
                    type="number" min={1}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={delay}
                    onChange={e => setDelay(Number(e.target.value))}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {createMutation.isError && (
          <p className="text-red-500 text-xs mt-4">Failed to create queue. Make sure you have a project created.</p>
        )}

        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg text-sm hover:bg-slate-200 transition">Cancel</button>
          <button 
            onClick={() => createMutation.mutate()} 
            disabled={createMutation.isPending || !name.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition disabled:opacity-50"
          >
            {createMutation.isPending ? 'Creating...' : 'Create Queue'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Queues Page ──────────────────────────────────────────────────────────────

export default function Queues() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [editQueue, setEditQueue] = useState<Queue | null>(null);

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => (await apiClient.get('/projects/')).data,
  });

  const { data: queues, isLoading, isError, refetch } = useQuery<Queue[]>({
    queryKey: ['queues'],
    queryFn: async () => {
      const response = await apiClient.get('/queues/');
      return response.data;
    },
    retry: 1,
    refetchInterval: 10_000, // Poll every 10s
  });

  const togglePauseMutation = useMutation({
    mutationFn: async ({ id, is_paused }: { id: string; is_paused: boolean }) => {
      await apiClient.patch(`/queues/${id}`, { is_paused: !is_paused });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['queues'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/queues/${id}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['queues'] }),
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-semibold text-slate-800">Queues Configuration</h2>
          <p className="text-sm text-slate-500 mt-1">Manage your job queues, priority levels, and retry policies.</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded-lg shadow-sm hover:bg-slate-50 transition text-sm"
          >
            <RefreshCw size={15} />
            Refresh
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg shadow hover:bg-blue-700 transition text-sm"
          >
            <Plus size={15} />
            Create Queue
          </button>
        </div>
      </div>

      {/* Loading & Error States */}
      {isLoading && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-16 flex flex-col items-center justify-center gap-4">
          <Loader2 className="animate-spin text-blue-500" size={36} />
          <p className="text-slate-500 text-sm font-medium">Loading queues…</p>
        </div>
      )}
      {isError && !isLoading && (
        <div className="bg-white rounded-xl shadow-sm border border-red-100 p-16 flex flex-col items-center justify-center gap-4">
          <ServerCrash className="text-red-400" size={40} />
          <p className="text-slate-700 font-medium">Failed to load queues</p>
          <button onClick={() => refetch()} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm">Try Again</button>
        </div>
      )}

      {/* Queues Table */}
      {!isLoading && !isError && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Queue Name</th>
                <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Configuration</th>
                <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Live Stats</th>
                <th className="px-6 py-4 text-right text-xs font-bold text-slate-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-100">
              {queues && queues.length > 0 ? (
                queues.map(queue => (
                  <tr key={queue.id} className="hover:bg-slate-50 transition">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-slate-900">{queue.name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {queue.is_paused ? (
                        <span className="px-2.5 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full bg-amber-100 text-amber-800">Paused</span>
                      ) : (
                        <span className="px-2.5 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full bg-emerald-100 text-emerald-800">Active</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                      <div className="flex flex-col gap-1">
                        <span>Concurrency: <span className="font-semibold text-slate-700">{queue.concurrency_limit}</span></span>
                        <span className="text-xs">Priority: <span className="font-medium text-slate-700">{(queue as any).priority || 1}</span></span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <QueueStatsCell queueId={queue.id} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-3">
                      <button
                        className="text-blue-600 hover:text-blue-800 transition font-semibold"
                        onClick={() => setEditQueue(queue)}
                        title="Configure"
                      >
                        Configure
                      </button>
                      <button
                        className={`transition font-semibold ${queue.is_paused ? 'text-emerald-600 hover:text-emerald-800' : 'text-amber-600 hover:text-amber-800'}`}
                        onClick={() => togglePauseMutation.mutate({ id: queue.id, is_paused: queue.is_paused })}
                      >
                        {queue.is_paused ? 'Resume' : 'Pause'}
                      </button>
                      <button
                        className="text-red-500 hover:text-red-700 transition"
                        title="Delete Queue"
                        onClick={() => { if (confirm("Delete this queue and all its jobs?")) deleteMutation.mutate(queue.id); }}
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
                      <List size={36} className="text-slate-300" />
                      <p className="font-medium text-slate-500">No queues yet</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Modals */}
      {showCreate && projects && (
        <CreateQueueModal projects={projects} onClose={() => setShowCreate(false)} onSuccess={() => queryClient.invalidateQueries({ queryKey: ['queues'] })} />
      )}
      {editQueue && (
        <EditQueueModal queue={editQueue} onClose={() => setEditQueue(null)} onSuccess={() => queryClient.invalidateQueries({ queryKey: ['queues'] })} />
      )}
    </div>
  );
}

// Extracted QueueStats logic to a separate component so it can run inside the map smoothly
function QueueStatsCell({ queueId }: { queueId: string }) {
  const { data: stats } = useQuery<QueueStats>({
    queryKey: ['queue-stats', queueId],
    queryFn: async () => (await apiClient.get(`/queues/${queueId}/stats`)).data,
    refetchInterval: 10_000,
  });

  if (!stats) return <span className="text-xs text-slate-400">Loading...</span>;
  return (
    <div className="flex gap-3 text-xs">
      <span className="text-slate-500">Q: <span className="font-medium text-amber-600">{stats.queued}</span></span>
      <span className="text-slate-500">R: <span className="font-medium text-blue-600">{stats.running}</span></span>
      <span className="text-slate-500">F: <span className="font-medium text-red-600">{stats.failed}</span></span>
    </div>
  );
}
