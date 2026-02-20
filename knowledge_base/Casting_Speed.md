# Source: https://darksouls2.wiki.fextralife.com/Casting+Speed

| Cast Speed | Cast Speed |
    | --- | --- |
    |  |  |
    | Category | Stat |
    

**Cast Speed** (CS) is a derived stat in [Dark Souls 2](/Dark+Souls+2+Wiki "Dark Souls 2 Wiki"). CS decreases the time it takes from the moment you press to cast a spell to the moment the spell becomes active/is hurled at enemy/completes buff animation.

### Dark Souls 2 Increasing Cast Speed

[Attunement](/Attunement#fex "Dark Souls 2 Attunement#fex") raises CS twice as efficiently as [Intelligence](/Intelligence#fex "Dark Souls 2 Intelligence#fex") or [Faith](/Faith#fex "Dark Souls 2 Faith#fex")

Also, the impact on CS of levels spent on ATN, INT, or FTH is halved above CS 115, and halved again above CS 125.   
More specifically, CS is based on a weighted average of ATN, INT, and FTH:

  * A level spent on ATN counts for a full point of this weighted average
  * A level spent on INT or FTH counts for a half-point of this weighted average.

  
I'm calling this average the woo quotient (W) for now. The formula to find it is:

  * (ATN + (INT/2) + (FTH/2)) / 3 = W

  
Starting out with a naked SL1 sorcerer, here are the breakpoints for cast speed:

  * If CS is between 12 and 115, then +2 CS for every +2 W
  * If CS is between 116 and 125, then +1 CS for every +2 W
  * If CS is between 126 and ???, then +1 CS for every +4 W

  
This formula may actually be **2(ATN/2+(INT+FTH)/4)+35** for CS 35-115 then simply work from there, for example 116-125 would be **((ATN/2+(INT+FTH)/4)*2-80)/2+115**. 

### Effects of Cast Speed

Cast speed affects how quickly your character goes through the spell-casting animation. It means your spells happen faster and you can take action (like rolling) sooner afterward. Right now nobody's published data on how many frames or milliseconds of reduction you get per point of CS, but it's probably just a matter of time.   
  
\- Using the [Cleric's Sacred Chime](/Cleric%27s+Sacred+Chime#fex "Dark Souls 2 Cleric%27s Sacred Chime#fex")   
(140 cast speed) along with 202 character cast speed, my spells are being cast at a little under half the time but not quite a quarter. It's possible that the value is just a flat percentage. For example, using my stats above the total cast speed I have is 347; if we take this as a flat percentage (I cast 347% faster, or it takes me roughly 1/3 the time to cast) it's close to what my actual cast speed seems to be. Also there doesn't seem to be a cap on cast speed, I was in a duel (Blue Sentinels) with someone who seemed to pump everything into cast speed and used pure cast speed armor as well as what seemed to be either Caitha's charm or the Dragon chime; they cast the same spells as me in half the time, Emit Force was sent out in about .3 to .5 seconds.   
  
\- The following data is credit to Lunar Bear of .  
  
According to the video above, the following table can be made. These are +- 1 frame
    
    
    | Casting Speed | 120 | 266 | 348 |
    | --- | --- | --- | --- |
    | Frame (30 FPS) | 1:04 | 1:00 | 0:29 |
    

At absolute best, this puts 348 casting speed at ~6 frames faster than 120 casting speed. This comes to about 0.2 seconds. Comparing 120 casting speed to 266 is approximately 4-5 frames faster, resulting in ~0.14 seconds faster casting.   
This confirms diminishing returns on casting speed. More testing is needed to get exact numbers.