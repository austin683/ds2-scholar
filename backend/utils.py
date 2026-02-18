# DS2 Scholar - Utility Functions
# AR Calculator + Soul Memory Tier Checker

# ─────────────────────────────────────────
# SOUL MEMORY TIER CHECKER
# ─────────────────────────────────────────

# Soul Memory tiers for DS2 (Scholar of the First Sin)
# These determine who you can summon/invade with
SOUL_MEMORY_TIERS = [
    (0,       9999,     1),
    (10000,   49999,    2),
    (50000,   99999,    3),
    (100000,  249999,   4),
    (250000,  499999,   5),
    (500000,  999999,   6),
    (1000000, 2999999,  7),
    (3000000, 9999999,  8),
    (10000000,99999999, 9),
]

def get_soul_memory_tier(soul_memory: int) -> dict:
    """
    Given a Soul Memory value, returns tier info and matchmaking range.
    """
    for low, high, tier in SOUL_MEMORY_TIERS:
        if low <= soul_memory <= high:
            # Matchmaking window is your tier and adjacent tiers
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
# AR CALCULATOR
# ─────────────────────────────────────────

# Scaling multipliers by grade at stat value
# Based on DS2 weapon scaling formula
# Grade order: E, D, C, B, A, S
# Returns a 0.0–1.0 multiplier based on stat value

def scaling_multiplier(stat: int, grade: str) -> float:
    """
    Returns the scaling bonus multiplier for a given stat and scaling grade.
    Based on DS2's scaling curve.
    """
    grade = grade.upper().strip()

    if grade == "-" or grade == "" or grade is None:
        return 0.0

    # Base scaling ratios per grade
    grade_ratios = {
        "S": 1.00,
        "A": 0.75,
        "B": 0.55,
        "C": 0.35,
        "D": 0.20,
        "E": 0.10,
    }

    if grade not in grade_ratios:
        return 0.0

    ratio = grade_ratios[grade]

    # DS2 uses a diminishing returns curve
    # Simplified piecewise linear approximation
    if stat <= 20:
        curve = stat / 20 * 0.55
    elif stat <= 40:
        curve = 0.55 + (stat - 20) / 20 * 0.30
    elif stat <= 50:
        curve = 0.85 + (stat - 40) / 10 * 0.10
    else:
        curve = 0.95 + (stat - 50) / 49 * 0.05  # very slow after 50

    return ratio * curve


def calculate_ar(
    base_physical: int,
    base_elemental: int,
    strength: int,
    dexterity: int,
    intelligence: int,
    faith: int,
    str_scale: str = "-",
    dex_scale: str = "-",
    int_scale: str = "-",
    fth_scale: str = "-",
    dark_scale: str = "-",
    upgrade_level: int = 10,
    max_upgrade: int = 10,
) -> dict:
    """
    Calculates estimated AR for a DS2 weapon given stats and scaling.

    Parameters:
        base_physical   : base physical damage at max upgrade
        base_elemental  : base elemental (fire/magic/dark/lightning) damage at max upgrade
        strength        : player STR stat (use two-hand value if two-handing: STR * 1.5)
        dexterity       : player DEX stat
        intelligence    : player INT stat
        faith           : player FTH stat
        str_scale       : STR scaling grade (S/A/B/C/D/E/-)
        dex_scale       : DEX scaling grade
        int_scale       : INT scaling grade
        fth_scale       : FTH scaling grade
        dark_scale      : Dark scaling grade (uses lowest of INT/FTH for dark bonus)
        upgrade_level   : current upgrade level
        max_upgrade     : max upgrade level for this weapon (usually 10, some are 5)
    """

    # Scale base damage to current upgrade level
    upgrade_ratio = upgrade_level / max_upgrade
    scaled_physical = base_physical * upgrade_ratio
    scaled_elemental = base_elemental * upgrade_ratio

    # Physical scaling bonus
    phys_bonus = (
        scaled_physical * scaling_multiplier(strength, str_scale) +
        scaled_physical * scaling_multiplier(dexterity, dex_scale)
    )

    # Elemental scaling bonus
    # Dark damage scales off lowest of INT or FTH
    dark_stat = min(intelligence, faith)
    elem_bonus = (
        scaled_elemental * scaling_multiplier(intelligence, int_scale) +
        scaled_elemental * scaling_multiplier(faith, fth_scale) +
        scaled_elemental * scaling_multiplier(dark_stat, dark_scale)
    )

    total_physical = scaled_physical + phys_bonus
    total_elemental = scaled_elemental + elem_bonus
    total_ar = total_physical + total_elemental

    return {
        "upgrade_level": upgrade_level,
        "physical_ar": round(total_physical),
        "elemental_ar": round(total_elemental),
        "total_ar": round(total_ar),
        "summary": (
            f"+{upgrade_level} | Physical: {round(total_physical)} | "
            f"Elemental: {round(total_elemental)} | "
            f"Total AR: {round(total_ar)}"
        )
    }


def compare_upgrades(
    base_physical: int,
    base_elemental: int,
    strength: int,
    dexterity: int,
    intelligence: int,
    faith: int,
    str_scale: str = "-",
    dex_scale: str = "-",
    int_scale: str = "-",
    fth_scale: str = "-",
    dark_scale: str = "-",
    current_level: int = 0,
    max_upgrade: int = 10,
) -> str:
    """
    Shows AR at every upgrade level from current to max.
    Useful for seeing if further upgrades are worth it.
    """
    results = []
    for lvl in range(current_level, max_upgrade + 1):
        result = calculate_ar(
            base_physical, base_elemental,
            strength, dexterity, intelligence, faith,
            str_scale, dex_scale, int_scale, fth_scale, dark_scale,
            lvl, max_upgrade
        )
        results.append(result["summary"])

    return "\n".join(results)


# ─────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("=== Soul Memory Tier Check ===")
    test_values = [5000, 75000, 300000, 1500000]
    for sm in test_values:
        result = get_soul_memory_tier(sm)
        print(f"SM {sm:,}: {result['summary']}")

    print("\n=== AR Calculator (Crypt Blacksword +5, hex build) ===")
    # Crypt Blacksword: 220 base physical, 0 elemental at +5
    # Scales: STR B, Dark B
    result = calculate_ar(
        base_physical=220,
        base_elemental=110,
        strength=30,
        dexterity=10,
        intelligence=30,
        faith=30,
        str_scale="B",
        dark_scale="B",
        upgrade_level=5,
        max_upgrade=5,
    )
    print(result["summary"])

    print("\n=== Upgrade Comparison (Crypt Blacksword, your stats) ===")
    print(compare_upgrades(
        base_physical=220,
        base_elemental=110,
        strength=30,
        dexterity=10,
        intelligence=30,
        faith=30,
        str_scale="B",
        dark_scale="B",
        current_level=0,
        max_upgrade=5,
    ))