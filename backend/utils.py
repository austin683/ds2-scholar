# Scholar companion — Utility Functions
# Soul Memory Tier Checker + Player Stats Context Builder
#
# Both exported functions accept a config object so this module stays
# game-agnostic. Callers (main.py) pass the active GameConfig instance.


def get_soul_memory_tier(soul_memory: int, sm_config) -> dict:
    """
    Given a Soul Memory value and a SoulMemoryConfig, returns tier info
    and per-item matchmaking ranges.

    sm_config: SoulMemoryConfig instance from the active GameConfig.
    """
    for low, high, tier in sm_config.tiers:
        if low <= soul_memory <= high:
            souls_to_next = (high - soul_memory + 1) if tier < sm_config.max_tier else 0

            # Build per-item matchmaking ranges
            item_ranges = {}
            for item, (down, up) in sm_config.item_ranges.items():
                lo_tier = max(1, tier - down)
                hi_tier = min(sm_config.max_tier, tier + up)
                lo_sm = sm_config.tiers[lo_tier - 1][0]
                hi_sm = sm_config.tiers[hi_tier - 1][1]
                item_ranges[item] = f"{lo_sm:,} \u2013 {hi_sm:,}"

            # Summary range uses the designated summary item (White Sign Soapstone for DS2)
            summary_down, summary_up = sm_config.item_ranges.get(sm_config.summary_item, (3, 1))
            wss_lo = max(1, tier - summary_down)
            wss_hi = min(sm_config.max_tier, tier + summary_up)
            matchmaking_range = (
                f"{sm_config.tiers[wss_lo - 1][0]:,} - {sm_config.tiers[wss_hi - 1][1]:,}"
            )

            return {
                "soul_memory": soul_memory,
                "tier": tier,
                "tier_range": f"{low:,} - {high:,}",
                "matchmaking_range": matchmaking_range,
                "item_ranges": item_ranges,
                "souls_to_next_tier": souls_to_next,
                "summary": (
                    f"Tier {tier} | Range: {low:,}\u2013{high:,} | "
                    f"{sm_config.summary_item} range: {matchmaking_range}. "
                    f"{'Souls to next tier: ' + f'{souls_to_next:,}.' if souls_to_next else 'Max tier reached.'}"
                )
            }

    return {"error": "Invalid soul memory value"}


def format_player_context(stats: dict, config) -> str:
    """
    Formats player stats into a context string to inject into RAG queries.

    stats: dict of player stat values (from PlayerStats.dict()).
    config: GameConfig instance from the active game config.

    Missing fields are simply omitted.
    """
    lines = ["=== Player Stats ==="]
    lines.append(f"Game Version: {config.game_version}")

    # Soul info
    if stats.get("soul_level"):
        lines.append(f"Soul Level: {stats['soul_level']}")
    if stats.get("soul_memory") and config.soul_memory:
        sm = stats["soul_memory"]
        tier_info = get_soul_memory_tier(sm, config.soul_memory)
        if "tier" in tier_info:
            lines.append(f"Soul Memory: {sm:,} (Tier {tier_info['tier']})")
        else:
            lines.append(f"Soul Memory: {sm:,}")

    # Primary stats — driven by config so new games only change stat_labels
    for key, label in config.stat_labels.items():
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
    from backend.configs.ds2 import DS2_CONFIG
    print("=== Soul Memory Tier Check ===")
    test_values = [5000, 318287, 1500000, 360000000]
    for sm in test_values:
        result = get_soul_memory_tier(sm, DS2_CONFIG.soul_memory)
        if "error" not in result:
            print(f"SM {sm:,}: {result['summary']}")
            for item, rng in result['item_ranges'].items():
                print(f"  {item}: {rng}")
