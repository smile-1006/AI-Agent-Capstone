import React, { useState } from 'react';
import { calculator } from '../api/tools';

export default function CalculatorWidget() {
  const [expr, setExpr] = useState('123+45');
  const [events, setEvents] = useState<string[]>([]);
  const [result, setResult] = useState<string | number | null>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    setEvents([]);
    setResult(null);
    setLoading(true);
    try {
      const res = await calculator(expr);
      // If backend returns an `events` array, animate them sequentially
      const ev: string[] = res.events || [];
      for (let i = 0; i < ev.length; i++) {
        // show each event with a small delay
        // eslint-disable-next-line no-await-in-loop
        await new Promise((r) => setTimeout(r, 250));
        setEvents((prev) => [...prev, ev[i]]);
      }
      // show final result
      setResult(res.result ?? res);
    } catch (e: any) {
      setEvents((p) => [...p, 'error: ' + (e?.message || String(e))]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ border: '1px solid #ccc', padding: 12, borderRadius: 6, maxWidth: 420 }}>
      <h3>Local Calculator (Windows)</h3>
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <input
          value={expr}
          onChange={(e) => setExpr(e.target.value)}
          style={{ flex: 1, padding: 8, fontSize: 16 }}
        />
        <button onClick={run} disabled={loading} style={{ padding: '8px 12px' }}>
          {loading ? 'Running…' : 'Run'}
        </button>
      </div>

      <div style={{ minHeight: 48 }}>
        <strong>Events:</strong>
        <ul>
          {events.map((ev, i) => (
            <li key={i}>{ev}</li>
          ))}
        </ul>
      </div>

      <div>
        <strong>Result:</strong>{' '}
        <span style={{ fontSize: 20 }}>{result === null ? '—' : String(result)}</span>
      </div>

      <div style={{ marginTop: 8, color: '#666', fontSize: 12 }}>
        Note: make sure `LOCAL_CALCULATOR_CMD=windows_calc` and `pywinauto` are installed
        and the backend runs in your interactive desktop session.
      </div>
    </div>
  );
}
