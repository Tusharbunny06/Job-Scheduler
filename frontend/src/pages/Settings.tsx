import { useState } from 'react';
import { Settings, Bell, Shield, Palette, Server, ChevronRight, Check } from 'lucide-react';

type SettingSection = 'general' | 'notifications' | 'security' | 'appearance' | 'api';

const sections: { id: SettingSection; label: string; icon: React.ReactNode; description: string }[] = [
  { id: 'general',       label: 'General',       icon: <Settings size={18} />,  description: 'Application preferences and defaults' },
  { id: 'notifications', label: 'Notifications', icon: <Bell size={18} />,      description: 'Configure alerts and event triggers' },
  { id: 'security',      label: 'Security',      icon: <Shield size={18} />,    description: 'Authentication and access control' },
  { id: 'appearance',    label: 'Appearance',    icon: <Palette size={18} />,   description: 'Theme, layout, and display options' },
  { id: 'api',           label: 'API',           icon: <Server size={18} />,    description: 'API keys and integration settings' },
];

function SaveBanner({ visible, onDismiss }: { visible: boolean; onDismiss: () => void }) {
  if (!visible) return null;
  return (
    <div className="fixed bottom-6 right-6 flex items-center gap-3 bg-emerald-600 text-white px-5 py-3 rounded-xl shadow-lg animate-fade-in z-50">
      <Check size={18} />
      <span className="text-sm font-medium">Settings saved successfully</span>
      <button onClick={onDismiss} className="ml-2 text-emerald-200 hover:text-white text-xs">✕</button>
    </div>
  );
}

export default function SettingsPage() {
  const [active, setActive] = useState<SettingSection>('general');
  const [saved, setSaved] = useState(false);

  // General settings state
  const [timezone, setTimezone] = useState('Asia/Kolkata');
  const [maxRetries, setMaxRetries] = useState(3);
  const [jobTimeout, setJobTimeout] = useState(300);

  // Notification settings state
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [failureAlerts, setFailureAlerts] = useState(true);
  const [successAlerts, setSuccessAlerts] = useState(false);
  const [alertEmail, setAlertEmail] = useState('admin@example.com');

  // Security settings state
  const [sessionTimeout, setSessionTimeout] = useState(60);
  const [twoFactor, setTwoFactor] = useState(false);

  // Appearance settings state
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>('light');
  const [compactMode, setCompactMode] = useState(false);
  const [showTimestamps, setShowTimestamps] = useState(true);

  // API settings state
  const [apiKey] = useState('sk-job-scheduler-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx');
  const [webhookUrl, setWebhookUrl] = useState('');

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const activeSection = sections.find(s => s.id === active)!;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-800">Settings</h2>
        <p className="text-sm text-slate-500 mt-1">Manage your application configuration</p>
      </div>

      <div className="flex gap-6 min-h-[500px]">
        {/* Sidebar Nav */}
        <div className="w-60 shrink-0 bg-white rounded-xl shadow-sm border border-slate-200 p-3 h-fit">
          {sections.map(s => (
            <button
              key={s.id}
              onClick={() => setActive(s.id)}
              className={`w-full flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg text-sm transition mb-1 ${
                active === s.id
                  ? 'bg-blue-50 text-blue-700 font-medium'
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <div className="flex items-center gap-3">
                <span className={active === s.id ? 'text-blue-600' : 'text-slate-400'}>{s.icon}</span>
                {s.label}
              </div>
              {active === s.id && <ChevronRight size={14} className="text-blue-400" />}
            </button>
          ))}
        </div>

        {/* Settings Panel */}
        <div className="flex-1 bg-white rounded-xl shadow-sm border border-slate-200 p-8">
          <div className="mb-6 pb-5 border-b border-slate-100">
            <h3 className="text-lg font-semibold text-slate-800">{activeSection.label}</h3>
            <p className="text-sm text-slate-500 mt-0.5">{activeSection.description}</p>
          </div>

          {/* General */}
          {active === 'general' && (
            <div className="space-y-6">
              <SettingRow label="Default Timezone" hint="Used for scheduled job times">
                <select
                  value={timezone}
                  onChange={e => setTimezone(e.target.value)}
                  className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-56"
                >
                  <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">America/New_York (EST)</option>
                  <option value="Europe/London">Europe/London (GMT)</option>
                  <option value="Asia/Tokyo">Asia/Tokyo (JST)</option>
                </select>
              </SettingRow>
              <SettingRow label="Max Job Retries" hint="Number of retry attempts before marking a job as failed">
                <input
                  type="number" min={0} max={10}
                  value={maxRetries}
                  onChange={e => setMaxRetries(Number(e.target.value))}
                  className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-24"
                />
              </SettingRow>
              <SettingRow label="Job Timeout (seconds)" hint="Maximum execution time before a job is killed">
                <input
                  type="number" min={30} step={30}
                  value={jobTimeout}
                  onChange={e => setJobTimeout(Number(e.target.value))}
                  className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-28"
                />
              </SettingRow>
            </div>
          )}

          {/* Notifications */}
          {active === 'notifications' && (
            <div className="space-y-6">
              <SettingRow label="Alert Email" hint="Where system notifications are sent">
                <input
                  type="email"
                  value={alertEmail}
                  onChange={e => setAlertEmail(e.target.value)}
                  className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-72"
                  placeholder="you@example.com"
                />
              </SettingRow>
              <SettingRow label="Email Alerts" hint="Receive notifications via email">
                <Toggle value={emailAlerts} onChange={setEmailAlerts} />
              </SettingRow>
              <SettingRow label="Failure Alerts" hint="Alert when a job fails or is moved to DLQ">
                <Toggle value={failureAlerts} onChange={setFailureAlerts} />
              </SettingRow>
              <SettingRow label="Success Alerts" hint="Alert when a job completes successfully">
                <Toggle value={successAlerts} onChange={setSuccessAlerts} />
              </SettingRow>
            </div>
          )}

          {/* Security */}
          {active === 'security' && (
            <div className="space-y-6">
              <SettingRow label="Session Timeout (minutes)" hint="Automatically log out after inactivity">
                <select
                  value={sessionTimeout}
                  onChange={e => setSessionTimeout(Number(e.target.value))}
                  className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-40"
                >
                  <option value={15}>15 minutes</option>
                  <option value={30}>30 minutes</option>
                  <option value={60}>1 hour</option>
                  <option value={240}>4 hours</option>
                  <option value={0}>Never</option>
                </select>
              </SettingRow>
              <SettingRow label="Two-Factor Authentication" hint="Require 2FA for all logins">
                <Toggle value={twoFactor} onChange={setTwoFactor} />
              </SettingRow>
              <div className="pt-4 border-t border-slate-100">
                <button className="px-4 py-2 border border-red-200 text-red-600 rounded-lg text-sm hover:bg-red-50 transition">
                  Change Password
                </button>
              </div>
            </div>
          )}

          {/* Appearance */}
          {active === 'appearance' && (
            <div className="space-y-6">
              <SettingRow label="Theme" hint="Choose your preferred color scheme">
                <div className="flex gap-2">
                  {(['light', 'dark', 'system'] as const).map(t => (
                    <button
                      key={t}
                      onClick={() => setTheme(t)}
                      className={`px-4 py-2 rounded-lg border text-sm capitalize transition ${
                        theme === t
                          ? 'bg-blue-600 text-white border-blue-600'
                          : 'bg-white text-slate-600 border-slate-300 hover:border-blue-400'
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </SettingRow>
              <SettingRow label="Compact Mode" hint="Use a denser layout for more information on screen">
                <Toggle value={compactMode} onChange={setCompactMode} />
              </SettingRow>
              <SettingRow label="Show Timestamps" hint="Display relative or absolute timestamps on jobs">
                <Toggle value={showTimestamps} onChange={setShowTimestamps} />
              </SettingRow>
            </div>
          )}

          {/* API */}
          {active === 'api' && (
            <div className="space-y-6">
              <SettingRow label="API Key" hint="Your secret key for API access — keep it safe">
                <div className="flex items-center gap-2">
                  <input
                    readOnly
                    value={apiKey}
                    type="password"
                    className="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-slate-50 w-80 font-mono"
                  />
                  <button
                    onClick={() => navigator.clipboard.writeText(apiKey)}
                    className="px-3 py-2 bg-slate-100 rounded-lg text-xs hover:bg-slate-200 transition text-slate-600"
                  >
                    Copy
                  </button>
                </div>
              </SettingRow>
              <SettingRow label="Webhook URL" hint="POST request sent when job status changes">
                <input
                  type="url"
                  value={webhookUrl}
                  onChange={e => setWebhookUrl(e.target.value)}
                  className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-80"
                  placeholder="https://your-server.com/webhook"
                />
              </SettingRow>
              <div className="pt-4 border-t border-slate-100">
                <button className="px-4 py-2 border border-amber-200 text-amber-700 rounded-lg text-sm hover:bg-amber-50 transition">
                  Regenerate API Key
                </button>
              </div>
            </div>
          )}

          {/* Save Button */}
          <div className="mt-8 pt-6 border-t border-slate-100 flex justify-end">
            <button
              onClick={handleSave}
              className="px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition shadow-sm"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>

      <SaveBanner visible={saved} onDismiss={() => setSaved(false)} />
    </div>
  );
}

function SettingRow({ label, hint, children }: { label: string; hint: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-8">
      <div className="flex-1">
        <p className="text-sm font-medium text-slate-800">{label}</p>
        <p className="text-xs text-slate-500 mt-0.5">{hint}</p>
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!value)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${value ? 'bg-blue-600' : 'bg-slate-200'}`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform ${value ? 'translate-x-6' : 'translate-x-1'}`}
      />
    </button>
  );
}
