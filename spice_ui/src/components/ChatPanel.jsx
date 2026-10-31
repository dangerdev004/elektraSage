import { useEffect, useRef, useState } from 'react';

// Chat with your own model through the local server (/api/chat -> CHAT_URL). The conversation lives in
// memory only; Clear empties it. "Send circuit" attaches the current netlist so the model can see the circuit.
export function ChatPanel({ getNetlist }) {
  const [msgs, setMsgs] = useState([]);
  const [text, setText] = useState('');
  const [withCircuit, setWithCircuit] = useState(true);
  const [busy, setBusy] = useState(false);
  const [cfg, setCfg] = useState(null);
  const end = useRef(null);

  useEffect(() => {
    fetch('/api/chat/config').then((r) => r.json()).then(setCfg).catch(() => setCfg({ configured: false, offline: true }));
  }, []);
  useEffect(() => { end.current?.scrollIntoView?.({ block: 'end' }); }, [msgs, busy]);

  const send = async () => {
    const content = text.trim();
    if (!content || busy) return;
    const history = [...msgs.filter((m) => !m.error), { role: 'user', content }];
    setMsgs([...msgs, { role: 'user', content }]);
    setText('');
    setBusy(true);
    try {
      const context = withCircuit ? getNetlist() : undefined;
      const r = await fetch('/api/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: history.slice(-30), context }),
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) setMsgs((m) => [...m, { role: 'assistant', content: body.error ?? `HTTP ${r.status}`, error: true }]);
      else setMsgs((m) => [...m, { role: 'assistant', content: body.reply }]);
    } catch (e) {
      setMsgs((m) => [...m, { role: 'assistant', content: `Could not reach the server (${e.message}). Start it with "npm run server".`, error: true }]);
    } finally { setBusy(false); }
  };

  return (
    <div className="chat">
      <div className="chat-head">
        <span className="side-label chat-title">Chat{cfg?.configured ? ` · ${cfg.model || cfg.host}` : ''}</span>
        <button type="button" className="mini" onClick={() => setMsgs([])} disabled={!msgs.length}>Clear</button>
      </div>
      <div className="chat-log">
        {cfg && !cfg.configured && (
          <p className="side-note">{cfg.offline ? 'The server is not reachable.' : <>Chat is not set up. Start the server with <code>CHAT_URL</code> pointing at your model (see the README).</>}</p>
        )}
        {msgs.map((m, i) => <div key={i} className={`chat-msg ${m.role}${m.error ? ' error' : ''}`}>{m.content}</div>)}
        {busy && <div className="chat-msg assistant dim">Thinking…</div>}
        <div ref={end} />
      </div>
      <label className="chat-opt"><input type="checkbox" checked={withCircuit} onChange={(e) => setWithCircuit(e.target.checked)} /> Send circuit netlist</label>
      <textarea
        className="chat-input" rows={3} value={text} placeholder="Ask about this circuit…" disabled={cfg ? !cfg.configured : false}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } e.stopPropagation(); }}
      />
      <button type="button" className="top-button" onClick={send} disabled={busy || !text.trim() || (cfg ? !cfg.configured : false)}>Send</button>
    </div>
  );
}
