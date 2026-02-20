# Source: https://darksouls2.wiki.fextralife.com/poise

#  Poise

  * Poise is an in-game statistic that increases your resistance to being staggered or stun-locked as an effect of taking hits from opponents. 
    * Interrupt: an enemy's attack interrups your action
    * Staggered:  an enemy's attacks causes you to temporarily be paralyzed, leaving you vulnerable to consecutive hits.
    * Stun-locked: being staggered continously.
  * Endurance and Adaptability contribute to your natural poise if raised equally. In other words: if you have 20/40 END and ADP, the contribution to your poise will be limited by the lower, to 20. If you have 40/40 END and ADP, then the contribution to you poise from these stats will be 40. Raising the lower of the two always results in poise gain.

##  How it works:

First, what is poise? **Poise is an invisible bar that lets you not get staggered when you get hit by an attack.** As long as you have more poise in your bar than the attack will damage your poise for (even 0.01 more), you will not be staggered, except in special cases that we will cover later. It does not matter how much more poise you have, as long as it’s higher than the attack you received.  
When you are in an attack animation and your poise allows you to not get staggered, the attack will go through as if nothing happened. When you are standing still, walking or running, getting hit with enough poise will put you in a half stagger animation, where movement speed is slightly reduced but you are not prevented from performing any actions. Poise damage is exactly the same in both instances above. The only difference is the half stagger animation.   
  
Poise damage is only reduced on a glancing blow. A glancing blow is, for example, when the player hits with the very tip of the weapon and it does reduced damage. There hasn't been extensive testing on them, but there seems to be a reduction of poise damage on glancing blows, which is speculated to be proportional to the percent of regular damage reduction.   
Note that some weapons, such as spears, will do the most damage at the closest distance and won’t do as much where you would think that they would.   
  
Stone ring adds 30 poise damage to every attack. Every time damage is dealt, 30 is added to the poise damage that damage instance normally deals.   
  
**When an attack hits you and your poise is depleted, as soon as your stagger animation ends your poise will be instantly reset to full.** Since the stagger animation must end, if you don’t roll away from attacks, your poise won't be reset and will continue to be staggered.   
When an attack hits you, your poise is not depleted, and don't receive any further poise damage, it begins to refill at a rate of 0.56 poise per second, regardless of maximum poise or current poise. **Poise regenerates at a rate of 0.56 poise per second.** This is so slow that poise can be effectively considered nonregenerative.   
  
An example on why poise is effectively nonregenerative: You are fighting with 55 poise, and your opponent hits you with a One Handed (1H) Light Attack (R1) of the Rapier. Your poise is now lowered to 20 and you are not staggered. We need 15 poise to regenerate to be above 35 poise and not get staggered by the next attack, so we will do some calculations. 15 poise divided by 0.56 poise per second gives us the amount of seconds it will take. The result of the calculation comes out to 26.8 seconds. **Poise regenerates so slowly that the fastest way to get your poise back to full is to get hit down to 0 poise to allow it to instantly reset.**   
  
**There are many attacks that have a poise damage value and subtract from your current poise, but will normally always stagger you.** The only time they will not stagger you is when you are within hyper armor frames, which we'll cover later. Another example for clarification:   
Once again, you have 55 poise and you opponent is 1 handing the Rapier. He hits you with a rolling attack, lowering your poise by 28 and staggering you, because rolling attacks always stagger. You are now left with 27 poise. He now hits you with a 1H R1 and it now also staggers you because the rolling attack both staggered you AND lowered your poise.   
As a note, if you’re wondering how long it would take to regenerate the 8 poise needed to be above 35, it would take 14.3 seconds.   
  
Next, we cover what are hyper armor frames and which weapons have them. When attacking with most great weapons, there will be hyper armor for a certain amount of frames (amount unknown), both before and after the attack.. **When you are hit with an attack while you are within hyper armor frames, all poise damage is halved and attacks that normally always stagger are now poisable.** The attacks with hyper armor frames are all Ultra Greatsword attacks, all Great Axe attacks, all Great Hammer attacks (excluding 1H Rolling and 2H R2), Halberd 1H R1, 1H R2, 1H Rolling, 2H R1 excluding Helix Halberd 1H R2, and parries with these weapons.   
No other attacks have hyper armor frames, although powerstancing is not taken into account for there are no further testing.  
  
One last example: Once again you have 55 poise and your opponent is using the Rapier one handed. You are wielding the Zweihander. Your opponent hits you with a 1H Rolling attack. However, you are not staggered because you timed your 2H R1 properly to utilize your hyper armor frames. The 28 poise damage of the rolling attack is halved to 14 and you are left with 41 poise. Your opponent follows up with a 1H R1 when you are not in hyper armor frames, but once again you are not staggered because of the reduced poise damage on the rolling attack. You are now left with 6 poise.

As the last example shows, hyper armor frames are extremely strong and proper utilization of them is very important for great weapon play.

#### Tools used for testing

This next part will go over the methods used to find all of this and how to reproduce my results. Let’s first go over how I found the breakpoints. Of course, Cheat Engine was used to monitor and edit my current and maximum poise. I set my current and max poise to 1000 (it can be any number) and then got hit by an attack and recorded the drop in current poise. Because I was put into at least a half stagger my poise did not begin regenerating immediately, so I could record exact poise damage. For finding which attacks need hyper armor frames, I either just walked right after being hit or I casted and held down the cast button for Sacred Oath to lock myself in an animation.   
  
Next let’s go over how I found the speed at which poise regenerates. I set my max poise to 100 and then set my current poise to 0.001 and timed how long it took to regenerate, then repeated. The results were both 178.xx seconds. Then I set my max poise to 10,000 and set my current poise to 0.001 and lapped the timer at every 100 poise regenerated until I was at 600 current poise. The results were all 178.xx seconds. I averaged the 8 tests and then divided 100 by the average to get 0.55978 poise per second. After rounding, poise regenerates at 0.56 poise per second.

Finally, I will explain how we found which attacks have hyper armor frames. My partner would draw a greatbow arrow and fire it at me just before my attack hit him. We would repeat this until I did not get staggered by a greatarrow, and if we couldn’t do it after a long time we determined that that attack did not have hyper armor frames.

Enemies Poise

  * Alonne Knight 22
  * Alonne Knight Captain 55
  * Amana Aberration (Lizard Man) 0
  * Amana Priestess (Amana Shrine Maiden) 0
  * Archdrake Pilgrim (Lindelt Cleric) 26,4
  * Ashen Crawler [Old Iron King DLC] 61,6
  * Ashen Warrior [Old Iron King DLC] 28,6
  * Astrologist [Old Iron King DLC] 33
  * Aurous Knight ?
  * Banedigger (Mounted Overseer) X
  * Barrel Carrier (Cask Runner)[Old Iron King DLC] 0
  * Basilisk 0
  * Bell Keeper 0
  * Black Drakeblood Knight (Drakeblood Knight) [Sunken King DLC] 143
  * Bonewheel Skeleton 0
  * Charred Loyce Knight [Ivory King DLC] 57,2
  * Corrosive Egg Crawlers (Corrosive Egg Insect) [Sunken King DLC] 0
  * Cragslipper (Razorback Nightcrawler) X
  * Crystal Lizard 0
  * Dark Priestess 0
  * Dark Spirit - A Chip Off the Ol' Rock 165
  * Dark Spirit - Abyss Ironclad 165
  * Dark Spirit - Pretender to the Xanthous Throne 0
  * Dark Spirit - Shadowveil Assassin 0
  * Dark Spirit - Tenebrous Rogue 0
  * Dark Spirit - The Ghost of Princes Past 77
  * Dark Spirit - Underworld Deadeye 0
  * Darkdweller (Dark Stalker) 0
  * Darksucker (Coal Tar) 0
  * Desert Sorceress 0
  * Dragon Acolyte 0
  * Dragon Knight 55
  * Drakekeeper X
  * Ducal Spider 0
  * Eleum Loyce Giant (Facsimile Giant) [Ivory King DLC] 330
  * Elite Knight [Ivory King DLC] 0
  * Entity of Avarice (Mimic) X110
  * Executioner (Torturer) 26,4
  * Falconer 0
  * Flame Lizard (Flame Salamander) X
  * Forlorn 48,4
  * Forrest Grotesque (Goblin) 0
  * Frozen Reindeer (Ice Stallion) [Ivory King DLC] 121
  * Fume Sorcerer [Old Iron King DLC] 17,6
  * Gaoler (Undead Jailer) 55
  * Giant Warrior (Giant) X
  * Grand Tusk (Fanged Beast) 22
  * Grave Warden 39,6
  * Great Basilisk (Giant Basilisk) X
  * Great Giant Warrior (Elite Giant) X
  * Great Poison Brumer (Giant Acid Horn Beetle) X
  * Greatsword Bell Keeper 88
  * Gyrm Warrior 55
  * Gyrm Worker (Horned Grym) X
  * Hammersmith (Undead Steelworker) 44
  * Headless Vengarl (Vengarl's Body) 66
  * Heide Knight 92,4
  * Hollow Crawler (Undead Supplicant) 0
  * Hollow Infantry 0
  * Hollow Mage 0
  * Hollow Mage (Black) (Necromancer) 0
  * Hollow Peasant (Undead Peasant) 0
  * Hollow Priest (Dark Cleric) 0
  * Hollow Prisoner [Ivory King DLC] 0
  * Hollow Pyromancer 0
  * Hollow Rogue (Rogue) 0
  * Hollow Royal Soldier (Hollow Soldier) 0
  * Hollow Varangian (Varangian Sailor) 0
  * Hunting Dog 46,2
  * Hunting Rat (Corpse Rat) 0
  * Imperious Knight Summoned 22
  * Invisible Roaming Soul (Forest Guardian) 44
  * Iron Headless Warrior (Old Iron King DLC) 194
  * Ironclad Soldier X
  * JESTER THOMAS 48,4
  * Leydia Pyromancer 0
  * Leydia Witch 0
  * Lion Clan Warrior X
  * Maldron The Assassin [Ivory King DLC] 96
  * Masked Manikin (Manikin) 0
  * Mongrel Rat (Dog Rat) 0
  * Nameless Usurper 0
  * Navlaan 0
  * Nimble Shadow (Suspicious Shadows) 0
  * Ogre X
  * Old Green Knight X
  * Oliver the Collector ?
  * Pagan Tree 0
  * Parasitized Undead 0
  * Petrifying Statue Cluster X
  * Poison Brumer (Poison Horn Beetle) X
  * Poison Statue Cluster [Sunken King DLC] X
  * Possessed Armor [Old Iron King DLC] 79,2
  * Primal Elephant Knight 111
  * Prisoned Sinner 0
  * Prowler Hound (Kobold) 0
  * Rampart Golem (Ice Golem) [Ivory King DLC] 70.4/83.6
  * Rampart Hedgehog (Ice Rat / Porcupine) [Ivory King DLC] 0
  * Rampart Soldier [Ivory King DLC] 33/77
  * Retainer Sorcerer (Retainer) [Ivory King DLC] 0
  * Rotten Vermin (Corrosive Ant Queen) X
  * Royal Swordsman 17,6
  * Rupturing Hollow (BOOM) 0
  * Sanctum Knight [Sunken King DLC] 134
  * Sanctum Priestess [Sunken King DLC] 0
  * Sanctum Soldier [Sunken King DLC] 123,2
  * Skeleton 0
  * Stone Knight Horse 30,8
  * Stone Soldier 44
  * Stray Hound (Stray Dog) 0
  * Syan Soldier 88
  * The Imperfect [Sunken King DLC] 264
  * Tseldoran Settler (Duke Tseldora) 0
  * Undead Aberration X22
  * Undead Crypt Knight (Imperious Knight) 220
  * Undead Devourer (Enslaved Pig) 0
  * Undead Huntsman (Artificial Undead) X
  * Wall Spectre (Wall Warrior) X
  * Witchtree (Forest Spirit) [Ivory King DLC] X

Bosses Posture

  * Last Giant X
  * The Pursuer 264
  * Dragonrider 220
  * Old Dragonslayer 220
  * Flexile Sentry 187,5
  * Ruin Sentinel 176
  * Belfry Gargoyle 176
  * Lost Sinner 264
  * Executioners Chariot X
  * Skeleton Lord 55 Poise 112 Stance
  * Covetous Demon X
  * Baneful Queen Mytha 176
  * Old Iron King X
  * Scorpioness Najka 264
  * Royal Rat Authority 0
  * Prowling Magus 30,8
  * Freja X
  * Royal Rat Vanguard X
  * The Rotten X
  * Looking Glass Knight X
  * Demon of Song X
  * Velstadt 308
  * King Vendrick X
  * Guardian Dragon X
  * Ancient Dragon X
  * Giant Lord X
  * Throne Defender & Watcher 176/220
  * Nashandra X
  * Darklurker 264
  * Elana Squalid Queen X
  * Sinh Slumbering Dragon X
  * 3 PVP Cancer 99/66/220
  * Smelter Demon 550
  * Sir Alonne 550
  * Raime 550
  * Alva 550
  * Ivory King 550
  * Lud & Zallen 550
  * Aldia 550