// Elden Ring — Game Configuration
// All Elden Ring-specific UI data lives here.
// Mirrors backend/configs/er.py (frontend-relevant fields only).
// To activate: set REACT_APP_GAME_ID=er before building the frontend.

export const GAME_CONFIG = {
  // ── Identity ────────────────────────────────────────────────────────────────
  gameId: 'er',
  gameName: 'Elden Ring',
  displayFont: "'Cinzel', serif",
  theme: {
    divider: '#d4881c',
    userBubbleTail: 'rgba(160, 100, 18, 0.85)',
  },
  botName: 'Scholar',
  tagline: 'Seek Your Path to the Erdtree',
  description: 'AI wiki companion for Elden Ring',
  placeholderText: 'Ask the Guide... (Enter to send, Shift+Enter for new line, / for commands)',

  // ── localStorage ────────────────────────────────────────────────────────────
  localStorageKey: 'er_player_stats',

  // ── Multiplayer system ──────────────────────────────────────────────────────
  // Elden Ring uses level-range matchmaking, not a tier-based Soul Memory system.
  hasSoulMemory: false,

  // ── Stat icons ──────────────────────────────────────────────────────────────
  // Set to false when individual stat icon PNGs are not available.
  // Icons exist in-game but are not yet sourced as standalone files.
  hasStatIcons: false,

  // ── Slash commands ──────────────────────────────────────────────────────────
  slashCommands: [
    { cmd: '/level', desc: 'Open level-up stat allocator' },
    { cmd: '/area',  desc: 'Set your current area (e.g. /area Caelid)' },
    { cmd: '/clear', desc: 'Clear the chat history' },
  ],

  // ── Stat fields (sidebar left column) ────────────────────────────────────────
  statFields: [
    { key: 'vig', label: 'VIG', icon: '/icons/er/icon-vigor.png' },
    { key: 'mnd', label: 'MND', icon: '/icons/er/icon-mind.png' },
    { key: 'end', label: 'END', icon: '/icons/er/icon-endurance.png' },
    { key: 'str', label: 'STR', icon: '/icons/er/icon-strength.png' },
    { key: 'dex', label: 'DEX', icon: '/icons/er/icon-dexterity.png' },
    { key: 'int', label: 'INT', icon: '/icons/er/icon-intelligence.png' },
    { key: 'fai', label: 'FAI', icon: '/icons/er/icon-faith.png' },
    { key: 'arc', label: 'ARC', icon: '/icons/er/icon-arcane.png' },
  ],

  // ── Sidebar right-column fields ──────────────────────────────────────────────
  // These appear in the right column of the player stats panel, aligned with the
  // first N left-column stat rows. Notes always occupies the last two rows.
  sidebarRightFields: [
    { key: 'soul_level',        label: 'Level',          type: 'number' },
    { key: 'main_hand',         label: 'Right Weapon 1', type: 'text'   },
    { key: 'off_hand',          label: 'Right Weapon 2', type: 'text'   },
    { key: 'build_type',        label: 'Build Type',     type: 'text'   },
    { key: 'current_area',      label: 'Current Area',   type: 'text'   },
    { key: 'last_boss_defeated',label: 'Last Boss',      type: 'text'   },
  ],

  // ── Stat key map ────────────────────────────────────────────────────────────
  statKeyMap: {
    vig: 'vigor',
    mnd: 'mind',
    end: 'endurance',
    str: 'strength',
    dex: 'dexterity',
    int: 'intelligence',
    fai: 'faith',
    arc: 'arcane',
    main_hand: 'right_weapon_1',
    off_hand:  'right_weapon_2',
  },

  // ── Default stats (empty form state) ────────────────────────────────────────
  defaultStats: {
    soul_level: '',
    vig: '', mnd: '', end: '',
    str: '', dex: '', int: '', fai: '', arc: '',
    main_hand: '',
    off_hand: '',
    build_type: '',
    current_area: '',
    last_boss_defeated: '',
    notes: '',
  },

  // ── Suggested questions (home screen grid) ──────────────────────────────────
  suggestedQuestions: [
    { label: 'How to start in Limgrave?', q: 'What should I do first in Limgrave as a new player?' },
    { label: 'Best starting class?',      q: 'What is the best starting class for a beginner in Elden Ring?' },
    { label: 'Ashes of War guide',         q: 'How do Ashes of War work and how do I change them?' },
    { label: 'Bleed build guide',         q: 'How do I build a bleed/hemorrhage build in Elden Ring?' },
    { label: 'How to beat Malenia?',      q: 'How do I beat Malenia, Blade of Miquella?' },
    { label: 'Where to find Smithing Stones?', q: 'Where can I find Smithing Stones to upgrade my weapons?' },
  ],
};

export default GAME_CONFIG;
