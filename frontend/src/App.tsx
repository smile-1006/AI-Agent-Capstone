import React, { useEffect, useMemo, useState } from 'react';

type HealthResponse = { status: string };

type ExecuteRequest = {
  goal: string;
};

type ExecuteResponse = {
  request_id: string;
  route: string;
  plan: unknown;
  research: unknown;
  draft: unknown;
  final: unknown;
};

type MessageRole = 'user' | 'assistant' | 'system';

type ChatMessage = {
  id: string;
  role: MessageRole;
  content: string;
};

const API_BASE = 'http://127.0.0.1:8000';

function uid(): string {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function GlassPanel({
  title,
  children,
}: {
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-[0_0_50px_rgba(0,0,0,0.25)]">
      {title ? (
        <div className="px-5 py-3 border-b border-white/10">
          <div className="text-sm font-semibold text-white/90">{title}</div>
        </div>
      ) : null}
      <div className={title ? 'p-5' : 'p-0'}>{children}</div>
    </div>
  );
}

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [goal, setGoal] = useState<string>('What is the weather forecast for tomorrow?');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: uid(),
      role: 'assistant',
      content: 'Ask a question and the agent pipeline will generate a plan, research, draft, review and final response.',
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState<ExecuteResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadHealth() {
      try {
        const res = await fetch(`${API_BASE}/api/health`);
        if (!res.ok) throw new Error(`Health request failed: ${res.status}`);
        const data = (await res.json()) as HealthResponse;
        if (!cancelled) setHealth(data);
      } catch (e) {
        if (!cancelled) setHealth({ status: 'unavailable' });
      }
    }

    loadHealth();
    return () => {
      cancelled = true;
    };
  }, []);

  const placeholder = useMemo(() => {
    return 'Enter your goal...';
  }, []);

  async function onExecute() {
    setError(null);
    setLoading(true);

    const userMsg: ChatMessage = { id: uid(), role: 'user', content: goal.trim() || '' };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const payload: ExecuteRequest = { goal: goal.trim() };
      const resp = await fetch(`${API_BASE}/api/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`Execute failed: ${resp.status} ${text}`);
      }

      const data = (await resp.json()) as ExecuteResponse;
      setLastResponse(data);

      const assistantContent =
        typeof data.final === 'string'
          ? data.final
          : 'Execution completed. See response details on the right.';

      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: 'assistant',
          content: assistantContent,
        },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-violet-500/20 via-transparent to-transparent" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom,_var(--tw-gradient-stops))] from-cyan-500/15 via-transparent to-transparent" />

      <div className="relative max-w-6xl mx-auto px-4 py-10">
        <header className="flex items-start justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">AI Agent Capstone</h1>
            <p className="text-sm text-white/70 mt-1">
              Production-grade multi-agent pipeline with MCP + memory.
            </p>
          </div>

          <div className="text-right">
            <div className="text-xs text-white/60">Backend status</div>
            <div className="inline-flex items-center gap-2 mt-1">
              <span
                className={
                  'h-2.5 w-2.5 rounded-full ' +
                  (health?.status === 'ok'
                    ? 'bg-emerald-400'
                    : 'bg-amber-400')
                }
              />
              <div className="text-sm text-white/90">
                {health ? health.status : 'checking...'}
              </div>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2">
            <GlassPanel title="Chat">
              <div className="flex flex-col h-[520px]">
                <div className="flex-1 overflow-auto pr-2 space-y-3">
                  {messages.map((m) => {
                    const isUser = m.role === 'user';
                    return (
                      <div
                        key={m.id}
                        className={
                          'flex ' +
                          (isUser ? 'justify-end' : 'justify-start')
                        }
                      >
                        <div
                          className={
                            'max-w-[85%] rounded-2xl border px-4 py-3 ' +
                            (isUser
                              ? 'border-white/10 bg-white/8'
                              : 'border-white/10 bg-white/5')
                          }
                        >
                          <div className="text-xs font-semibold text-white/70 mb-1">
                            {m.role === 'user' ? 'You' : 'Agent'}
                          </div>
                          <div className="text-sm text-white/90 whitespace-pre-wrap">
                            {m.content}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  {loading ? (
                    <div className="text-sm text-white/70">Agent is executing...</div>
                  ) : null}
                </div>

                <div className="mt-4">
                  <label className="block text-xs text-white/60 mb-2">Goal / request</label>
                  <textarea
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-violet-500/50"
                    rows={3}
                    value={goal}
                    placeholder={placeholder}
                    onChange={(e) => setGoal(e.target.value)}
                  />

                  {error ? (
                    <div className="mt-3 text-sm text-red-300">{error}</div>
                  ) : null}

                  <div className="flex items-center justify-between mt-4">
                    <div className="text-xs text-white/60">
                      Endpoint: <span className="text-white/80">POST /api/execute</span>
                    </div>
                    <button
                      onClick={onExecute}
                      disabled={loading || !goal.trim()}
                      className="rounded-xl bg-violet-500/90 hover:bg-violet-500 text-white px-5 py-2 text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loading ? 'Executing...' : 'Execute'}
                    </button>
                  </div>
                </div>
              </div>
            </GlassPanel>
          </div>

          <div>
            <GlassPanel title="Execution Details">
              <div className="space-y-4">
                {lastResponse ? (
                  <>
                    <div className="text-xs text-white/60">Request ID</div>
                    <div className="text-sm text-white/90 break-all">{lastResponse.request_id}</div>

                    <div className="h-px bg-white/10" />

                    <div className="text-xs text-white/60">Route</div>
                    <div className="text-sm text-white/90">{lastResponse.route}</div>

                    <div className="h-px bg-white/10" />

                    <details className="group">
                      <summary className="cursor-pointer text-sm text-white/80">Plan</summary>
                      <pre className="mt-2 text-xs text-white/70 overflow-auto max-h-40 whitespace-pre-wrap">
                        {JSON.stringify(lastResponse.plan, null, 2)}
                      </pre>
                    </details>

                    <details className="group">
                      <summary className="cursor-pointer text-sm text-white/80">Research</summary>
                      <pre className="mt-2 text-xs text-white/70 overflow-auto max-h-40 whitespace-pre-wrap">
                        {JSON.stringify(lastResponse.research, null, 2)}
                      </pre>
                    </details>

                    <details className="group">
                      <summary className="cursor-pointer text-sm text-white/80">Final</summary>
                      <pre className="mt-2 text-xs text-white/70 overflow-auto max-h-40 whitespace-pre-wrap">
                        {typeof lastResponse.final === 'string'
                          ? lastResponse.final
                          : JSON.stringify(lastResponse.final, null, 2)}
                      </pre>
                    </details>
                  </>
                ) : (
                  <div className="text-sm text-white/70">
                    Execute a goal to see the agent pipeline breakdown here.
                  </div>
                )}
              </div>
            </GlassPanel>
          </div>
        </div>

        <footer className="mt-10 text-xs text-white/50 text-center">
          Built with React + Tailwind glassmorphism UI. Backend served by FastAPI.
        </footer>
      </div>
    </div>
  );
}

