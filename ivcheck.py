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

import pokemonlib
import argparse
import subprocess

skip_count = 0

parser = argparse.ArgumentParser(description='Pokemon go renamer')
parser.add_argument('--device-id', type=str, default=None,
                    help="Optional, if not specified the phone is automatically detected. Useful only if you have multiple phones connected. Use adb devices to get a list of ids.")
parser.add_argument('--adb-path', type=str, default="adb",
                    help="If adb isn't on your PATH, use this option to specify the location of adb.")
parser.add_argument('--nopaste', action='store-const', const=True, default=False,
                    help="Use this switch if your device doesn't support the paste key, for example if you're using a Samsung (Requires Clipper).")
parser.add_argument('--norename', action='store-const', const=True, default=False,
                    help="Don't rename, useful for just loading every pokemon into calcy IV history for CSV export.")
parser.add_argument('--wait-after-error', action='store-const', const=True, default=False,
                    help="Upon calcy IV error, wait for user input.")
parser.add_argument('--max-retries', type=int, default=5,
                    help="Maximum retries, set to 0 for unlimited.")
parser.add_argument('--stop-after', type=int, default=None,
                    help="Stop after this many pokemon.")
parser.add_argument('--sleep-short', type=float, default=0.2,
                    help="Sleep duration for shorter pauses.")
parser.add_argument('--sleep-long', type=float, default=1.3,
                    help="Sleep duration for longer pauses.")
parser.add_argument('--sleep-super-long', type=float, default=2.1,
                    help="Sleep duration for super long pauses.")
parser.add_argument('--name-line-x', type=float, default=50.74,
                    help="X coordinate (in %) of name edit button position.")
parser.add_argument('--name-line-y', type=float, default=47.97,
                    help="Y coordinate (in %) of name edit button position.")
parser.add_argument('--ok-button-x', type=float, default=86.46,
                    help="X coordinate (in %) of OK button position for keyboard input.")
parser.add_argument('--ok-button-y', type=float, default=57.08,
                    help="Y coordinate (in %) of OK button position for keyboard input.")
parser.add_argument('--save-button-x', type=float, default=51.48,
                    help="X coordinate (in %) of OK button position to name change dialog.")
parser.add_argument('--save-button-y', type=float, default=55.47,
                    help="Y coordinate (in %) of OK button position to name change dialog.")
args = parser.parse_args()

p = pokemonlib.PokemonGo(args.device_id)
n = 0


def check_calcy_logcat(p):
    calcyLogcat = p.get_last_logcat()

    if not calcyLogcat:
        print('Something weird went on! I can\'t get the logcat output from CalcyIV!')
        print('Are you sure you\'re running CalcyIV?')
        raise pokemonlib.CalcyIVNotRunning

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
                elif "Pidgey" in line:
                    print("This is a Pidgey... Whatevs...")
                    subprocess.run(["adb", "-s", p.device_id, "shell", "am", "broadcast", "-a", "clipper.set", "-e", "text", "∞\ Pidgey"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                print(line)
                print("Everything seems ok! Renaming pokémon...")
                return True

    print("###############################################################################")
    print("Cool! We have a new error message. Check it below and send it to the developer:")
    for line in calcyLogcat:
        print('Log: ' + str(calcyLogcat))
    print("###############################################################################")
    raise pokemonlib.CalcyIVError


while args.stop_after is None or n < args.stop_after:
    if args.use_intents:
        print("Sending check signal to CalcyIV...")
        p.send_intent("tesmath.calcy.ACTION_ANALYZE_SCREEN", "tesmath.calcy/.IntentReceiver", args.sleep_long)

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
            p.tap(97.22, 20.31, args.sleep_super_long)
            skip_count = 0
            continue
        print("Attempt nº " + str(skip_count) + ". Trying again...")
        continue

    if not args.no_rename:
        # p.tap(54.91, 69.53, args.sleep_short)  # Dismiss Calcy IV
        p.tap(args.name_line_x, args.name_line_y, args.sleep_short)  # Rename
        if args.nopaste:
            p.tap(args.edit_box_x, args.edit_box_y, args.sleep_short)  # Press in the edit box
            p.swipe(args.edit_line_x, args.edit_line_y, args.edit_line_x, args.edit_line_y, args.sleep_short, 600)  # Use swipe to simulate a long press to bring up copy/paste dialog
            p.tap(args.paste_button_x, args.paste_button_y, args.sleep_short)  # Press paste
            p.tap(args.ok_button_x, args.ok_button_y, args.sleep_short)  # Press OK on edit line
        else:
            p.key('KEYCODE_PASTE KEYCODE_TAB KEYCODE_ENTER', args.sleep_short)  # Paste into rename
            # p.key('', args.sleep_short)  # Press tab
            # p.key('', args.sleep_short)  # Press enter

        p.tap(args.save_button_x, args.save_button_y, args.sleep_long)  # Press OK on Pokemon go rename dialog

    n = n + 1
    p.tap(97.22, 20.31, args.sleep_super_long)  # Tap to next pokemon

