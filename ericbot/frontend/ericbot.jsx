import React, { useState, useEffect, useRef } from "react";

const API = "http://localhost:8000/api";

const VENTURES = {
  hatch: { label: "Hatch", emoji: "🌿", color: "#22c55e" },
  eric_digital: { label: "Eric.Digital", emoji: "💻", color: "#3b82f6" },
  ancient_coast: { label: "Ancient Coast", emoji: "🏠", color: "#f59e0b" },
  nexus: { label: "NEXUS", emoji: "🤖", color: "#8b5cf6" },
};

const STATUSES = ["new", "contacted", "qualified", "proposal", "won", "lost", "nurture"];

// ── Utilities ────────────────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

function Badge({ text, color }) {
  return (
    <span
      style={{
        background: color + "22",
        color,
        border: `1px solid ${color}55`,
        borderRadius: 4,
        padding: "1px 8px",
        fontSize: 12,
        fontWeight: 600,
      }}
    >
      {text}
    </span>
  );
}

function Card({ title, children, action }) {
  return (
    <div style={{ background: "#1e1e2e", borderRadius: 12, padding: 20, marginBottom: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={{ margin: 0, color: "#cdd6f4", fontSize: 15, fontWeight: 700 }}>{title}</h3>
        {action}
      </div>
      {children}
    </div>
  );
}

function Metric({ label, value, sub }) {
  return (
    <div style={{ textAlign: "center", padding: "12px 16px" }}>
      <div style={{ fontSize: 28, fontWeight: 800, color: "#cdd6f4" }}>{value}</div>
      <div style={{ fontSize: 12, color: "#6c7086", marginTop: 2 }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: "#f38ba8", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

// ── Dashboard Tab ─────────────────────────────────────────────────────────────

function DashboardTab() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const load = async () => {
    try {
      const d = await apiFetch("/dashboard");
      setData(d);
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => { load(); }, []);

  if (error) return <p style={{ color: "#f38ba8" }}>Error: {error}</p>;
  if (!data) return <p style={{ color: "#6c7086" }}>Loading...</p>;

  const m = data.metrics;
  const conf = Math.round(m.voice_confidence * 100);

  return (
    <div>
      <Card title="Command Center">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
          <Metric label="Total Leads" value={m.total_leads} />
          <Metric label="New Leads" value={m.new_leads} />
          <Metric
            label="Follow-ups Due"
            value={m.followups_due}
            sub={m.followups_due > 0 ? "⚠ Act now" : null}
          />
          <Metric label="Won Revenue" value={`$${m.won_revenue.toLocaleString()}`} />
          <Metric label="Pending Tasks" value={m.pending_tasks} />
          <Metric
            label="Overdue Tasks"
            value={m.overdue_tasks}
            sub={m.overdue_tasks > 0 ? "⚠ Overdue" : null}
          />
          <Metric label="Voice Samples" value={m.voice_samples} />
          <Metric label="Voice Confidence" value={`${conf}%`} />
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card title="Pipeline by Venture">
          {Object.keys(VENTURES).map((v) => (
            <div
              key={v}
              style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid #313244" }}
            >
              <span style={{ color: VENTURES[v].color }}>
                {VENTURES[v].emoji} {VENTURES[v].label}
              </span>
              <Badge text={data.pipeline_by_venture[v] || 0} color={VENTURES[v].color} />
            </div>
          ))}
        </Card>

        <Card title="Urgent Follow-ups">
          {data.urgent_followups.length === 0 ? (
            <p style={{ color: "#6c7086", fontSize: 13 }}>All clear 🎉</p>
          ) : (
            data.urgent_followups.map((l) => (
              <div key={l.id} style={{ padding: "6px 0", borderBottom: "1px solid #313244" }}>
                <div style={{ fontWeight: 600, color: "#cdd6f4" }}>{l.name}</div>
                <div style={{ fontSize: 12, color: "#6c7086" }}>
                  {VENTURES[l.venture]?.emoji} {l.venture} · {l.contact}
                </div>
              </div>
            ))
          )}
        </Card>
      </div>

      <Card title="Top Tasks">
        {data.top_tasks.length === 0 ? (
          <p style={{ color: "#6c7086", fontSize: 13 }}>No pending tasks</p>
        ) : (
          data.top_tasks.map((t) => (
            <div key={t.id} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid #313244" }}>
              <div>
                <span style={{ color: "#cdd6f4" }}>{t.title}</span>
                {t.venture && (
                  <span style={{ marginLeft: 8, fontSize: 12, color: VENTURES[t.venture]?.color }}>
                    {VENTURES[t.venture]?.emoji} {t.venture}
                  </span>
                )}
              </div>
              <Badge
                text={t.priority}
                color={t.priority === "high" ? "#f38ba8" : t.priority === "medium" ? "#f9e2af" : "#a6e3a1"}
              />
            </div>
          ))
        )}
      </Card>
    </div>
  );
}

// ── Chat Tab ──────────────────────────────────────────────────────────────────

function ChatTab() {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "What's up? I'm EricBot — your AI clone. Tell me what you need." },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [confidence, setConfidence] = useState(0);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const msg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    setLoading(true);
    try {
      const data = await apiFetch("/chat", {
        method: "POST",
        body: JSON.stringify({ message: msg, include_history: true }),
      });
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
      setConfidence(data.voice_confidence);
    } catch (e) {
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${e.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 160px)" }}>
      <div style={{ fontSize: 12, color: "#6c7086", marginBottom: 8 }}>
        Voice confidence: <span style={{ color: confidence > 0.6 ? "#a6e3a1" : "#f9e2af" }}>{Math.round(confidence * 100)}%</span>
      </div>
      <div style={{ flex: 1, overflowY: "auto", background: "#1e1e2e", borderRadius: 12, padding: 16, marginBottom: 12 }}>
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              justifyContent: m.role === "user" ? "flex-end" : "flex-start",
              marginBottom: 12,
            }}
          >
            <div
              style={{
                maxWidth: "72%",
                padding: "10px 14px",
                borderRadius: m.role === "user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                background: m.role === "user" ? "#89b4fa" : "#313244",
                color: m.role === "user" ? "#1e1e2e" : "#cdd6f4",
                fontSize: 14,
                lineHeight: 1.5,
                whiteSpace: "pre-wrap",
              }}
            >
              {m.content}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ color: "#6c7086", fontSize: 13, fontStyle: "italic" }}>EricBot is typing...</div>
        )}
        <div ref={bottomRef} />
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          style={{
            flex: 1,
            background: "#1e1e2e",
            border: "1px solid #45475a",
            borderRadius: 8,
            color: "#cdd6f4",
            padding: "10px 14px",
            fontSize: 14,
            outline: "none",
          }}
          placeholder="Ask EricBot anything..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <button
          onClick={send}
          disabled={loading}
          style={{
            background: "#89b4fa",
            color: "#1e1e2e",
            border: "none",
            borderRadius: 8,
            padding: "10px 20px",
            fontWeight: 700,
            cursor: loading ? "default" : "pointer",
            opacity: loading ? 0.6 : 1,
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}

// ── Leads Tab ─────────────────────────────────────────────────────────────────

function LeadsTab() {
  const [leads, setLeads] = useState([]);
  const [filter, setFilter] = useState({ venture: "", status: "" });
  const [form, setForm] = useState({ name: "", contact: "", venture: "hatch", source: "", notes: "", value: 0 });
  const [showForm, setShowForm] = useState(false);
  const [draft, setDraft] = useState({ lead_id: null, text: "", loading: false });

  const load = async () => {
    const params = new URLSearchParams();
    if (filter.venture) params.set("venture", filter.venture);
    if (filter.status) params.set("status", filter.status);
    const data = await apiFetch(`/leads?${params}`);
    setLeads(data);
  };

  useEffect(() => { load(); }, [filter]);

  const createLead = async () => {
    await apiFetch("/leads", { method: "POST", body: JSON.stringify({ ...form, value: parseFloat(form.value) || 0 }) });
    setForm({ name: "", contact: "", venture: "hatch", source: "", notes: "", value: 0 });
    setShowForm(false);
    load();
  };

  const updateStatus = async (id, status) => {
    await apiFetch(`/leads/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
    load();
  };

  const generateDraft = async (lead) => {
    setDraft({ lead_id: lead.id, text: "", loading: true });
    try {
      const data = await apiFetch(`/leads/draft?lead_id=${lead.id}&channel=email&context=${encodeURIComponent(lead.notes || "follow-up")}`);
      setDraft({ lead_id: lead.id, text: data.draft, loading: false });
    } catch (e) {
      setDraft({ lead_id: lead.id, text: `Error: ${e.message}`, loading: false });
    }
  };

  const sel = { background: "#1e1e2e", border: "1px solid #45475a", borderRadius: 6, color: "#cdd6f4", padding: "6px 10px", fontSize: 13 };
  const inp = { ...sel, width: "100%" };

  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, alignItems: "center" }}>
        <select style={sel} value={filter.venture} onChange={(e) => setFilter((f) => ({ ...f, venture: e.target.value }))}>
          <option value="">All Ventures</option>
          {Object.entries(VENTURES).map(([k, v]) => <option key={k} value={k}>{v.emoji} {v.label}</option>)}
        </select>
        <select style={sel} value={filter.status} onChange={(e) => setFilter((f) => ({ ...f, status: e.target.value }))}>
          <option value="">All Statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <button
          onClick={() => setShowForm(!showForm)}
          style={{ marginLeft: "auto", background: "#a6e3a1", color: "#1e1e2e", border: "none", borderRadius: 8, padding: "7px 16px", fontWeight: 700, cursor: "pointer" }}
        >
          + Add Lead
        </button>
      </div>

      {showForm && (
        <Card title="New Lead">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {[["name", "Name *"], ["contact", "Contact (email/phone)"], ["source", "Source"]].map(([k, p]) => (
              <input key={k} style={inp} placeholder={p} value={form[k]} onChange={(e) => setForm((f) => ({ ...f, [k]: e.target.value }))} />
            ))}
            <select style={sel} value={form.venture} onChange={(e) => setForm((f) => ({ ...f, venture: e.target.value }))}>
              {Object.entries(VENTURES).map(([k, v]) => <option key={k} value={k}>{v.emoji} {v.label}</option>)}
            </select>
            <input style={inp} type="number" placeholder="Value ($)" value={form.value} onChange={(e) => setForm((f) => ({ ...f, value: e.target.value }))} />
            <textarea
              style={{ ...inp, gridColumn: "1/-1", minHeight: 60, resize: "vertical" }}
              placeholder="Notes"
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
            />
          </div>
          <button onClick={createLead} style={{ marginTop: 10, background: "#89b4fa", color: "#1e1e2e", border: "none", borderRadius: 8, padding: "8px 20px", fontWeight: 700, cursor: "pointer" }}>
            Save Lead
          </button>
        </Card>
      )}

      {leads.map((lead) => (
        <div key={lead.id} style={{ background: "#1e1e2e", borderRadius: 10, padding: 16, marginBottom: 10 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <span style={{ fontWeight: 700, color: "#cdd6f4", fontSize: 15 }}>{lead.name}</span>
              {lead.contact && <span style={{ marginLeft: 8, color: "#6c7086", fontSize: 13 }}>{lead.contact}</span>}
              <div style={{ marginTop: 4, display: "flex", gap: 6 }}>
                <Badge text={`${VENTURES[lead.venture]?.emoji} ${lead.venture}`} color={VENTURES[lead.venture]?.color || "#89b4fa"} />
                <Badge
                  text={lead.status}
                  color={lead.status === "won" ? "#a6e3a1" : lead.status === "lost" ? "#f38ba8" : "#89b4fa"}
                />
                {lead.value > 0 && <Badge text={`$${lead.value.toLocaleString()}`} color="#f9e2af" />}
              </div>
              {lead.notes && <p style={{ color: "#6c7086", fontSize: 13, margin: "6px 0 0" }}>{lead.notes}</p>}
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "flex-end" }}>
              <select
                style={{ ...sel, fontSize: 12 }}
                value={lead.status}
                onChange={(e) => updateStatus(lead.id, e.target.value)}
              >
                {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <button
                onClick={() => generateDraft(lead)}
                style={{ background: "#313244", color: "#cdd6f4", border: "none", borderRadius: 6, padding: "5px 12px", fontSize: 12, cursor: "pointer" }}
              >
                ✍ Draft
              </button>
            </div>
          </div>
          {draft.lead_id === lead.id && (
            <div style={{ marginTop: 10, background: "#313244", borderRadius: 8, padding: 12 }}>
              {draft.loading ? (
                <span style={{ color: "#6c7086", fontSize: 13 }}>Drafting...</span>
              ) : (
                <pre style={{ color: "#cdd6f4", fontSize: 13, whiteSpace: "pre-wrap", margin: 0 }}>{draft.text}</pre>
              )}
            </div>
          )}
        </div>
      ))}
      {leads.length === 0 && <p style={{ color: "#6c7086" }}>No leads found. Add your first one above.</p>}
    </div>
  );
}

// ── Tasks Tab ─────────────────────────────────────────────────────────────────

function TasksTab() {
  const [tasks, setTasks] = useState([]);
  const [accountability, setAccountability] = useState(null);
  const [form, setForm] = useState({ title: "", description: "", venture: "", priority: "medium" });
  const [showForm, setShowForm] = useState(false);

  const loadTasks = async () => setTasks(await apiFetch("/tasks"));
  const loadNudge = async () => setAccountability(await apiFetch("/tasks/accountability"));

  useEffect(() => { loadTasks(); loadNudge(); }, []);

  const createTask = async () => {
    await apiFetch("/tasks", { method: "POST", body: JSON.stringify(form) });
    setForm({ title: "", description: "", venture: "", priority: "medium" });
    setShowForm(false);
    loadTasks();
  };

  const complete = async (id) => {
    await apiFetch(`/tasks/${id}/complete`, { method: "POST" });
    loadTasks();
    loadNudge();
  };

  const inp = { background: "#1e1e2e", border: "1px solid #45475a", borderRadius: 6, color: "#cdd6f4", padding: "6px 10px", fontSize: 13, width: "100%" };
  const sel = { ...inp, width: "auto" };

  return (
    <div>
      {accountability && (
        <Card title="Accountability Nudge">
          <div style={{ background: "#313244", borderRadius: 8, padding: 12, marginBottom: 10 }}>
            <p style={{ color: "#cdd6f4", fontSize: 14, margin: 0, lineHeight: 1.6 }}>{accountability.nudge}</p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 4 }}>
            {Object.entries(accountability.stats).map(([k, v]) => (
              <div key={k} style={{ textAlign: "center", padding: 8 }}>
                <div style={{ fontSize: 20, fontWeight: 800, color: "#cdd6f4" }}>{v}</div>
                <div style={{ fontSize: 10, color: "#6c7086" }}>{k.replace(/_/g, " ")}</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <button
          onClick={() => setShowForm(!showForm)}
          style={{ background: "#a6e3a1", color: "#1e1e2e", border: "none", borderRadius: 8, padding: "7px 16px", fontWeight: 700, cursor: "pointer" }}
        >
          + Add Task
        </button>
      </div>

      {showForm && (
        <Card title="New Task">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <input style={inp} placeholder="Title *" value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} />
            <select style={sel} value={form.venture} onChange={(e) => setForm((f) => ({ ...f, venture: e.target.value }))}>
              <option value="">Any venture</option>
              {Object.entries(VENTURES).map(([k, v]) => <option key={k} value={k}>{v.emoji} {v.label}</option>)}
            </select>
            <select style={sel} value={form.priority} onChange={(e) => setForm((f) => ({ ...f, priority: e.target.value }))}>
              {["low", "medium", "high"].map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
            <textarea style={{ ...inp, gridColumn: "1/-1", minHeight: 50, resize: "vertical" }} placeholder="Description" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
          </div>
          <button onClick={createTask} style={{ marginTop: 10, background: "#89b4fa", color: "#1e1e2e", border: "none", borderRadius: 8, padding: "8px 20px", fontWeight: 700, cursor: "pointer" }}>
            Save Task
          </button>
        </Card>
      )}

      {tasks.map((t) => (
        <div key={t.id} style={{ background: "#1e1e2e", borderRadius: 10, padding: 14, marginBottom: 8, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <span style={{ fontWeight: 600, color: "#cdd6f4" }}>{t.title}</span>
            <div style={{ marginTop: 4, display: "flex", gap: 6 }}>
              {t.venture && <Badge text={`${VENTURES[t.venture]?.emoji} ${t.venture}`} color={VENTURES[t.venture]?.color || "#89b4fa"} />}
              <Badge text={t.priority} color={t.priority === "high" ? "#f38ba8" : t.priority === "medium" ? "#f9e2af" : "#a6e3a1"} />
              {t.due_date && <span style={{ fontSize: 12, color: "#6c7086" }}>Due: {new Date(t.due_date).toLocaleDateString()}</span>}
            </div>
            {t.description && <p style={{ color: "#6c7086", fontSize: 13, margin: "4px 0 0" }}>{t.description}</p>}
          </div>
          <button
            onClick={() => complete(t.id)}
            style={{ background: "#a6e3a1", color: "#1e1e2e", border: "none", borderRadius: 8, padding: "6px 14px", fontWeight: 700, cursor: "pointer", whiteSpace: "nowrap" }}
          >
            ✓ Done
          </button>
        </div>
      ))}
      {tasks.length === 0 && <p style={{ color: "#6c7086" }}>No pending tasks. You're crushing it.</p>}
    </div>
  );
}

// ── Voice Tab ─────────────────────────────────────────────────────────────────

function VoiceTab() {
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState({ category: "email", content: "" });
  const [status, setStatus] = useState("");

  const load = async () => setProfile(await apiFetch("/voice/profile"));
  useEffect(() => { load(); }, []);

  const ingest = async () => {
    if (!form.content.trim()) return;
    setStatus("Ingesting...");
    try {
      const r = await apiFetch("/voice/ingest", { method: "POST", body: JSON.stringify(form) });
      setStatus(`✓ Ingested! Total: ${r.total_samples} samples`);
      setForm((f) => ({ ...f, content: "" }));
      load();
    } catch (e) {
      setStatus(`Error: ${e.message}`);
    }
  };

  const conf = profile ? Math.round(profile.confidence * 100) : 0;
  const confColor = conf >= 80 ? "#a6e3a1" : conf >= 40 ? "#f9e2af" : "#f38ba8";

  const sel = { background: "#1e1e2e", border: "1px solid #45475a", borderRadius: 6, color: "#cdd6f4", padding: "6px 10px", fontSize: 13 };

  return (
    <div>
      <Card title="Voice Profile">
        {profile ? (
          <>
            <div style={{ display: "flex", gap: 24, marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: 32, fontWeight: 800, color: confColor }}>{conf}%</div>
                <div style={{ fontSize: 12, color: "#6c7086" }}>confidence</div>
              </div>
              <div>
                <div style={{ fontSize: 32, fontWeight: 800, color: "#cdd6f4" }}>{profile.sample_count}</div>
                <div style={{ fontSize: 12, color: "#6c7086" }}>total samples</div>
              </div>
              <div>
                {Object.entries(profile.categories).map(([cat, n]) => (
                  <div key={cat} style={{ fontSize: 13, color: "#6c7086" }}>
                    <span style={{ color: "#cdd6f4" }}>{cat}</span>: {n}
                  </div>
                ))}
              </div>
            </div>
            {profile.sample_count > 0 && (
              <pre style={{ background: "#313244", borderRadius: 8, padding: 12, fontSize: 12, color: "#cdd6f4", whiteSpace: "pre-wrap", maxHeight: 200, overflowY: "auto", margin: 0 }}>
                {profile.style_summary}
              </pre>
            )}
          </>
        ) : (
          <p style={{ color: "#6c7086" }}>Loading...</p>
        )}
      </Card>

      <Card title="Feed a Sample">
        <p style={{ color: "#6c7086", fontSize: 13, marginTop: 0 }}>
          Paste real examples of how you communicate — emails, texts, social posts, call notes. The more you feed it, the more it sounds like you.
        </p>
        <select
          style={{ ...sel, marginBottom: 10 }}
          value={form.category}
          onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
        >
          {["email", "phone", "text", "social", "sales"].map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <textarea
          style={{ ...sel, width: "100%", minHeight: 120, display: "block", resize: "vertical", marginBottom: 10 }}
          placeholder="Paste your sample here..."
          value={form.content}
          onChange={(e) => setForm((f) => ({ ...f, content: e.target.value }))}
        />
        <button
          onClick={ingest}
          style={{ background: "#89b4fa", color: "#1e1e2e", border: "none", borderRadius: 8, padding: "8px 20px", fontWeight: 700, cursor: "pointer" }}
        >
          Ingest Sample
        </button>
        {status && <span style={{ marginLeft: 12, fontSize: 13, color: status.startsWith("✓") ? "#a6e3a1" : "#f38ba8" }}>{status}</span>}
      </Card>
    </div>
  );
}

// ── Draft Tab ─────────────────────────────────────────────────────────────────

function DraftTab() {
  const [form, setForm] = useState({ recipient_name: "", venture: "hatch", channel: "email", context: "", tone: "friendly" });
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    setDraft("");
    try {
      const params = new URLSearchParams(form);
      const data = await apiFetch(`/draft?${params}`);
      setDraft(data.draft);
    } catch (e) {
      setDraft(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const inp = { background: "#1e1e2e", border: "1px solid #45475a", borderRadius: 6, color: "#cdd6f4", padding: "8px 12px", fontSize: 13, width: "100%" };
  const sel = { ...inp, width: "auto" };

  return (
    <div>
      <Card title="AI Outreach Generator">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <input style={inp} placeholder="Recipient name *" value={form.recipient_name} onChange={(e) => setForm((f) => ({ ...f, recipient_name: e.target.value }))} />
          <select style={sel} value={form.venture} onChange={(e) => setForm((f) => ({ ...f, venture: e.target.value }))}>
            {Object.entries(VENTURES).map(([k, v]) => <option key={k} value={k}>{v.emoji} {v.label}</option>)}
          </select>
          <select style={sel} value={form.channel} onChange={(e) => setForm((f) => ({ ...f, channel: e.target.value }))}>
            {["email", "text", "social", "phone"].map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <select style={sel} value={form.tone} onChange={(e) => setForm((f) => ({ ...f, tone: e.target.value }))}>
            {["friendly", "professional", "urgent", "casual", "warm"].map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <textarea
            style={{ ...inp, gridColumn: "1/-1", minHeight: 80, resize: "vertical" }}
            placeholder="Context: what's this outreach about?"
            value={form.context}
            onChange={(e) => setForm((f) => ({ ...f, context: e.target.value }))}
          />
        </div>
        <button
          onClick={generate}
          disabled={loading || !form.recipient_name || !form.context}
          style={{ marginTop: 12, background: loading ? "#45475a" : "#89b4fa", color: "#1e1e2e", border: "none", borderRadius: 8, padding: "10px 24px", fontWeight: 700, cursor: loading ? "default" : "pointer", fontSize: 14 }}
        >
          {loading ? "Generating..." : "✍ Generate Draft"}
        </button>
      </Card>

      {draft && (
        <Card title="Generated Draft" action={
          <button onClick={() => navigator.clipboard.writeText(draft)} style={{ background: "#313244", color: "#cdd6f4", border: "none", borderRadius: 6, padding: "4px 12px", fontSize: 12, cursor: "pointer" }}>
            Copy
          </button>
        }>
          <pre style={{ color: "#cdd6f4", fontSize: 14, whiteSpace: "pre-wrap", lineHeight: 1.6, margin: 0 }}>{draft}</pre>
        </Card>
      )}
    </div>
  );
}

// ── Inbox Tab (SMS auto-responder) ────────────────────────────────────────────

const TIERS = {
  business: { label: "Business", color: "#89b4fa", desc: "Drafts in your voice; routine replies can auto-send" },
  personal: { label: "Personal", color: "#f5c2e7", desc: "Never auto-answered as you — honest away-reply + reminder" },
  unknown: { label: "Unknown", color: "#6c7086", desc: "Logged + flagged for you; no auto-reply" },
};

function InboxTab() {
  const [status, setStatus] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [pending, setPending] = useState([]);
  const [form, setForm] = useState({ name: "", phone: "", tier: "business", venture: "hatch", auto_send: false, away_mode: false, away_reply: "" });
  const [showForm, setShowForm] = useState(false);
  const [edits, setEdits] = useState({});

  const load = async () => {
    setStatus(await apiFetch("/sms/status"));
    setContacts(await apiFetch("/sms/contacts"));
    setPending(await apiFetch("/sms/pending"));
  };
  useEffect(() => { load(); }, []);

  const createContact = async () => {
    if (!form.phone.trim()) return;
    await apiFetch("/sms/contacts", { method: "POST", body: JSON.stringify(form) });
    setForm({ name: "", phone: "", tier: "business", venture: "hatch", auto_send: false, away_mode: false, away_reply: "" });
    setShowForm(false);
    load();
  };

  const setTier = async (id, tier) => {
    await apiFetch(`/sms/contacts/${id}`, { method: "PATCH", body: JSON.stringify({ tier }) });
    load();
  };
  const toggle = async (id, field, val) => {
    await apiFetch(`/sms/contacts/${id}`, { method: "PATCH", body: JSON.stringify({ [field]: val }) });
    load();
  };

  const approve = async (p) => {
    await apiFetch(`/sms/pending/${p.id}/approve`, { method: "POST", body: JSON.stringify({ edited_text: edits[p.id] ?? p.draft }) });
    load();
  };
  const reject = async (p) => {
    await apiFetch(`/sms/pending/${p.id}/reject`, { method: "POST" });
    load();
  };

  const inp = { background: "#1e1e2e", border: "1px solid #45475a", borderRadius: 6, color: "#cdd6f4", padding: "6px 10px", fontSize: 13, width: "100%" };
  const sel = { ...inp, width: "auto" };

  return (
    <div>
      {/* Status / safety banner */}
      {status && (
        <div style={{ background: "#1e1e2e", borderRadius: 12, padding: "12px 16px", marginBottom: 16, borderLeft: `3px solid ${status.configured ? "#a6e3a1" : "#f9e2af"}` }}>
          <div style={{ fontSize: 13, color: "#cdd6f4" }}>
            SMS gateway: <strong style={{ color: status.configured ? "#a6e3a1" : "#f9e2af" }}>{status.configured ? "connected" : "not configured"}</strong>
            {"  ·  "}
            Auto-send: <strong style={{ color: status.auto_send_enabled ? "#a6e3a1" : "#6c7086" }}>{status.auto_send_enabled ? "armed" : "off"}</strong>
          </div>
          <div style={{ fontSize: 12, color: "#6c7086", marginTop: 4 }}>
            🔒 Personal contacts are never answered in your voice — they get an honest away-reply (if enabled) and a reminder pings you.
          </div>
        </div>
      )}

      {/* Approval queue */}
      <Card title={`Approval Queue${pending.length ? ` (${pending.length})` : ""}`}>
        {pending.length === 0 ? (
          <p style={{ color: "#6c7086", fontSize: 13, margin: 0 }}>Nothing waiting. Drafts that need your eyes land here.</p>
        ) : (
          pending.map((p) => (
            <div key={p.id} style={{ background: "#313244", borderRadius: 8, padding: 12, marginBottom: 10 }}>
              <div style={{ fontSize: 12, color: "#6c7086", marginBottom: 6 }}>
                To <strong style={{ color: "#cdd6f4" }}>{p.contact_name || p.phone}</strong>
                {p.intent && <> · <em>{p.intent}</em></>}
              </div>
              <textarea
                style={{ ...inp, minHeight: 60, resize: "vertical", marginBottom: 8 }}
                value={edits[p.id] ?? p.draft}
                onChange={(e) => setEdits((s) => ({ ...s, [p.id]: e.target.value }))}
              />
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={() => approve(p)} style={{ background: "#a6e3a1", color: "#1e1e2e", border: "none", borderRadius: 6, padding: "6px 16px", fontWeight: 700, cursor: "pointer" }}>
                  ✓ Approve &amp; Send
                </button>
                <button onClick={() => reject(p)} style={{ background: "#45475a", color: "#cdd6f4", border: "none", borderRadius: 6, padding: "6px 16px", cursor: "pointer" }}>
                  Reject
                </button>
              </div>
            </div>
          ))
        )}
      </Card>

      {/* Contacts */}
      <Card
        title="Contacts"
        action={
          <button onClick={() => setShowForm(!showForm)} style={{ background: "#a6e3a1", color: "#1e1e2e", border: "none", borderRadius: 8, padding: "6px 14px", fontWeight: 700, cursor: "pointer" }}>
            + Add
          </button>
        }
      >
        {showForm && (
          <div style={{ background: "#313244", borderRadius: 8, padding: 12, marginBottom: 12 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <input style={inp} placeholder="Name" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
              <input style={inp} placeholder="Phone (+1555...)" value={form.phone} onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} />
              <select style={sel} value={form.tier} onChange={(e) => setForm((f) => ({ ...f, tier: e.target.value }))}>
                {Object.entries(TIERS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
              </select>
              <select style={sel} value={form.venture} onChange={(e) => setForm((f) => ({ ...f, venture: e.target.value }))}>
                {Object.entries(VENTURES).map(([k, v]) => <option key={k} value={k}>{v.emoji} {v.label}</option>)}
              </select>
            </div>
            <div style={{ fontSize: 12, color: "#6c7086", margin: "8px 0" }}>{TIERS[form.tier].desc}</div>
            <div style={{ display: "flex", gap: 16, marginBottom: 8 }}>
              {form.tier === "business" && (
                <label style={{ fontSize: 13, color: "#cdd6f4", display: "flex", gap: 6, alignItems: "center" }}>
                  <input type="checkbox" checked={form.auto_send} onChange={(e) => setForm((f) => ({ ...f, auto_send: e.target.checked }))} />
                  Auto-send routine replies
                </label>
              )}
              {form.tier === "personal" && (
                <label style={{ fontSize: 13, color: "#cdd6f4", display: "flex", gap: 6, alignItems: "center" }}>
                  <input type="checkbox" checked={form.away_mode} onChange={(e) => setForm((f) => ({ ...f, away_mode: e.target.checked }))} />
                  Send honest away-reply
                </label>
              )}
            </div>
            <button onClick={createContact} style={{ background: "#89b4fa", color: "#1e1e2e", border: "none", borderRadius: 8, padding: "7px 18px", fontWeight: 700, cursor: "pointer" }}>
              Save Contact
            </button>
          </div>
        )}

        {contacts.length === 0 ? (
          <p style={{ color: "#6c7086", fontSize: 13, margin: 0 }}>No contacts yet. Add people so EricBot knows how to route their texts.</p>
        ) : (
          contacts.map((c) => (
            <div key={c.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid #313244" }}>
              <div>
                <span style={{ fontWeight: 600, color: "#cdd6f4" }}>{c.name || c.phone}</span>
                <span style={{ marginLeft: 8, fontSize: 12, color: "#6c7086" }}>{c.phone}</span>
                <div style={{ marginTop: 4, display: "flex", gap: 6, alignItems: "center" }}>
                  <Badge text={TIERS[c.tier]?.label || c.tier} color={TIERS[c.tier]?.color || "#6c7086"} />
                  {c.tier === "business" && c.auto_send ? <Badge text="auto-send" color="#a6e3a1" /> : null}
                  {c.tier === "personal" && c.away_mode ? <Badge text="away-reply" color="#f5c2e7" /> : null}
                </div>
              </div>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                {c.tier === "business" && (
                  <button onClick={() => toggle(c.id, "auto_send", !c.auto_send)} style={{ background: "#313244", color: "#cdd6f4", border: "none", borderRadius: 6, padding: "4px 10px", fontSize: 12, cursor: "pointer" }}>
                    {c.auto_send ? "Disable auto-send" : "Enable auto-send"}
                  </button>
                )}
                {c.tier === "personal" && (
                  <button onClick={() => toggle(c.id, "away_mode", !c.away_mode)} style={{ background: "#313244", color: "#cdd6f4", border: "none", borderRadius: 6, padding: "4px 10px", fontSize: 12, cursor: "pointer" }}>
                    {c.away_mode ? "Disable away-reply" : "Enable away-reply"}
                  </button>
                )}
                <select style={{ ...sel, fontSize: 12 }} value={c.tier} onChange={(e) => setTier(c.id, e.target.value)}>
                  {Object.keys(TIERS).map((t) => <option key={t} value={t}>{TIERS[t].label}</option>)}
                </select>
              </div>
            </div>
          ))
        )}
      </Card>
    </div>
  );
}

// ── App Shell ─────────────────────────────────────────────────────────────────

const TABS = [
  { id: "dashboard", label: "Dashboard", emoji: "📊" },
  { id: "chat", label: "Chat", emoji: "💬" },
  { id: "leads", label: "Leads", emoji: "🎯" },
  { id: "tasks", label: "Tasks", emoji: "✅" },
  { id: "inbox", label: "Inbox", emoji: "📱" },
  { id: "voice", label: "Voice", emoji: "🎤" },
  { id: "draft", label: "Draft", emoji: "✍" },
];

export default function EricBot() {
  const [tab, setTab] = useState("dashboard");

  const tabContent = {
    dashboard: <DashboardTab />,
    chat: <ChatTab />,
    leads: <LeadsTab />,
    tasks: <TasksTab />,
    inbox: <InboxTab />,
    voice: <VoiceTab />,
    draft: <DraftTab />,
  };

  return (
    <div style={{ minHeight: "100vh", background: "#181825", color: "#cdd6f4", fontFamily: "'Inter', system-ui, sans-serif" }}>
      {/* Header */}
      <div style={{ background: "#1e1e2e", borderBottom: "1px solid #313244", padding: "14px 24px", display: "flex", alignItems: "center", gap: 12 }}>
        <span style={{ fontSize: 22 }}>🤖</span>
        <div>
          <div style={{ fontWeight: 800, fontSize: 18, color: "#cdd6f4" }}>EricBot</div>
          <div style={{ fontSize: 12, color: "#6c7086" }}>AI Clone & Business Development Engine</div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          {Object.entries(VENTURES).map(([k, v]) => (
            <span key={k} style={{ fontSize: 12, color: v.color, background: v.color + "22", padding: "2px 8px", borderRadius: 4 }}>
              {v.emoji} {v.label}
            </span>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ background: "#1e1e2e", borderBottom: "1px solid #313244", display: "flex", padding: "0 24px" }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              background: "none",
              border: "none",
              color: tab === t.id ? "#89b4fa" : "#6c7086",
              borderBottom: tab === t.id ? "2px solid #89b4fa" : "2px solid transparent",
              padding: "12px 16px",
              fontSize: 14,
              fontWeight: tab === t.id ? 700 : 400,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            {t.emoji} {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ maxWidth: 900, margin: "0 auto", padding: "24px 24px" }}>
        {tabContent[tab]}
      </div>
    </div>
  );
}
