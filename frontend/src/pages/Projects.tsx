import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { Layers, Plus, X, Loader2 } from 'lucide-react';

interface Project {
  id: string;
  name: string;
}

export default function Projects() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');

  const { data: projects, isLoading } = useQuery<Project[]>({
    queryKey: ['projects'],
    queryFn: async () => {
      const response = await apiClient.get('/projects/');
      return response.data;
    }
  });

  const createMutation = useMutation({
    mutationFn: async (name: string) => {
      await apiClient.post('/projects/', { name });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setShowCreate(false);
      setNewProjectName('');
    },
  });

  if (isLoading) return (
    <div className="flex justify-center p-16 text-blue-500">
      <Loader2 className="animate-spin" size={32} />
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-semibold text-slate-800">Projects</h2>
          <p className="text-sm text-slate-500 mt-1">Manage your workspaces and job queues.</p>
        </div>
        <button 
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg shadow hover:bg-blue-700 transition"
        >
          <Plus size={16} /> Create Project
        </button>
      </div>

      {showCreate && (
        <div className="bg-white rounded-xl shadow-sm border border-blue-100 p-6 flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <h3 className="font-medium text-slate-800">New Project</h3>
            <button onClick={() => setShowCreate(false)} className="text-slate-400 hover:text-slate-600"><X size={18} /></button>
          </div>
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="e.g. E-commerce Backend"
              className="flex-1 border border-slate-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={newProjectName}
              onChange={e => setNewProjectName(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && newProjectName.trim()) {
                  createMutation.mutate(newProjectName);
                }
              }}
            />
            <button
              onClick={() => createMutation.mutate(newProjectName)}
              disabled={!newProjectName.trim() || createMutation.isPending}
              className="px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
            >
              {createMutation.isPending ? 'Saving...' : 'Save'}
            </button>
          </div>
          {createMutation.isError && <p className="text-sm text-red-500">Failed to create project.</p>}
        </div>
      )}
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {projects?.map(project => (
          <div key={project.id} className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 hover:shadow-md transition cursor-pointer group">
            <div className="flex items-center justify-between mb-4">
              <div className="p-2.5 bg-blue-50 text-blue-600 rounded-lg group-hover:bg-blue-100 transition"><Layers size={22} /></div>
            </div>
            <h3 className="text-lg font-semibold text-slate-800 mb-1">{project.name}</h3>
            <p className="text-slate-500 text-sm font-mono mt-4 truncate">{project.id}</p>
          </div>
        ))}
        {projects?.length === 0 && (
          <div className="col-span-3 text-center py-16 text-slate-500 bg-white rounded-xl border border-dashed border-slate-300 flex flex-col items-center gap-3">
            <Layers size={32} className="text-slate-300" />
            <p className="font-medium">No projects found</p>
            <p className="text-sm">Create your first project to get started.</p>
          </div>
        )}
      </div>
    </div>
  );
}
