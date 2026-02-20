# Source: https://darksouls2.wiki.fextralife.com/Item+Discovery

Item discovery is a hidden [stat](/Stats "Dark Souls 2 Stats") in [Dark Souls 2](/Dark+Souls+2+Wiki "Dark Souls 2 Wiki") that represents the rate at which you discover items. It was a normal stat displayed on your character screen in _Dark Souls_ that was adjusted due to different factors like items you wore and whether you were human or hollow. In Dark Souls 2, the amount of item discovery you have is hidden from view, but there are certain items that display that they increase your item discovery. As an aside note, [enemies](/Enemies "Dark Souls 2 Enemies") in Dark Souls 2 will despawn after being killed enough times, unless one joins the [Company of Champions](/Company+of+Champions "Dark Souls 2 Company of Champions").

Update: See full-scale test results [here](/Mechanics+Research "Dark Souls 2 Mechanics Research").

  
The actual amount each item increases item discovery is:  
  
[Prisoner's Hood](/Prisoner's+Hood "Dark Souls 2 Prisoner's Hood") = 10  
[Traveling Merchant Hat](/Traveling+Merchant+Hat "Dark Souls 2 Traveling Merchant Hat") = 25  
[Jester's Cap](/Jester's+Cap "Dark Souls 2 Jester's Cap") = 50  
[Symbol of Avarice](/Symbol+of+Avarice "Dark Souls 2 Symbol of Avarice") = 100 (also increases soul absorption, but you gradually lose health   
(5 per second, can be reduced with the [Ring of Restoration](/Ring+of+Restoration "Dark Souls 2 Ring of Restoration") and Charred Loyce Shields)  
[Prisoner's Tatters](/Prisoner's+Tatters "Dark Souls 2 Prisoner's Tatters") = 15  
[Watchdragon Parma](/Watchdragon+Parma "Dark Souls 2 Watchdragon Parma") = 50 as of patch 1.10   
[Covetous Gold Serpent Ring](/Covetous+Gold+Serpent+Ring "Dark Souls 2 Covetous Gold Serpent Ring") = 50   
Covetous Gold Serpent Ring+1 = 75   
Covetous Gold Serpent Ring+2 = 100   
[Rusted Coin](/Rusted+Coin "Dark Souls 2 Rusted Coin") = 100

Burning [Bonfire Ascetic](/Bonfire+Ascetic "Dark Souls 2 Bonfire Ascetic") will increase item discovery on enemies in that area. The increase begins at +150 for bonfire intensity 2 and caps at +375 for bonfire intensity 8.

  * They all stack. These are just base points that are used in item discovery calculation. They do not represent percent of item discovery increase.
  * So best stack is Symbol of Avarice + Covetous Gold Serpent Ring+2 + Prisoner's Tatters + Watchdragon Parma + Rusted Coin + Bonfire Intensity 8 = 740.
  * Nearly all enemies in game (except bosses, and also known - hollows in Things Betwixt) can have up to 10 possible drop items. It looks like item discovery only affects whether you will get a drop or not. The higher your item discovery, the more chance you will get a drop.   
All items have the same rate of drop (no different specified). Just a random number is used to select a drop item from the list of drop items assigned to enemy.
  * If this random number is higher than your item discovery then you don't get any drop at all. The random number can be between 0 and 10000.
  * Total item discovery is calculated as follows in 10 maximum steps (they also equal to drop tiers):
  * Let's call your additional item discovery from equipped items "addition." Formula is tested on Hollow Infantry. If your addition = 100 like from Symbol of Avarice:   
1: 150 + addition +   
2: 150 + addition +   
3: 150 + addition +   
4: 150 + addition +   
5: 150 + addition +   
6: 150 + addition +   
7: 700 + addition +   
8: 500 + addition,  
then you will get 2900 in total.
  * If your addition is 265 (all from items) then you will get 4220.   
Sometimes it is:   
1: 150 + addition +   
2: 150 + addition +   
3: 150 + addition +   
4: 150 + addition +   
5: 100 + addition +   
6: 400 + addition +   
7: 100 + addition, and so on.
  * It seems that the formula is based on the enemy you kill. If enemy drop rate should be more rare then formula addition steps are lowered and base numbers at the end are lowered too. But your "addition" is always the same as you have from equipped items.   
Now let's say your random number generated as 1000.   
Then (150 + 100) + (150 + 100) + (150 + 100) + (150 + 100) = 1000   
Once sum of tiers becomes higher or equal to random number then addition stops. And you get the index of your drop that can be from 0 to 9 (10 total).   
In our example you will get 3 (+1 +1 +1 then stop before 4th +1).   
Index 3 is 4th item in drop items list (counting from 0).   
If it is first Infantry in the [Forest of Fallen Giants](/Forest+of+Fallen+Giants "Dark Souls 2 Forest of Fallen Giants") that has these drops:   
Hollow Infantry Helm   
Hollow Infantry Armor   
Hollow Infantry Gloves   
Hollow Infantry Boots   
Bandit's Knife   
Lifegem   
Throwing Knife   
then you will get Hollow Infantry Boots as drop.
  * Some items will only be dropped by an enemy once. For example if you kill a falconer and it drops the falconer gloves that falconer will never drop the falconer gloves again until you enter a new NG cycle either by beating the game or using a [Bonfire Ascetic](/Bonfire+Ascetic "Dark Souls 2 Bonfire Ascetic"). This will increase the drop rate of the other items when killing this individual falconer.
  * Soul memory and currently collected souls do not affect item discovery calculation / drop. Human/hollow form does not affect item discovery.