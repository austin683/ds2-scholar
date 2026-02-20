# Source: https://darksouls2.wiki.fextralife.com/Agility

| Agility | Agility |
    | --- | --- |
    |  |  |
    | Type | Stat |
    

**Agility (AGL)** is a secondary attribute that is determined by the primary attributes [Adaptability](/Adaptability "Dark Souls 2 Adaptability")****(ADP) and [Attunement](/Attunement "Dark Souls 2 Attunement")****(ATN). You can find this value in the Player Status screen, in the third column from the left, near the bottom.

Agility increases the duration of invincibility while dodging, the speed of using [consumable](/Consumables "Dark Souls 2 Consumables") items (including the [Estus Flask](/Estus+Flask "Dark Souls 2 Estus Flask")), the speed at which you toggle between LH/RH equipment slots, and the speed at which you raise your guard while blocking.

### Agility and Invincibility Frames (I-frames)

'I-frame' is short for **invincibility frame**. One frame is 1/30 of a second (this duration comes from the original console versions of the game running at 30 frames per second). Running at a higher framerate doesn’t change the total invincibility duration, but the duration itself is measured in these exact increments.

I-frames begin on the first frame of the rolling animation.
    
    
    | Agility | AGL Investment | Invincibility Frames (Roll) | Duration |
    | --- | --- | --- | --- |
    | 85(a) | 1 | 6 | 0.2 sec |
    | 85(b) | 2 | 7 | 0.23 sec |
    | 85(e) | 5 | 8 | 0.27 sec |
    | 88 | 8 | 9 | 0.3 sec |
    | 92 | 12 | 10 | 0.33 sec |
    | 96 | 16 | 11 | 0.37 sec |
    | 99 | 19 | 12 | 0.4 sec |
    | 105 | 25 | 13 | 0.43 sec |
    | 110(d) | 33 | 14 | 0.47 sec |
    | 113(c) | 53 | 15 | 0.5 sec |
    | 116(a) | 72 | 16 | 0.53 sec |
    | 120 | 99 | 17 | 0.57 sec |
    

I-frames begin on the fifth frame of the backstep animation.
    
    
    | Agility | AGL Investment | Invincibility Frames (Backstep) | Duration |
    | --- | --- | --- | --- |
    | 85(a) | 1 | 2 | 0.07 sec |
    | 85(d) | 4 | 3 | 0.1 sec |
    | 87 | 7 | 4 | 0.13 sec |
    | 91 | 11 | 5 | 0.17 sec |
    | 96 | 16 | 6 | 0.2 sec |
    | 100 | 20 | 7 | 0.23 sec |
    | 108 | 28 | 8 | 0.27 sec |
    | 112(b) | 45 | 9 | 0.3 sec |
    | 115(d) | 68 | 10 | 0.33 sec |
    | 120 | 99 | 11 | 0.37 sec |
    

### How Agility is calculated in Dark Souls 2

Your ADP is multiplied by 0.75, and your ATN is multiplied by 0.25. These values, called 'ADP investment' and 'ATN investment' respectively, are added together to determine your 'AGL investment' (which is rounded down to the nearest whole number). There are 99 possible values for AGL investment: 1 = 85(a) AGL, 2 = 85(b) AGL, etc. Each of these values correlates to a specific amount of frames while dodging. The charts above only show the breakpoints for I-frames while rolling or backstepping. Since AGL works as a series of breakpoints, there is no benefit in having an Agility value between any of those listed, since they offer no benefit (89 is the exact same as 88, for example).

As you level ADP/ATN, your AGL will always rise, but the value in the player status menu will not always be updated. The letters used for some low and high values signify differences in AGL investment that are not accurately reflected in the menu. Most players will end up with 86-105 AGL, so this factor can usually be ignored.

Example: the Bandit starting class begins with 3 ADP and 2 ATN. 3(0.75) + 2(0.25) = 2.75, rounded down to 2. So we have an AGL investment of 2, which corresponds to 85(b) AGL. This means that in-game, the menu only shows that we have 85 AGL, but the class starts with 7/2 I-frames on roll/backstep.

### The secondary functions of Agility

**Weapon Swap** \- The speed at which you can swap between equipment in your RH/LH slots. This multiplier scales from 120% at minimum AGL up to 145% at maximum AGL.

**Blocking** \- The speed at which you can raise your guard (shield/weapon) to block an incoming attack. This multiplier scales from 100% at minimum AGL up to 150% at maximum AGL.

**Item Use** \- The speed at which you use items, including the Estus Flask. This multiplier sees change only between 90 and 100 AGL. 
    
    
    | Agility | Item Usage Speed |
    | --- | --- |
    | 85-90 | 97% |
    | 91 | 99% |
    | 92 | 101% |
    | 93 | 103% |
    | 94 | 106% |
    | 95 | 109% |
    | 96 | 112% |
    | 97 | 113% |
    | 98 | 115% |
    | 99 | 117% |
    | 100-120 | 120% |
    

The duration for drinking Estus is 2.5 seconds at base AGL, and slightly over 2 seconds at 100 AGL. Note that while using the Estus Flask, HP is not restored instantly but rather regenerated over a few seconds. This speed, around 300-310 HP/second, is not affected in any way by AGL. Since 100 AGL does not provide an additional i-frame while rolling, many players elect to remain at 99 AGL and forego the final 3% in item usage speed (the difference is imperceptible).

### Additional information on Rolling

  * Rolling consumes 30 stamina points, and this cost is increased to 37.5 stamina points (+25%) if you chain multiple rolls. If your roll exhausts your stamina to below 0, it will provide a reduced amount of I-frames (exact values unknown).
  * While below 70% equipment load, the rolling animation lasts 25 frames total. If your equipment load is >70%, the animation lasts 31 frames. The distance traveled while rolling is not determined by AGL, but by equipment load in a mostly linear fashion.
  * There is a separate status during frames 1-20 of the rolling animation, called 'super armor'. While in this state, you can receive damage, but you will never be staggered regardless of your current poise.
  * If your character does not meet the attribute requirements for the armor they are wearing, rolling will cost additional stamina and provide reduced I-frames.

    
    
    | Stats |
    | --- |
    | Adaptability ♦ Attunement ♦ Bonfires ♦ Dexterity ♦ Endurance ♦ Equipment Load ♦ Faith ♦ Intelligence ♦ Soul Memory ♦ Stamina ♦ Stats ♦ strength ♦ Vigor ♦ Vitality |