# DS2 Scholar - Utility Functions
# Soul Memory Tier Checker + Player Stats Context Builder

# ─────────────────────────────────────────
# SOUL MEMORY TIER CHECKER
# ─────────────────────────────────────────

# Full 45-tier system as listed on the Fextralife wiki (Soul Memory page).
# Each entry: (lower_bound, upper_bound, tier_number)
SOUL_MEMORY_TIERS = [
    (0,           9_999,       1),
    (10_000,      19_999,      2),
    (20_000,      29_999,      3),
    (30_000,      39_999,      4),
    (40_000,      49_999,      5),
    (50_000,      69_999,      6),
    (70_000,      89_999,      7),
    (90_000,      109_999,     8),
    (110_000,     129_999,     9),
    (130_000,     149_999,     10),
    (150_000,     179_999,     11),
    (180_000,     209_999,     12),
    (210_000,     239_999,     13),
    (240_000,     269_999,     14),
    (270_000,     299_999,     15),
    (300_000,     349_999,     16),
    (350_000,     399_999,     17),
    (400_000,     449_999,     18),
    (450_000,     499_999,     19),
    (500_000,     599_999,     20),
    (600_000,     699_999,     21),
    (700_000,     799_999,     22),
    (800_000,     899_999,     23),
    (900_000,     999_999,     24),
    (1_000_000,   1_099_999,   25),
    (1_100_000,   1_199_999,   26),
    (1_200_000,   1_299_999,   27),
    (1_300_000,   1_399_999,   28),
    (1_400_000,   1_499_999,   29),
    (1_500_000,   1_749_999,   30),
    (1_750_000,   1_999_999,   31),
    (2_000_000,   2_249_999,   32),
    (2_250_000,   2_499_999,   33),
    (2_500_000,   2_749_999,   34),
    (2_750_000,   2_999_999,   35),
    (3_000_000,   4_999_999,   36),
    (5_000_000,   6_999_999,   37),
    (7_000_000,   8_999_999,   38),
    (9_000_000,   11_999_999,  39),
    (12_000_000,  14_999_999,  40),
    (15_000_000,  19_999_999,  41),
    (20_000_000,  29_999_999,  42),
    (30_000_000,  44_999_999,  43),
    (45_000_000,  359_999_999, 44),
    (360_000_000, 999_999_999, 45),
]

MAX_TIER = len(SOUL_MEMORY_TIERS)  # 45

# Tier offsets per multiplayer item (wiki: Soul Memory page, Multiplayer Items table).
# (down_tiers, up_tiers) — how many tiers below/above your own you can connect with.
ITEM_RANGES = {
    "White Sign Soapstone":                      (3, 1),
    "White Sign Soapstone + Name-Engraved Ring": (6, 4),
    "Small White Sign Soapstone":                (4, 2),
    "Small White Sign Soapstone + NER":          (7, 5),
    "Red Sign Soapstone":                        (5, 2),
    "Dragon Eye":                                (5, 5),
    "Cracked Red Eye Orb (invading)":            (0, 4),
}


def _tier_sm_range(tier: int) -> tuple:
    """Return (low, high) soul memory values for the given tier number (1-indexed)."""
    return SOUL_MEMORY_TIERS[tier - 1][:2]


def get_soul_memory_tier(soul_memory: int) -> dict:
    """
    Given a Soul Memory value, returns tier info and per-item matchmaking ranges.
    """
    for low, high, tier in SOUL_MEMORY_TIERS:
        if low <= soul_memory <= high:
            souls_to_next = (high - soul_memory + 1) if tier < MAX_TIER else 0

            # Build per-item matchmaking ranges
            item_ranges = {}
            for item, (down, up) in ITEM_RANGES.items():
                lo_tier = max(1, tier - down)
                hi_tier = min(MAX_TIER, tier + up)
                lo_sm = _tier_sm_range(lo_tier)[0]
                hi_sm = _tier_sm_range(hi_tier)[1]
                item_ranges[item] = f"{lo_sm:,} – {hi_sm:,}"

            # White Sign Soapstone is the most common — use it as the summary range
            wss_lo = max(1, tier - 3)
            wss_hi = min(MAX_TIER, tier + 1)
            matchmaking_range = f"{_tier_sm_range(wss_lo)[0]:,} - {_tier_sm_range(wss_hi)[1]:,}"

            return {
                "soul_memory": soul_memory,
                "tier": tier,
                "tier_range": f"{low:,} - {high:,}",
                "matchmaking_range": matchmaking_range,
                "item_ranges": item_ranges,
                "souls_to_next_tier": souls_to_next,
                "summary": (
                    f"Tier {tier} | Range: {low:,}–{high:,} | "
                    f"White Sign Soapstone range: {matchmaking_range}. "
                    f"{'Souls to next tier: ' + f'{souls_to_next:,}.' if souls_to_next else 'Max tier reached.'}"
                )
            }

    return {"error": "Invalid soul memory value"}


# ─────────────────────────────────────────
# PLAYER STATS CONTEXT BUILDER
# ─────────────────────────────────────────

def format_player_context(stats: dict) -> str:
    """
    Formats player stats into a context string to inject into RAG queries.
    Stats dict can include any combination of the fields below.
    Missing fields are simply omitted.
    """
    lines = ["=== Player Stats ==="]
    lines.append("Game Version: Scholar of the First Sin (SotFS)")

    # Soul info
    if stats.get("soul_level"):
        lines.append(f"Soul Level: {stats['soul_level']}")
    if stats.get("soul_memory"):
        sm = stats["soul_memory"]
        tier_info = get_soul_memory_tier(sm)
        if "tier" in tier_info:
            lines.append(f"Soul Memory: {sm:,} (Tier {tier_info['tier']})")
        else:
            lines.append(f"Soul Memory: {sm:,}")

    # Primary stats (DS2 order)
    stat_labels = {
        "vigor":        "VGR",
        "endurance":    "END",
        "vitality":     "VIT",
        "attunement":   "ATN",
        "strength":     "STR",
        "dexterity":    "DEX",
        "adaptability": "ADP",
        "intelligence": "INT",
        "faith":        "FTH",
    }

    for key, label in stat_labels.items():
        if stats.get(key) is not None:
            lines.append(f"{label}: {stats[key]}")

    # Current weapons
    if stats.get("right_weapon_1"):
        lines.append(f"Right Weapon 1: {stats['right_weapon_1']}")
    if stats.get("right_weapon_2"):
        lines.append(f"Right Weapon 2: {stats['right_weapon_2']}")

    # Current location/progress
    if stats.get("current_area"):
        lines.append(f"Current Area: {stats['current_area']}")
    if stats.get("last_boss_defeated"):
        lines.append(f"Last Boss Defeated: {stats['last_boss_defeated']}")

    # Build notes
    if stats.get("build_type"):
        lines.append(f"Build Type: {stats['build_type']}")
    if stats.get("notes"):
        lines.append(f"Notes: {stats['notes']}")

    lines.append("====================")
    return "\n".join(lines)


# ─────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("=== Soul Memory Tier Check ===")
    test_values = [5000, 318287, 1500000, 360000000]
    for sm in test_values:
        result = get_soul_memory_tier(sm)
        if "error" not in result:
            print(f"SM {sm:,}: {result['summary']}")
            for item, rng in result['item_ranges'].items():
                print(f"  {item}: {rng}")
