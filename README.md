# UPE-Intern-Project

## Sudoku, for ZOOMERS!

### How was it put together?

The actual 'soduku' part of it was coded w/o AI and used traditional googling
It was fun to get to work with lists and data in python in a more rigiourous application, and a game that was pretty much just a big grid was a nice onramp for me

The gimick of 'Zoomer Edition' is that is provides puzzles that are solved using 'naked' singles, and harder modes use 'hidden' singles as well. This is to work with how the puzzles are made and verified to be solvable. lots of soduks that are valid exist, but to get them to be 'easy' for those who cant guess exponential numbers of tiles it is essential for them to use as little guessing as needed, as each guess introduces myriad paths to travel down. 

So, in making a puzzle the program effectivly goes through the process of randomizing to make a valid sodoku, then removing many of the 81 tiles, then applying the two simple solving methods I set up to try and solve the puzzle from that potentialy solvable board. This makes sure a person can solve it with NO guessing as the computer just does things a casual solver does, but lots of times and a lot stupider. 

this then produces 3 big things: a valid solved board, a valid and casualy achiveable starting board, and a list of moves that fill out the starting config into the solved board. Uniqueness of solutions for a board is complex, and much harder to prove without exhaustive checking, so instead of trying to do this for a board the program instead just assumes the solver will go along with the solved board and to check moves the player makes it just references this board without dynamicly recalculating the solvability of a boardstate everytime a number is placed. This is for sure somthing to work on, but I found it a bit much and moved on. 

### But how does one ZOOMER?

To layer onto the ZOOMER aspect of this sodoku edition I was inspired when i saw someone swap between reels and the nyt sodoku whilst on the T, and this moved me to integrate various bright colors and agregious animation to the process of solving.

In addition to this the helper features that are present are desinged to teach the patterns that help one solve sodoku's quickly and efficently -- you may even feel yourself thinking very much like the algorithims used to curate these move suggestions after enough time spent with them. 

I found it really fun beating the hints to the answers, and it makes the process of racing against your own capabilitys far more engaging then what a sodoku for uncs could possibly provide. 

### Conclusions

Is this a mirrorhouse distortion of what should be a relaxing and intelectual game?
oh for SURE

Did anyone need this?
literaly ZERO people ever

Does this handle sodoku making / solving efficently or particuarly effectivly? 
no, but it handles it in a way i figured out enought to crawl over the finishline 

ok thanks have fun!
