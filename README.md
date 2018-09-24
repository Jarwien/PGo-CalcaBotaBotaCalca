# Calça Bota, a Bota Calça

*This project is a fork of [Azelphur/PokemonGo-CalcyIV-Renamer](https://github.com/Azelphur/PokemonGo-CalcyIV-Renamer).*

## Description
This is a (not so small anymore) script which uses adb, clipper and other stuff to automatically rename your pokémons in Pokémon Go using CalcyIV's renaming feature.

## Usage
1. Open CalcyIV
2. Open Pokémon Go, and go to the first pokémon you'd like to rename. **The script "swipes" forward**, so sort your pokémons in a way that the following pokémons are the one you want to rename (probably A-Z).
3. Clone the repo/download the files, `cd` into the directory and run the main file `ivcheck.py`:

        $ ./ivcheck.py
    or

        $ python ivcheck.py

4. **Watch it!** This is an automated tool that simulates taps and swipes and stuff. **Things COULD go wrong!**

## Problems?
* It's going too fast for my phone
    - This was developed and tested on a Google Pixel. You can slow it down by increasing the `--sleep_short`, `--sleep_long` and `--sleep_super_long` arguments (in seconds), like zo:

            $ ./ivcheck.py --sleep_short=0.4 --sleep_long=2 --sleep_super_long=3
    - When you find a combination that works for you, you can hardcode the arguments by editing the defaults on the file `ivcheck.py`, just Ctrl+F them.

* It's not pasting the pokémon names:
    - In older versions of android, the PASTE keycode doesn't work. Try the `--no-paste` argument, though I have not developed it nor tested it, so it may not work. This will be fixed in the future alongside a complete refactoring of azure's code.