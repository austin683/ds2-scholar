# DS2 Scholar - Utility Functions
# Soul Memory Tier Checker + Player Stats Context Builder

# ─────────────────────────────────────────
# SOUL MEMORY TIER CHECKER
# ─────────────────────────────────────────

SOUL_MEMORY_TIERS = [
    (0,         9999,      1),
    (10000,     49999,     2),
    (50000,     99999,     3),
    (100000,    249999,    4),
    (250000,    499999,    5),
    (500000,    999999,    6),
    (1000000,   2999999,   7),
    (3000000,   9999999,   8),
    (10000000,  99999999,  9),
]

def get_soul_memory_tier(soul_memory: int) -> dict:
    """
    Given a Soul Memory value, returns tier info and matchmaking range.
    """
    for low, high, tier in SOUL_MEMORY_TIERS:
        if low <= soul_memory <= high:
            lower_bound = SOUL_MEMORY_TIERS[max(0, tier - 2)][0]
            upper_bound = SOUL_MEMORY_TIERS[min(len(SOUL_MEMORY_TIERS) - 1, tier)][1]
            souls_to_next = high - soul_memory + 1 if tier < 9 else 0

            return {
                "soul_memory": soul_memory,
                "tier": tier,
                "tier_range": f"{low:,} - {high:,}",
                "matchmaking_range": f"{lower_bound:,} - {upper_bound:,}",
                "souls_to_next_tier": souls_to_next,
                "summary": (
                    f"Tier {tier} | Range: {low:,}–{high:,} | "
                    f"You can match with players from {lower_bound:,}–{upper_bound:,} Soul Memory. "
                    f"{'Souls to next tier: ' + f'{souls_to_next:,}' if souls_to_next else 'Max tier reached.'}"
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
    test_values = [5000, 75000, 300000, 1500000]
    for sm in test_values:
        result = get_soul_memory_tier(sm)
        print(f"SM {sm:,}: {result['summary']}")

    print("\n=== Player Context Builder ===")
    test_stats = {
        "soul_level": 52,
        "soul_memory": 300000,
        "vigor": 20,
        "endurance": 15,
        "vitality": 15,
        "attunement": 20,
        "strength": 20,
        "dexterity": 12,
        "adaptability": 10,
        "intelligence": 30,
        "faith": 30,
        "main_hand": "Flame Longsword +3",
        "off_hand": "Sunset Staff +5",
        "current_area": "Iron Keep",
        "last_boss_defeated": "Lost Sinner",
        "build_type": "Hex",
        "notes": "Looking to transition to a better hex weapon",
    }
    print(format_player_context(test_stats))