# Source: https://darksouls2.wiki.fextralife.com/Ruler's+Sword

Requirements: STR 20 / C, DEX 20 / C (*D), INT 16, FTH 16

Weapon Type: Greatsword

Attack Type: Slash / Thrust

Enchantable: Yes

Special: No

*When infused: 196 physical dmg/196 elemental dmg and B scaling with chosen element. Dex scaling changes to D. 

**Ruler's Sword** is a **[Greatsword](/Greatswords "Dark Souls 2 Greatswords")** and one of the available **[Weapons](/Weapons "Dark Souls 2 Weapons")** in **[Dark Souls 2](/Dark+Souls+2+Wiki "Dark Souls 2 Wiki")**. **Ruler's Sword** upgrades with [Petrified Dragon Bone](/Petrified+Dragon+Bone "Dark Souls 2 Petrified Dragon Bone") to +5. Holding souls grants a damage bonus, gradually increasing as more souls are amassed, and with 1 million souls, it boasts a total bonus damage of +118. Its move set mirrors that of the [Mirrah Greatsword](/Mirrah+Greatsword "Dark Souls 2 Mirrah Greatsword"). 

> Greatsword of Vendrick, king of Drangleic. The strength of this sword is relative to the number of souls possessed by its wielder.
> 
> The great king shut himself away, and was soon reduced to a mere shell. Just what was it that he yearned to protect?
> 
> Effect: attack boosted by souls held
> 
> Sotfs changed to:
> 
> Greatsword of Vendrick, King of Drangleic. The strength of this sword is relative to the number of souls possessed by its wielder.
> 
> One fragment of Dark, having taken human shape, became obsessed with the King's soul. Impelled by its own cravings, it sought souls, and strove to make the strength of the Giants its own.
> 
> Effect: attack boosted by souls held.

### How to get Ruler's Sword in Dark Souls 2

  * Trade with [Weaponsmith Ornifex](/Weaponsmith+Ornifex "Dark Souls 2 Weaponsmith Ornifex") the [Soul of the King](/Soul+of+the+King "Dark Souls 2 Soul of the King").

### DS2 Ruler's Sword Hints and Tips

  * Upgrades with [Petrified Dragon Bone](/Petrified+Dragon+Bone "Dark Souls 2 Petrified Dragon Bone") to +5
  * At the cap of 1 million souls the total bonus damage of this weapon is +118 (without other bonuses or scaling).
  * Has the same move set as the [Mirrah Greatsword](/Mirrah+Greatsword "Dark Souls 2 Mirrah Greatsword")
  * Formula for bonus damage is this (tested and confirmed only on normal infusion Ruler's Sword +5, tests needed for other infusions, plus it may vary by a minimum value due to decimal digits in the calculation):  
  
Bonus damage = Str scaling + Dex scaling + souls additive;  
  
Str scaling = (43 + (Souls held * 0.000022)) * Atk: Str / 100  
Basically, the souls quantity improves linearly the starting 43, with a maximum value of 43 + 22 when held souls quantity is 1 million. The rest of the formula is to apply the calculated Str scaling to the character's stats and calculate the Str part of the bonus damage.  
  
Dex scaling = (22 + (Souls held * 0.00001)) * Atk: Dex / 100  
Basically, the souls quantity improves linearly the starting 22, with a maximum value of 22 + 10 when held souls quantity is 1 million. The rest of the formula is to apply the calculated Dex scaling to the character's stats and calculate the Dex part of the bonus damage.  
  
souls additive = (Souls held * 0.0001275) - 44  
This regulates the last simplest part. Basically, the souls quantity defines this value and it could be rewrittten like this:  
\- 44 + (127.5 * "how much souls you have on a scale of 1 million")  
So, for example, if you have 50000 souls the value in the parenthesis is 127.5 * 50000/1000000 -> that is 127.5 * 0.05  
I only rewrote the formula as it was first showed to have a more minimal calculation.  
  
Because of this, we could say the scalings are "standard" (so basically when souls additive is equal to 0) when the player has 345098 souls.

    
    
    |  | Ruler's Sword +5 (40 STR, 40 DEX, 16 INT, 16 FAI, carrying 1M souls) | Claymore +10 (40 STR, 40 DEX) |
    | --- | --- | --- |
    | Dogs at MacDuff (NG) | 450 dmg (two handed R1/RB attack) | 405 dmg (two handed R1/RB attack) |
    | Knights at Heide ruins (NG) | 497 dmg (two handed R1/RB attack) | 447 dmg (two handed R1/RB attack) |
    | Knights at Dragon aerie (NG) | 411 dmg (two handed R1/RB attack) | 361 dmg (two handed R1/RB attack) |
    

###  DS2 Ruler's Sword Upgrades Table
    
    
    | Name | Phys Atk | Mag Atk | Fire Atk | Lit Atk | Dark Atk | Stability / Durability | STR Scaling | DEX Scaling | Mag Scaling | Fire Scaling | Lit Scaling | Dark Scaling | Bleed | Poison | Phys DR% | Mag DR% | Fire DR% | Lit DR% | Dark DR% |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    | Regular | 112 | - | - | - | - | 110 / 35 | C | C | - | - | - | - | - | - | 60 | 10 | 40 | 40 | 20 |
    | Regular +5 | 280 | - | - | - | - | ^ | C | C | - | - | - | - | - | - | 60 | 10 | 40 | 40 | 20 |
    | Magic | 78 | 78 | - | - | - | ^ | D | D | C | - | - | - | - | - | 57.9 | 26.6 | 37.9 | 37.9 | 17.9 |
    | Magic +5 | 196 | 196 | - | - | - | ^ | C | D | B | - | - | - | - | - | 57.9 | 26.6 | 37.9 | 37.9 | 17.9 |
    | Fire | 78 | - | 78 | - | - | ^ | D | D | - | C | - | - | - | - | 57.9 | 7.9 | 56.6 | 37.9 | 17.9 |
    | Fire +5 | 196 | - | 196 | - | - | ^ | C | D | - | B | - | - | - | - | 57.9 | 7.9 | 56.6 | 37.9 | 17.9 |
    | Lightning | 78 | - | - | 78 | - | ^ | D | D | - | - | C | - | - | - | 57.9 | 7.9 | 37.9 | 56.6 | 17.9 |
    | Lightning +5 | 196 | - | - | 196 | - | ^ | C | D | - | - | B | - | - | - | 57.9 | 7.9 | 37.9 | 56.6 | 17.9 |
    | Dark | 78 | - | - | - | 78 | ^ | D | D | - | - | - | C | - | - | 57.9 | 7.9 | 37.9 | 37.9 | 36.6 |
    | Dark +5 | 196 | - | - | - | 196 | ^ | C | D | - | - | - | B | - | - | 57.9 | 7.9 | 37.9 | 37.9 | 36.6 |
    | Poison | 78 | - | - | - | - | ^ | D | D | - | - | - | - | 112 | - | 57.9 | 7.9 | 37.9 | 37.9 | 17.9 |
    | Poison +5 | 196 | - | - | - | - | ^ | C | D | - | - | - | - | 140 | - | 57.9 | 7.9 | 37.9 | 37.9 | 17.9 |
    | Bleed | 78 | - | - | - | - | ^ | D | D | - | - | - | - | - | 112 | 57.9 | 7.9 | 37.9 | 37.9 | 17.9 |
    | Bleed +5 | 196 | - | - | - | - | ^ | C | D | - | - | - | - | - | 140 | 57.9 | 7.9 | 37.9 | 37.9 | 17.9 |
    | Raw | 128 | - | - | - | - | ^ | E | E | - | - | - | - | - | - | 60 | 10 | 40 | 40 | 20 |
    | Raw +5 | 322 | - | - | - | - | ^ | E | E | - | - | - | - | - | - | 60 | 10 | 40 | 40 | 20 |
    | Enchanted | 112 | - | - | - | - | ^ | E | E | D | - | - | - | - | - | 60 | 10 | 40 | 40 | 20 |
    | Enchanted+5 | 280 | - | - | - | - | ^ | E | E | D | - | - | - | - | - | 60 | 10 | 40 | 40 | 20 |
    | Mundane | 56 | - | - | - | - | ^ | D | E | - | - | - | - | - | - | 60 | 10 | 40 | 40 | 20 |
    | Mundane +5 | 140 | - | - | - | - | ^ | D | E | - | - | - | - | - | - | 60 | 10 | 40 | 40 | 20 |
    

### DS2 Ruler's Sword Table Key

Please see the [Upgrades](/Upgrades "Dark Souls 2 Upgrades") page for details on Upgrade paths, [ore](/ore "Dark Souls 2 ore") and blacksmiths. You can see the [Stats](/Stats "Dark Souls 2 Stats") page for detailed explanations on what they do.
    
    
    | Requirements/ / Parameter Bonus | Attack Values | Damage Reduction (%) / Reducing the elemental damage taken in % | Auxiliary Effects | Others |
    | --- | --- | --- | --- | --- |
    | / Strength | / Physical | / Physical | / Bleed | / Durability |
    | / Dexterity | / Magic | / Magic | / Poison | / Weight |
    | / Intelligence | / Fire | / Fire | / Petrify | / Cast Speed |
    | / Faith | / Lightning | / Lightning | / Curse | / Range |
    | / Magic Bonus | / Dark | / Stability |  |  |
    | Fire Bonus | / Counter Strength |  |  |  |
    | / Lighting Bonus | / Poise Damage |  |  |  |
    | / Dark Bonus |  |  |  |  |
    

Parameter Bonus: Strength, Dexterity, Magic, Fire, Lightning and Dark bonuses - The scaling multiplier applied to the [Attack: stat]. Scaling quality is from highest to lowest as follows: S/A/B/C/D/E.  
The higher the player's [Str, Dex, Mag, Fire, Lightning, Dark] stat, the higher the [Attack Bonus: Stat] is (found on the player status screen). The higher the scaling letter, the higher the percent multiplier applied to the [Attack: Stat].  
This resulting bonus damage is added to the base physical damage of the weapon and is shown in the equipment screen in blue numbers as a "+ X".  
Attack Type: Defines what kind of moveset the weapon has.  
Physical Damage falls under three categories: [Thrust](/Thrust+Damage "Dark Souls 2 Thrust Damage") (T), [Slash](/Slash+Damage "Dark Souls 2 Slash Damage") (Sl), [Strike](/Strike+Damage "Dark Souls 2 Strike Damage") (St).  
Elemental Damage Types: [Magic](/Magic+Damage "Dark Souls 2 Magic Damage"), [Fire](/Fire+Damage "Dark Souls 2 Fire Damage"), [Lightning](/Lightning+Damage "Dark Souls 2 Lightning Damage"), [Dark](/Dark+Damage "Dark Souls 2 Dark Damage").  
Auxiliary Effects: [Bleed](/Bleed "Dark Souls 2 Bleed"), [Poison](/Poison "Dark Souls 2 Poison"), [Petrification](/Petrification "Dark Souls 2 Petrification"), and [Curse](/Curse "Dark Souls 2 Curse").  
Stability: How well the player keeps stance after being hit.  
Durability: The weapon's HP, when the durability hits 0, the effectiveness of its attacks become weakened to the point of almost uselessness. When an items durability is low, a message will come up saying "Weapon At Risk!".  
Weight: How much the item weighs when equipped.  

    
    
    | Greatswords |
    | --- |
    | Bastard Sword ♦ Black Dragon Greatsword ♦ Black Knight Greatsword ♦ BlueMoon Greatsword ♦ Charred Loyce Greatsword ♦ Claymore ♦ Defender Greatsword ♦ Drakeblood Greatsword ♦ Drangleic Sword ♦ Flamberge ♦ Greatsword of The Forlorn ♦ Key to the Embedded ♦ Loyce Greatsword ♦ Majestic Greatsword ♦ Mastodon Greatsword ♦ Mirrah Greatsword ♦ Moonlight Greatsword ♦ Old Knight Greatsword ♦ Royal Greatsword ♦ Thorned Greatsword ♦ Watcher Greatsword |