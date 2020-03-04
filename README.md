# Wanikani CLI Client

This is a program for doing kanji reviews and lessons from the command line.  
It was made for personal use and was not intended to be a publicly used  
utility. The source is freely available to learn from, modify, or to use as is.  

#### Usage
This is a python3 program.  
`$ python3 wanikani_cli.py`  
  
This program expects a file called `token` that contains a Wanikani  API token  
(version 2). You can generate an API token on wanikani.com by clicking on  
Account in the top right corner and then API Tokens. From  here you can  
generate a new token. **NOTE: Required permissions: `reviews:create` and  
`assignments:start`.** Once you generate an API key, paste it into a file  
called `token` in the directory where you execute this program.   

#### Disabling keyboard input kanji prediction
When typing Japanese, the input system by default predicts kanji from the  
hiragana you enter. It is recommended to disable kanji prediction when using  
this program, as it can be used to sort of cheat and find the answer to kanji  
readings. This can be done from System Preferences -> Language & Regions ->  
Keyboard Preferences, under the Input Sources tab, select Japanese and uncheck  
the boxes for Live Conversion and Predictive candidates. 

#### Image only radicals in Wanikani
The Wanikani API has a number of radicals for which it does not return any  
unicode characters. Some of these actually have unicode representations, but  
there are a few that do not have unicode representations at all. To help deal  
with this, there is a lookup table in the file `radicals_lookup.json` that  
contains radicals that have unicode representations not returned by the  
Wanikani API.  

For more info on these radicals see:   
https://community.wanikani.com/t/how-to-type-wanikani-radicals/19311
