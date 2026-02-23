// DS2 Scholar — Game Configuration
// All Dark Souls 2-specific UI data lives here.
// To support a new game, create a parallel config object and swap the import in App.js.
// Data mirrors backend/configs/ds2.py (frontend-relevant fields only).

export const GAME_CONFIG = {
  // ── Identity ────────────────────────────────────────────────────────────────
  gameId: 'ds2',
  gameName: 'Dark Souls II',
  displayFont: "'OptimusPrinceps', serif",
  theme: {
    divider: '#ca8a04',
    userBubbleTail: 'rgba(180, 83, 9, 0.8)',
  },
  botName: 'Scholar',
  tagline: 'Seek Guidance from the Archives',
  description: 'AI wiki companion for Scholar of the First Sin',
  placeholderText: 'Ask the Scholar... (Enter to send, Shift+Enter for new line, / for commands)',

  // ── localStorage ────────────────────────────────────────────────────────────
  localStorageKey: 'ds2_player_stats',

  // ── Multiplayer system ──────────────────────────────────────────────────────
  // Set to true when the game uses a tier-based matchmaking system (Soul Memory).
  // When false, the "Check Soul Memory Tier" suggested question is hidden.
  hasSoulMemory: true,

  // ── Slash commands ──────────────────────────────────────────────────────────
  slashCommands: [
    { cmd: '/level', desc: 'Open level-up stat allocator' },
    { cmd: '/area',  desc: 'Set your current area (e.g. /area Lost Bastille)' },
    { cmd: '/clear', desc: 'Clear the chat history' },
  ],

  // ── Sidebar right-column fields ──────────────────────────────────────────────
  // These appear in the right column of the player stats panel, aligned with the
  // first N left-column stat rows. Notes always occupies the last two rows.
  sidebarRightFields: [
    { key: 'soul_level',        label: 'Level',          type: 'number' },
    { key: 'soul_memory',       label: 'Soul Memory',    type: 'number' },
    { key: 'main_hand',         label: 'Right Weapon 1', type: 'text'   },
    { key: 'off_hand',          label: 'Right Weapon 2', type: 'text'   },
    { key: 'build_type',        label: 'Build Type',     type: 'text'   },
    { key: 'current_area',      label: 'Current Area',   type: 'text'   },
    { key: 'last_boss_defeated',label: 'Last Boss',      type: 'text'   },
  ],

  // ── Stat fields (sidebar grid) ───────────────────────────────────────────────
  // key: short frontend key used in the stats form state
  // label: display abbreviation shown next to the icon
  // icon: path to the stat icon in /public/icons/
  statFields: [
    { key: 'vgr', label: 'VGR', icon: '/icons/icon-vigor.png' },
    { key: 'end', label: 'END', icon: '/icons/icon-endurance.png' },
    { key: 'vit', label: 'VIT', icon: '/icons/icon-vitality.png' },
    { key: 'atn', label: 'ATN', icon: '/icons/icon-attunement.png' },
    { key: 'str', label: 'STR', icon: '/icons/icon-strength.png' },
    { key: 'dex', label: 'DEX', icon: '/icons/icon-dexterity.png' },
    { key: 'adp', label: 'ADP', icon: '/icons/icon-adaptability.png' },
    { key: 'int', label: 'INT', icon: '/icons/icon-intelligence.png' },
    { key: 'fth', label: 'FTH', icon: '/icons/icon-faith.png' },
  ],

  // ── Stat key map ────────────────────────────────────────────────────────────
  // Maps the short frontend stat keys to the field names the backend PlayerStats model expects.
  statKeyMap: {
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
  },

  // ── Default stats (empty form state) ────────────────────────────────────────
  defaultStats: {
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
  },

  // ── Suggested questions (home screen grid) ──────────────────────────────────
  // Each entry has a `label` (button text) and either:
  //   `q`      — a question string sent directly to the chat
  //   `action` — a string key dispatched to the `handlers` object in App.js
  suggestedQuestions: [
    { label: 'Soul Memory explained', q: 'How does Soul Memory work and how does it affect matchmaking?' },
    { label: 'Check Soul Memory Tier', action: 'handleCheckSoulMemory' },
    { label: 'How to beat The Pursuer?', q: 'How do I beat The Pursuer boss in Dark Souls 2?' },
    { label: 'Best starting class?', q: 'What is the best starting class for a beginner in Dark Souls 2?' },
    { label: 'Where to farm souls?', q: 'What are the best places to farm souls early on?' },
    { label: 'ADP & iframes explained', q: 'How does Adaptability affect dodge roll iframes?' },
  ],
};

export default GAME_CONFIG;
