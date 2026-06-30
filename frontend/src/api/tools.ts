export const API_BASE = 'http://127.0.0.1:8000';

async function postJson(path: string, body: any) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Request failed: ${res.status} ${txt}`);
  }
  return await res.json();
}

export async function webSearch(query: string, max_results = 3) {
  return await postJson('/api/tools/web_search', { query, max_results });
}

export async function executeGoal(goal: string, context: any = {}) {
  return await postJson('/api/execute', { goal, context });
}

export async function pdfRead(path: string, max_pages = 3) {
  return await postJson('/api/tools/pdf_read', { path, max_pages });
}

export async function imageProcess(path: string, action = 'info') {
  return await postJson('/api/tools/image_process', { path, action });
}

export async function calculator(expression: string) {
  return await postJson('/api/tools/calculator', { expression });
}
