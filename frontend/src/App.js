import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const SLASH_COMMANDS = [
  { cmd: '/level', desc: 'Open level-up stat allocator' },
];

const STAT_FIELDS = [
  { key: 'vgr', label: 'VGR', icon: '/icons/icon-vigor.png' },
  { key: 'end', label: 'END', icon: '/icons/icon-endurance.png' },
  { key: 'vit', label: 'VIT', icon: '/icons/icon-vitality.png' },
  { key: 'atn', label: 'ATN', icon: '/icons/icon-attunement.png' },
  { key: 'str', label: 'STR', icon: '/icons/icon-strength.png' },
  { key: 'dex', label: 'DEX', icon: '/icons/icon-dexterity.png' },
  { key: 'adp', label: 'ADP', icon: '/icons/icon-adaptability.png' },
  { key: 'int', label: 'INT', icon: '/icons/icon-intelligence.png' },
  { key: 'fth', label: 'FTH', icon: '/icons/icon-faith.png' },
];

// Maps the short frontend stat keys to the long names the backend PlayerStats model expects
const STAT_KEY_MAP = {
  vgr: 'vigor',
  end: 'endurance',
  vit: 'vitality',
  atn: 'attunement',
  str: 'strength',
  dex: 'dexterity',
  adp: 'adaptability',
  int: 'intelligence',
  fth: 'faith',
  main_hand: 'right_weapon_1',
  off_hand: 'right_weapon_2',
};

const DEFAULT_STATS = {
  soul_level: '',
  soul_memory: '',
  vgr: '', end: '', vit: '', atn: '',
  str: '', dex: '', adp: '', int: '', fth: '',
  main_hand: '',
  off_hand: '',
  build_type: '',
  current_area: '',
  last_boss_defeated: '',
  notes: '',
};

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [stats, setStats] = useState(() => {
    try {
      const saved = localStorage.getItem('ds2_player_stats');
      return saved ? JSON.parse(saved) : DEFAULT_STATS;
    } catch {
      return DEFAULT_STATS;
    }
  });
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [levelModalOpen, setLevelModalOpen] = useState(false);
  const [levelDraft, setLevelDraft] = useState({});
  const [levelStep, setLevelStep] = useState('count'); // 'count' | 'distribute'
  const [levelCount, setLevelCount] = useState('');

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    localStorage.setItem('ds2_player_stats', JSON.stringify(stats));
  }, [stats]);

  const handleStatChange = (key, value) => {
    setStats(prev => ({ ...prev, [key]: value }));
  };

  const buildPlayerStats = () => {
    const result = {};
    Object.entries(stats).forEach(([key, val]) => {
      if (val !== '' && val !== null && val !== undefined) {
        const mappedKey = STAT_KEY_MAP[key] ?? key;
        result[mappedKey] = val;
      }
    });
    return result;
  };

  const handleCloseLevelModal = () => {
    setLevelModalOpen(false);
    setLevelStep('count');
    setLevelCount('');
  };

  const handleConfirmLevel = () => {
    const changes = [];
    const newStats = { ...stats };

    STAT_FIELDS.forEach(({ key, label }) => {
      const oldVal = stats[key];
      const newVal = levelDraft[key];
      if (newVal !== '' && newVal !== oldVal) {
        changes.push(`${label} ${oldVal || '—'}→${newVal}`);
        newStats[key] = newVal;
      }
    });

    if (changes.length > 0) {
      const gained = STAT_FIELDS.reduce((sum, { key }) => {
        const o = parseInt(stats[key]) || 0;
        const n = parseInt(levelDraft[key]) || 0;
        return sum + Math.max(0, n - o);
      }, 0);
      const oldSL = parseInt(stats.soul_level) || 0;
      if (gained > 0) {
        newStats.soul_level = String(oldSL + gained);
      }
      setStats(newStats);
      const levelLine = gained > 0 ? `Level: ${oldSL}→${oldSL + gained}` : '';
      const statsLine = `Stats: ${changes.join(', ')}`;
      const content = levelLine ? `${levelLine}\n\n${statsLine}` : statsLine;
      setMessages(prev => [...prev, { role: 'assistant', content }]);
    }

    handleCloseLevelModal();
  };

  const handleClearStats = () => {
    setStats(DEFAULT_STATS);
    localStorage.removeItem('ds2_player_stats');
  };

  const handleClearChat = () => setMessages([]);

  const handleCheckSoulMemory = async () => {
    const sm = stats.soul_memory;
    const userMsg = { role: 'user', content: 'What is my Soul Memory tier?' };
    setMessages(prev => [...prev, userMsg]);
    if (!sm) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Please fill in your **Soul Mem** field on the left to check your tier.' }]);
      return;
    }
    setLoading(true);

    try {
      const res = await axios.post('http://localhost:8001/soul-memory', {
        soul_memory: parseInt(sm, 10),
      });
      const d = res.data;
      const tierRange = d.tier_range.replace(' - ', '–');
      const matchRange = d.matchmaking_range.replace(' - ', '–');
      const nextTierPart = d.souls_to_next_tier > 0
        ? ` Souls to next tier: ${d.souls_to_next_tier.toLocaleString()}.`
        : ' Max tier reached.';
      const assistantMsg = {
        role: 'assistant',
        content: `Your Soul Memory is ${d.soul_memory.toLocaleString()} — you're in Tier ${d.tier} (Range: ${tierRange}). You can match with players from ${matchRange} Soul Memory.${nextTierPart}`,
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'Error: ' + (err.response?.data?.detail ?? err.message),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async (overrideQuestion) => {
    const question = (overrideQuestion ?? input).trim();
    if (!question || loading) return;

    // /level — open the level-up modal
    if (question === '/level') {
      setLevelDraft({ ...stats });
      setLevelStep('count');
      setLevelCount('');
      setLevelModalOpen(true);
      setInput('');
      return;
    }

    const userMsg = { role: 'user', content: question };
    // Capture index before the user message is added (+1 for user msg, that's where assistant goes)
    const assistantIdx = messages.length + 1;
    const chatHistory = messages.slice(-10);

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    let assistantAdded = false;
    let accumulated = '';
    let lineBuffer = '';

    try {
      const response = await fetch('http://localhost:8001/ask-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          player_stats: buildPlayerStats(),
          chat_history: chatHistory,
        }),
      });

      if (!response.ok) throw new Error(`HTTP error ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Buffer partial lines so SSE events split across reads are handled correctly
        lineBuffer += decoder.decode(value, { stream: true });
        const lines = lineBuffer.split('\n');
        lineBuffer = lines.pop(); // keep incomplete trailing line

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const chunk = JSON.parse(line.slice(6));
            accumulated += chunk;
            const snapshot = accumulated; // capture current value for closures
            if (!assistantAdded) {
              assistantAdded = true;
              setLoading(false);
              setMessages(prev => [...prev, { role: 'assistant', content: snapshot }]);
            } else {
              setMessages(prev => {
                const updated = [...prev];
                updated[assistantIdx] = { role: 'assistant', content: snapshot };
                return updated;
              });
            }
          }
        }
      }
    } catch (err) {
      const errMsg = { role: 'assistant', content: 'Error: ' + err.message };
      if (assistantAdded) {
        setMessages(prev => {
          const updated = [...prev];
          updated[assistantIdx] = errMsg;
          return updated;
        });
      } else {
        setMessages(prev => [...prev, errMsg]);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-screen bg-neutral-900 text-neutral-100 overflow-hidden" style={{ minHeight: '620px' }}>

      {/* Sidebar */}
      <aside
        className={`flex flex-col h-full bg-neutral-800 transition-all duration-300 overflow-hidden border-r border-white/[0.06] ${
          sidebarOpen ? 'w-80 min-w-[20rem]' : 'w-0 min-w-0'
        }`}
      >
        <div className="relative h-full min-w-[20rem]">

          {/* Title — pinned top */}
          <div className="absolute top-0 left-0 right-0 h-[72px] flex items-end justify-center pb-3 pointer-events-none z-10">
            <div className="text-yellow-500 text-2xl leading-tight" style={{ fontFamily: 'OptimusPrinceps, serif' }}>Player Stats</div>
          </div>

          {/* Grid + button — flow from just below title, space absorbs at bottom */}
          <div className="absolute top-[72px] bottom-0 left-0 right-0 flex flex-col overflow-y-auto px-7">
          <div
            className="pt-3 pb-2 grid gap-x-3 gap-y-2 w-full flex-none"
            style={{ gridTemplateColumns: '6rem 1fr', gridTemplateRows: 'repeat(9, auto)', alignItems: 'stretch' }}
          >

            {/* Left: VGR → FTH, one per row */}
            {STAT_FIELDS.map(({ key, label, icon }, i) => (
              <div key={key} className="flex flex-col gap-1.5" style={{ gridColumn: 1, gridRow: i + 1 }}>
                <label className="flex items-center gap-1.5 text-xs text-[#b8b8b8] uppercase tracking-wider leading-none">
                  <img src={icon} alt={label} className="w-5 h-5 object-contain" />
                  {label}
                </label>
                <input
                  type="number"
                  value={stats[key]}
                  onChange={e => handleStatChange(key, e.target.value)}
                  className="bg-neutral-700/70 rounded-md px-2 py-1.5 text-xs text-neutral-100 focus:outline-none focus:ring-1 focus:ring-inset focus:ring-yellow-600/60 w-full"
                  placeholder="—"
                />
              </div>
            ))}

            {/* Right: rows 1–7, aligned with VGR–ADP */}
            {[
              { key: 'soul_level', label: 'Level', type: 'number' },
              { key: 'soul_memory', label: 'Soul Memory', type: 'number' },
              { key: 'main_hand', label: 'Right Weapon 1', type: 'text' },
              { key: 'off_hand', label: 'Right Weapon 2', type: 'text' },
              { key: 'build_type', label: 'Build Type', type: 'text' },
              { key: 'current_area', label: 'Current Area', type: 'text' },
              { key: 'last_boss_defeated', label: 'Last Boss', type: 'text' },
            ].map(({ key, label, type }, i) => (
              <div key={key} className="flex flex-col gap-1.5" style={{ gridColumn: 2, gridRow: i + 1 }}>
                <label className="flex items-center gap-1.5 text-xs text-[#b8b8b8] uppercase tracking-wider leading-none">
                  {label}
                  <span className="w-5 h-5 shrink-0 inline-block" />
                </label>
                <input
                  type={type}
                  value={stats[key]}
                  onChange={e => handleStatChange(key, e.target.value)}
                  className="bg-neutral-700/70 rounded-md px-2 py-1.5 text-xs text-neutral-100 focus:outline-none focus:ring-1 focus:ring-inset focus:ring-yellow-600/60 w-full"
                  placeholder="—"
                />
              </div>
            ))}

            {/* Notes spans rows 8–9 (aligns with INT + FTH), textarea fills the height */}
            <div className="flex flex-col gap-1.5 overflow-hidden" style={{ gridColumn: 2, gridRow: '8 / span 2', alignSelf: 'stretch', marginTop: 0 }}>
              <label className="flex items-center gap-1.5 text-xs text-[#b8b8b8] uppercase tracking-wider leading-none">
                Notes
                <span className="w-5 h-5 shrink-0 inline-block" />
              </label>
              <textarea
                value={stats.notes}
                onChange={e => handleStatChange('notes', e.target.value)}
                className="flex-1 bg-neutral-700/70 rounded-md px-2 py-1.5 text-xs text-neutral-100 focus:outline-none focus:ring-1 focus:ring-inset focus:ring-yellow-600/60 w-full resize-none"
                placeholder="—"
              />
            </div>

          </div>{/* end grid */}

          {/* Clear Stats — immediately below grid */}
          <div className="pt-7 pb-5 flex-none">
            <button
              onClick={handleClearStats}
              className="w-full bg-yellow-600 hover:bg-yellow-500 active:bg-yellow-700 text-neutral-900 font-semibold text-xs rounded-md py-2 transition-colors"
            >
              Clear Stats
            </button>
          </div>

          </div>{/* end flex-col content zone */}

        </div>
      </aside>

      {/* Main area */}
      <div className="flex flex-col flex-1 min-w-0">

        {/* Header */}
        <header className="flex items-center gap-3 px-5 h-[72px] bg-neutral-800 shrink-0 border-b border-white/[0.06]">
          <button
            onClick={() => setSidebarOpen(o => !o)}
            className="text-yellow-500 hover:text-yellow-400 transition-colors p-1 rounded-md hover:bg-neutral-700/60"
            title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {sidebarOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              )}
            </svg>
          </button>

          <h1 className="flex items-center gap-2 text-yellow-500 text-2xl leading-tight tracking-wide" style={{ fontFamily: 'OptimusPrinceps, serif' }}>
            Scholar
            <span className="text-neutral-500 text-xl">·</span>
            <span className="text-neutral-400 text-xl">Dark Souls II</span>
          </h1>

          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              className="ml-auto text-neutral-400 hover:text-neutral-200 text-xs bg-neutral-700/50 hover:bg-neutral-700 rounded-full px-3 py-1.5 transition-colors"
            >
              Clear Chat
            </button>
          )}
        </header>

        {/* Messages */}
        <main className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3">
          {messages.length === 0 && !loading && (
            <div className="relative flex flex-1 flex-col items-center justify-center gap-8 py-8">

              {/* Info tooltip — top-right of home screen only */}
              <div className="absolute top-0 right-0 group">
                <button className="w-6 h-6 flex items-center justify-center rounded-full bg-neutral-700/50 text-neutral-500 text-xs hover:bg-neutral-700 hover:text-neutral-300 transition-colors">
                  ?
                </button>
                <div className="pointer-events-none absolute right-0 top-8 w-64 bg-neutral-800 rounded-xl px-3 py-2.5 text-xs text-neutral-300 leading-relaxed opacity-0 group-hover:opacity-100 transition-opacity z-10 shadow-xl shadow-black/60">
                  Ask about items, bosses, builds, and mechanics. Answers are sourced directly from the Fextralife wiki. Fill in your stats on the left for personalized advice.
                </div>
              </div>

              <div className="text-center">
                <h2 className="text-yellow-500 text-[3.25rem] -mb-1" style={{ fontFamily: 'OptimusPrinceps, serif' }}>
                  Scholar
                </h2>
                <p className="text-neutral-500 text-base tracking-widest uppercase mb-3" style={{ fontFamily: 'OptimusPrinceps, serif' }}>
                  Seek Guidance from the Archives
                </p>
                <p className="text-neutral-400 text-sm max-w-sm mx-auto leading-relaxed">
                  AI wiki companion for Scholar of the First Sin
                </p>
              </div>

              <div className="w-full max-w-lg grid grid-cols-2 gap-2">
                {[
                  { label: 'Check Soul Memory Tier', action: handleCheckSoulMemory },
                  { label: 'Soul Memory explained', q: 'How does Soul Memory work and how does it affect matchmaking?' },
                  { label: 'How to beat The Pursuer?', q: 'How do I beat The Pursuer boss in Dark Souls 2?' },
                  { label: 'Best PvE build?', q: 'What is a good beginner PvE build for Dark Souls 2?' },
                  { label: 'Where to farm souls?', q: 'What are the best places to farm souls early on?' },
                  { label: 'ADP & iframes explained', q: 'How does Adaptability affect dodge roll iframes?' },
                ].map(({ label, q, action }) => (
                  <button
                    key={label}
                    onClick={() => action ? action() : handleSend(q)}
                    className="text-center px-5 py-3.5 rounded-xl bg-neutral-800 hover:bg-neutral-700/80 text-neutral-400 hover:text-neutral-200 text-sm transition-all leading-snug shadow-sm hover:shadow-md"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[75%] px-4 py-2.5 text-sm leading-relaxed break-words ${
                  msg.role === 'user'
                    ? 'bg-yellow-700/80 text-neutral-100 rounded-2xl rounded-br-none whitespace-pre-wrap'
                    : 'bg-neutral-800 text-neutral-200 rounded-2xl rounded-bl-none shadow-md shadow-black/30'
                }`}
              >
                {msg.role === 'user' ? msg.content : (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      h1: ({ children }) => <h1 className="text-[#c9a84c] font-bold text-base mt-3 mb-1 first:mt-0">{children}</h1>,
                      h2: ({ children }) => <h2 className="text-[#c9a84c] font-bold text-sm mt-3 mb-1 first:mt-0">{children}</h2>,
                      h3: ({ children }) => <h3 className="text-[#c9a84c] font-semibold text-sm mt-2 mb-1 first:mt-0">{children}</h3>,
                      p: ({ children }) => <p className="mb-2 last:mb-0 text-neutral-200">{children}</p>,
                      ul: ({ children }) => <ul className="list-disc list-outside pl-5 mb-2 space-y-1">{children}</ul>,
                      ol: ({ children }) => <ol className="list-decimal list-outside pl-5 mb-2 space-y-1">{children}</ol>,
                      li: ({ children }) => <li className="text-neutral-200 leading-relaxed">{children}</li>,
                      strong: ({ children }) => <strong className="text-neutral-100 font-semibold">{children}</strong>,
                      em: ({ children }) => <em className="text-neutral-300 italic">{children}</em>,
                      code: ({ children }) => <code className="bg-neutral-900/80 text-yellow-300 rounded px-1 py-0.5 text-xs font-mono">{children}</code>,
                      pre: ({ children }) => <pre className="bg-neutral-900/80 rounded-lg p-3 mb-2 overflow-x-auto text-xs font-mono text-yellow-200">{children}</pre>,
                      hr: () => <hr className="border-neutral-700 my-2" />,
                      table: ({ children }) => <div className="overflow-x-auto mb-2"><table className="w-full border-collapse text-xs">{children}</table></div>,
                      thead: ({ children }) => <thead className="bg-neutral-900/60">{children}</thead>,
                      tbody: ({ children }) => <tbody>{children}</tbody>,
                      tr: ({ children }) => <tr className="border-b border-neutral-700/50">{children}</tr>,
                      th: ({ children }) => <th className="text-left text-[#c9a84c] font-semibold px-3 py-1.5 border border-neutral-700/50 whitespace-nowrap">{children}</th>,
                      td: ({ children }) => <td className="text-neutral-200 px-3 py-1.5 border border-neutral-700/50">{children}</td>,
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-neutral-800 rounded-2xl rounded-bl-none px-4 py-2.5 text-sm text-yellow-500 italic animate-pulse shadow-md shadow-black/30">
                Consulting the wiki...
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </main>

        {/* Input */}
        <footer className="px-4 pt-[19px] pb-[19px] bg-neutral-800 shrink-0 border-t border-white/[0.06]">
          {/* Slash command menu */}
          {input.startsWith('/') && !input.includes(' ') && (() => {
            const filtered = SLASH_COMMANDS.filter(({ cmd }) =>
              cmd.toLowerCase().startsWith(input.toLowerCase())
            );
            if (!filtered.length) return null;
            return (
              <div className="mb-2 bg-neutral-700 rounded-xl overflow-hidden shadow-xl shadow-black/50">
                {filtered.map(({ cmd, desc }) => (
                  <button
                    key={cmd}
                    onMouseDown={e => {
                      e.preventDefault();
                      if (cmd === '/level') {
                        // Execute immediately — no arguments needed
                        setInput('');
                        setLevelDraft({ ...stats });
                        setLevelStep('count');
                        setLevelCount('');
                        setLevelModalOpen(true);
                      } else {
                        const newVal = cmd + ' ';
                        setInput(newVal);
                        requestAnimationFrame(() => requestAnimationFrame(() => {
                          if (textareaRef.current) {
                            textareaRef.current.focus();
                            textareaRef.current.setSelectionRange(newVal.length, newVal.length);
                          }
                        }));
                      }
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-neutral-600/80 transition-colors flex items-baseline gap-2"
                  >
                    <span className="text-yellow-400 text-sm font-mono shrink-0">{cmd}</span>
                    <span className="text-neutral-400 text-xs">{desc}</span>
                  </button>
                ))}
              </div>
            );
          })()}
          <div className="flex gap-2 items-end">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={loading}
              placeholder="Ask the Scholar... (Enter to send, Shift+Enter for new line, / for commands)"
              className="flex-1 bg-neutral-700/70 rounded-xl px-3 py-2.5 text-sm text-neutral-100 placeholder-neutral-500 focus:outline-none focus:ring-1 focus:ring-inset focus:ring-yellow-600/50 resize-none leading-relaxed disabled:opacity-50"
              style={{ minHeight: '42px', maxHeight: '160px', overflowY: 'auto' }}
              onInput={e => {
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px';
              }}
            />
            <button
              onClick={() => handleSend()}
              disabled={loading || !input.trim()}
              className="shrink-0 bg-yellow-600 hover:bg-yellow-500 active:bg-yellow-700 disabled:opacity-40 disabled:cursor-not-allowed text-neutral-900 font-semibold text-sm rounded-xl px-4 py-2.5 transition-colors"
            >
              Send
            </button>
          </div>
        </footer>
      </div>

      {/* /level modal */}
      {levelModalOpen && (() => {
        const total = parseInt(levelCount) || 0;
        const spent = STAT_FIELDS.reduce((sum, { key }) => {
          return sum + Math.max(0, (parseInt(levelDraft[key]) || 0) - (parseInt(stats[key]) || 0));
        }, 0);
        const remaining = total - spent;
        const currentSL = parseInt(stats.soul_level) || 0;

        return (
          <div
            className="fixed inset-0 bg-black/75 flex items-center justify-center z-50"
            onClick={handleCloseLevelModal}
          >
            <div
              className="bg-neutral-800 rounded-2xl px-6 py-7 w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto shadow-2xl shadow-black/80"
              onClick={e => e.stopPropagation()}
            >
              <h2
                className="text-yellow-500 text-3xl text-center"
                style={{ fontFamily: 'OptimusPrinceps, serif' }}
              >
                Level Up
              </h2>

              {levelStep === 'count' ? (
                /* Step 1 — how many levels? */
                <div className="flex flex-col items-center gap-5 mt-2">
                  <p className="text-neutral-300 text-sm -mb-1">How many levels did you gain?</p>
                  <input
                    type="number"
                    min="1"
                    value={levelCount}
                    onChange={e => setLevelCount(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter' && parseInt(levelCount) > 0) {
                        setLevelDraft({ ...stats });
                        setLevelStep('distribute');
                      }
                    }}
                    autoFocus
                    className="bg-neutral-700/70 rounded-lg px-3 py-2 text-center text-neutral-100 text-lg w-16 focus:outline-none focus:ring-1 focus:ring-inset focus:ring-yellow-600/50 my-2"
                    placeholder=""
                  />
                  <div className="flex gap-2 w-full">
                    <button
                      onClick={handleCloseLevelModal}
                      className="flex-1 bg-neutral-700/60 hover:bg-neutral-700 text-neutral-200 text-sm font-semibold rounded-xl py-2.5 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => {
                        if (parseInt(levelCount) > 0) {
                          setLevelDraft({ ...stats });
                          setLevelStep('distribute');
                        }
                      }}
                      disabled={!(parseInt(levelCount) > 0)}
                      className="flex-1 bg-yellow-600 hover:bg-yellow-500 disabled:opacity-40 disabled:cursor-not-allowed text-neutral-900 text-sm font-semibold rounded-xl py-2.5 transition-colors"
                    >
                      Continue
                    </button>
                  </div>
                </div>
              ) : (
                /* Step 2 — distribute levels */
                <>
                  {/* Soul level + remaining counter */}
                  <div className="text-center mt-1 mb- space-y-1.5">
                    <p className="text-neutral-400 text-base">
                      Soul Level:&nbsp;
                      <span className="text-neutral-200">{currentSL || '—'}</span>
                      {spent > 0 && <span className="text-yellow-400"> → {currentSL + spent}</span>}
                    </p>
                    <p
                      className={`text-[1.35rem] ${remaining > 0 ? 'text-yellow-400' : 'text-neutral-500'}`}
                      style={{ fontFamily: 'OptimusPrinceps, serif' }}
                    >
                      {remaining} level{remaining !== 1 ? 's' : ''} remaining
                    </p>
                  </div>

                  {/* Stats grid — 3 columns */}
                  <div className="grid grid-cols-3 gap-x-6 gap-y-5 mb-2 mx-auto" style={{ width: 'fit-content' }}>
                    {STAT_FIELDS.map(({ key, label, icon }) => {
                      const draftVal = parseInt(levelDraft[key]) || 0;
                      const origVal = parseInt(stats[key]) || 0;
                      const added = draftVal - origVal;
                      return (
                        <div key={key} className="flex flex-col items-center gap-1.5">
                          <label className="flex items-center gap-1.5 text-xs text-neutral-400 uppercase tracking-wider">
                            <img src={icon} alt={label} className="w-8 h-8 object-contain" />
                            {label}
                          </label>
                          <div className="flex items-center gap-2">
                            <span className="text-neutral-200 text-base w-8 text-right">
                              {levelDraft[key] || '—'}
                            </span>
                            <button
                              disabled={remaining <= 0}
                              onClick={() => setLevelDraft(prev => ({
                                ...prev,
                                [key]: String((parseInt(prev[key]) || 0) + 1),
                              }))}
                              className="w-6 h-6 flex items-center justify-center rounded-lg bg-neutral-700/70 hover:bg-yellow-600 disabled:opacity-30 disabled:cursor-not-allowed text-neutral-200 hover:text-neutral-900 transition-colors text-xs"
                            >
                              ▲
                            </button>
                          </div>
                          <span className={`text-[10px] leading-none ${added > 0 ? 'text-yellow-500' : 'invisible'}`}>
                            +{added}
                          </span>
                        </div>
                      );
                    })}
                  </div>

                  {/* Clear selection */}
                  <div className="flex justify-center mb-7">
                    <button
                      onClick={() => setLevelDraft({ ...stats })}
                      disabled={spent === 0}
                      className="text-xs text-neutral-300 hover:text-neutral-100 disabled:text-neutral-500 disabled:cursor-not-allowed transition-colors"
                    >
                      Clear selection
                    </button>
                  </div>

                  {/* Buttons */}
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={handleCloseLevelModal}
                      className="flex-1 bg-neutral-700/60 hover:bg-neutral-700 text-neutral-200 text-sm font-semibold rounded-xl py-2 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleConfirmLevel}
                      className="flex-1 bg-yellow-600 hover:bg-yellow-500 active:bg-yellow-700 text-neutral-900 text-sm font-semibold rounded-xl py-2 transition-colors"
                    >
                      Confirm
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        );
      })()}
    </div>
  );
}

export default App;
