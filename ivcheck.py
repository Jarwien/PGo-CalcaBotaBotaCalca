#!/usr/bin/env python3

## Character Sorting Table
# *This is the order in which PokémonGo displays your pokémon when sorting by name (A-Z}.*

# - `꩜ ` (the special @, does not exist on Gboard)
# - `$`
# - `%`
# - `&`
# - `*`
# - `,`
# - `.`
# - `?`
# - `_`
# - `¡` (alongside `!`)
# - `¿` (alongside `?`)
# - `“` (alongside `"`)
# - `›` (alongside `'`)
# - `+`
# - `‽` (alongside `?`)
# - `⁺` (superscript plus, does not exist on Gboard)
# - `»` (alongside `"`)
# - `÷`
# - `×`
# - `∅` (alingside `0`)
# - `≈` (alongside `=`)
# - `↑` (alingside `^`)
# - `→` (alingside `^`)
# - `↓` (alingside `^`)
# - `←` (alingside `^`)
# - `·` (alongside `-`)
# - `†` (alongside `*`)
# - `‡` (alongside `*`)
# - `•`
# - `★` (alongside `*`)
# - `♠` (alongside `•`)
# - `♦` (alongside `•`)
# - `♣` (alongside `•`)
# - `♥` (alongside `•`)
# - `✓`
# - `‰`
# - `∞` (alongside `=`)

import random
import pokemonlib
import argparse
import subprocess
import time

#############
# ARGUMENTS #
#############
parser = argparse.ArgumentParser(description='Calça a bota, bota a calça!')
parser.add_argument('-d', '--device-id', type=str, default=None,
                    help="Optional, if not specified the phone is automatically detected. Useful only if you have multiple phones connected. Use adb devices to get a list of ids.")
parser.add_argument('--adb-path', type=str, default="adb",
                    help="If adb isn't on your PATH, use this option to specify the location of adb.")
parser.add_argument('-u', '--user', type=str, default=None,
                    help="Specify the user when CalcyIV is running on another use, like when running Island or other sandboxing app.")
parser.add_argument('--no-paste', action='store_const', const=True, default=False,
                    help="Use this switch if your device doesn't support the paste key, for example if you're using a Samsung (Requires Clipper).")
parser.add_argument('--no-rename', action='store_const', const=True, default=False,
                    help="Don't rename, useful for just loading every pokemon into calcy IV history for CSV export.")
parser.add_argument('-w', '--wait-after-error', action='store_const', const=True, default=False,
                    help="Upon calcy IV error, wait for user input.")
parser.add_argument('-m', '--max-retries', type=int, default=5,
                    help="Maximum retries, set to 0 for unlimited.")
parser.add_argument('-s', '--stop-after', type=int, default=None,
                    help="Stop after this many pokemon.")

parser.add_argument('-ss', '--sleep-short', type=float, default=0.2,
                    help="Sleep duration for shorter pauses.")
parser.add_argument('-sl', '--sleep-long', type=float, default=1.3,
                    help="Sleep duration for longer pauses.")
parser.add_argument('-sh', '--sleep-huge', type=float, default=2.3,
                    help="Sleep duration for super long pauses.")

parser.add_argument('--name-line-x', type=float, default=50.74,
                    help="X coordinate (in %%) of name edit button position.")
parser.add_argument('--name-line-y', type=float, default=47.97,
                    help="Y coordinate (in %%) of name edit button position.")

parser.add_argument('--ok-button-x', type=float, default=86.46,
                    help="X coordinate (in %%) of OK button position for keyboard input.")
parser.add_argument('--ok-button-y', type=float, default=57.08,
                    help="Y coordinate (in %%) of OK button position for keyboard input.")

parser.add_argument('--save-button-x', type=float, default=51.48,
                    help="X coordinate (in %%) of OK button position to name change dialog.")
parser.add_argument('--save-button-y', type=float, default=55.47,
                    help="Y coordinate (in %%) of OK button position to name change dialog.")
args = parser.parse_args()


########
# Init #
########
## Initializes PokemonGo object
p = pokemonlib.PokemonGo(args.device_id, args.user)
n = 0
skip_count = 0
evoPokemons = ['Pidgey', 'Caterpie', 'Weedle', 'Wurmple', 'Whismur']


#############
# Functions #
#############
def check_calcy_logcat(p):
    calcyLogcat = p.get_last_logcat()

    if not calcyLogcat:
        calcyLogcat = p.get_last_logcat(2)
        if not calcyLogcat:
            print('I couldn\'t get the logcat output from CalcyIV! Are you sure you\'re running CalcyIV?')
            print('If you\'re sure, try increasing the sleep-huge time from ' + str(args.sleep_huge) + ' to something bigger (in seconds).')
            print('I\'ll do that for you now, but you should change the defaults if this works. I\'m increasing the value by 0.5 seconds.')
            args.sleep_huge = args.sleep_huge + 0.5
            raise pokemonlib.CalcyIVError

    for line in calcyLogcat:
        # print("line: " + line)
        # if line.endswith("has red error box at the top of the screen"):
        #     raise pokemonlib.RedBarError
        if "Scan invalid" in line:
            print("Invalid Scan!")
            raise pokemonlib.CalcyIVError
        elif "Received values: Id: " in line:
            if "-1" in line:
                print("CalcyIV's got an error!")
                raise pokemonlib.CalcyIVError
            else:
                # TODO: add this subprocess.run() as functions inside pokemonlib
                # and check for clipper presence.
                if "Unown" in line:
                    print("This is an Unknown! Using alternate rename scheme...")
                    subprocess.run(["adb", "-s", p.device_id, "shell", "am", "broadcast", "-a", "clipper.set", "-e", "text", "‽\ Unown"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    for pokemon in evoPokemons:
                        if pokemon in line:
                            print("This is a " + pokemon + "... Good for XP! ")
                            subprocess.run(["adb", "-s", p.device_id, "shell", "am", "broadcast", "-a", "clipper.set", "-e", "text", "∞\ " + pokemon], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                print(line)
                print("Everything seems ok! Renaming pokémon...")
                return True

    print("###############################################################################")
    print("Cool! We have a new error message. Check it below and send it to the developer:")
    for line in calcyLogcat:
        print('Log: ' + str(calcyLogcat))
    print("###############################################################################")
    raise pokemonlib.CalcyIVError


#############
# Main Loop #
#############
while args.stop_after is None or n < args.stop_after:
    print("Sending check signal to CalcyIV...")
    p.send_intent("tesmath.calcy.ACTION_ANALYZE_SCREEN", "tesmath.calcy/.IntentReceiver", args.sleep_huge)

    try:
        check_calcy_logcat(p)
        skip_count = 0
    except pokemonlib.RedBarError:
        print("RedBarError, continuing")
        continue
    except pokemonlib.CalcyIVError:
        if args.wait_after_error:
            input("CalcyIVError, Press enter to continue")
        skip_count = skip_count + 1
        if skip_count > args.max_retries and args.max_retries != 0:
            print("CalcyIVError " + str(args.max_retries) + " times in a row, skipping to next pokemon")
            n = n + 1
            p.tap(97.22, 20.31, args.sleep_huge)
            skip_count = 0
            continue

        print("Attempt nº " + str(skip_count + 1) + ". Changing pokémon's angle and trying again...")

        # The following swipes at fixed 26% height (y), from x = [30%-70%, 30-70%], where '30%-70%' is chosen *randomly*.
        # This makes it more probable to get a good angle, but it's probably overkill.
        p.swipe(random.randint(30, 70), 26, random.randint(30, 70), 26, args.sleep_short, 100)
        continue

    if not args.no_rename:
        p.tap(args.name_line_x, args.name_line_y, args.sleep_short)  # Rename
        if args.no_paste:
            p.tap(args.edit_box_x, args.edit_box_y, args.sleep_short)  # Press in the edit box
            p.swipe(args.edit_line_x, args.edit_line_y, args.edit_line_x, args.edit_line_y, args.sleep_short, 600)  # Use swipe to simulate a long press to bring up copy/paste dialog
            p.tap(args.paste_button_x, args.paste_button_y, args.sleep_short)  # Press paste
            p.tap(args.ok_button_x, args.ok_button_y, args.sleep_short)  # Press OK on edit line
        else:
            if p.version_sdk >= 24:
                p.key('KEYCODE_PASTE KEYCODE_TAB KEYCODE_ENTER', args.sleep_short)  # Paste into rename
            else:
                # TODO: check clipper
                clipboard = p.get_clipboard_from_device()
                p.type(clipboard, args.sleep_short)
                # In this case, the PGo OK button is pressed twice, first to leave the system keyboard
                # and then to actually confirm.
                p.tap(args.save_button_x, args.save_button_y, args.sleep_long)
        p.tap(args.save_button_x, args.save_button_y, args.sleep_long)  # Press OK on Pokemon go rename dialog

    n = n + 1
    p.tap(97.22, 20.31, args.sleep_huge)  # Tap to next pokemon

