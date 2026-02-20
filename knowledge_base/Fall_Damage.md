# Source: https://darksouls2.wiki.fextralife.com/Fall+Damage

# Fall Damage

  
Fall Damage in [Dark Souls 2](/Dark+Souls+2+Wiki "Dark Souls 2 Wiki") has a larger impact on the gameplay than in previous iterations. It is based on a static damage model, meaning you take the same amount of fall damage from the same location regardless of soul level. This can have a significant impact on the game while you are at a low level or are trying to descend down the pit in [Majula](/Majula "Dark Souls 2 Majula"). Fall Damage is also impacted by equip weight, meaning you will take the least amount of fall damage if you are stark naked. Luckily there is a ring, a spell, and various clothing that will lessen the amount of fall damage taken. Falling from a deadly height (determined by dropping a [prism stone](/Prism+Stone "Dark Souls 2 Prism Stone"), purchasable from [Sweet Shalquoir](/Sweet+Shalquoir "Dark Souls 2 Sweet Shalquoir")) will still kill you regardless of HP and equipment.

The formulas that calculate Fall Damage roughly goes as follows (values in meters);

  * 0-5m = 0 (no damage incurred)
  * 5-7m (max 97 HP) = 1945 * (Effective Height-5m) * 2.5%
  * 7-10m (max 584 HP) = 97 + (1945 * (Effective Height-7m) * 10%)
  * 10-19.5m (max 1945 HP) = 584 + (1945 * (Effective Height-10m) * 10.53%)

Effective Height takes into consideration the physical height of the fall and the player's current Equip Load percentage.

  * When Equip Load % is 100% or lower: Effective Height = Height * (1 + (10% * Equip Load %))
  * When Equip Load % is over 100% up to 120%: Effective Height = Height * (1.1 + (50% * (Equip Load % - 100%)))

By comparison, _Demon's Souls_ and _Dark Souls_ had a dynamic fall damage model, where fall damage was a percentage of your current full HP, even if your current full HP was halved from being cursed or wearing rings that affected it.

* * *

### Health

  * Fall damage increases with equipment load, as established before.
  * Armor without the corresponding passive effect does not mitigate fall damage.
  * Height over 19.4m is considered a lethal fall, with the maximum damage possibly taken being 1945 HP.
  * The pit in Majula is roughly 15.4m, so with 0% Equip Load the fall will cost about 1357 HP.
  * With no armor or weapons equipped and only the Silvercat ring, the fall into the pit in Majula will cost about 800 HP.
  * With the jesters tights this can be reduced to 500. Each piece of the [Lion Warrior Set](/Lion+Warrior+Set "Dark Souls 2 Lion Warrior Set") reduces damage even further.
  * Fall Damage reducing items lower Effective Height by certain amounts, listed below.

### Equipment

  * [Silvercat Ring](/Silvercat+Ring "Dark Souls 2 Silvercat Ring") \- 4
  * [Flying Feline Boots](/Flying+Feline+Boots "Dark Souls 2 Flying Feline Boots") \- 3
  * [Jester's Tights](/Jester's+Tights "Dark Souls 2 Jester's Tights") \- 2
  * [Fall Control](/Fall+Control "Dark Souls 2 Fall Control") \- 100 (effectively trivializes fall damage from survivable heights)
  * [Lion Warrior Helm](/Lion+Warrior+Helm "Dark Souls 2 Lion Warrior Helm"), [Cape](/Lion+Warrior+Cape "Dark Souls 2 Lion Warrior Cape"), [Cuffs](/Lion+Warrior+Cuffs "Dark Souls 2 Lion Warrior Cuffs") \- 1
  * [Red Lion Warrior Cape](/Red+Lion+Warrior+Cape "Dark Souls 2 Red Lion Warrior Cape") \- 2
  * [Lion Warrior Skirt](/Lion+Warrior+Skirt "Dark Souls 2 Lion Warrior Skirt") \- 2
  * [Moon Butterfly Wings](/Moon+Butterfly+Wings "Dark Souls 2 Moon Butterfly Wings") \- 2
  * [Moon Butterfly Skirt](/Moon+Butterfly+Skirt "Dark Souls 2 Moon Butterfly Skirt") \- 1
  * [Sanctum Knight Leggings](/Sanctum+Knight+leggings "Dark Souls 2 Sanctum Knight leggings") \- 2

### Fall Damage Notes

  * Credits go to HalfGrownHollow and their findings into DS2 Fall Damage calculations.