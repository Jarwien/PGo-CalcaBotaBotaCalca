## **For support, development, shenanigans: check out the [Discord](https://discord.gg/skUAWKg).**


# Description
This is a small script which uses adb to send touch and key events to your phone, in combination with Calcy IV it can automatically rename all of your pokémon. This script doesn't login to the pokémon go servers using the "unofficial API" and only relies on an Android phone (sorry, iPhone users). The upside to this is that you're very unlikely to get banned for using it. The downside is that it's a lot slower, and that you can't use your phone while it's running.

## Warnings
This script essentially blindly sends touch events to your phone. If a popup appears over where the script thinks a button is, or if your phone lags, it can do unintended things. Please keep an eye on your phone while it is running. If it transfers your shiny 100% dragonite, it's because you weren't watching it.

# Usage
- Download the files from this repository
- Install adb, make sure it's on your systems PATH, alternatively you can place adb in the same folder as main.py
- Install [clipper](https://github.com/majido/clipper) and start the service
- Install Python >=3.7 (older versions will not work)
- Run `pip install -r requirements.txt`
- Change your Calcy IV renaming scheme to `$IV%Range$$MoveTypes$$AttIV$$DefIV$$HpIV$$Appraised$` or if you're used to regular expressions, change your `iv_regexes` setting to match your renaming scheme.
    - Alternatively, if you want to keep your renaming string without too much fuss, check [question 5](#user-content-now-a-decent-faq) in the FAQ.
- Copy or rename `config.example.yaml` to `config.yaml`.
- Edit config.yaml locations for your phone
    - The defaults are for a Oneplus 3T and should work with any 1080p phone that does not have soft buttons.
    - Each setting is an X,Y location. You can turn on Settings > Developer options > Pointer location to assist you in gathering X,Y locations or run the code on [question 1](#user-content-now-a-decent-faq) in the FAQ.
    - Each location setting has a corresponding screenshot in [docs/locations](docs/locations).
- Once you've done all that, run `python ivcheck.py`

## Rulesets and actions
Actions allow you to define new ways of renaming your pokémon, outside of the usual Calcy IV renaming scheme. Actions are processed from first to last, and the first one to have all its conditions pass is used.

**Conditions:**
- **name**: The pokémon name.
- **iv**: The exact IV

    _Note: this will only be set if Calcy IV has discovered an exact IV. Use `iv_avg` for a solution._

- **iv_avg**: The average between `iv_min` and `iv_max` below.

    _Note: This is not the true average, Calcy is a bit smarter, but it works._

- **iv_min**: The minimum possible IV.

    _This will be set even if Calcy IV pulls an exact IV_

- **iv_max**: The maximum possible IV.

    _This will be set even if Calcy IV pulls an exact IV_

- **success**: Whether the calcy IV scan succeeded `[true / false]`.

    _Note: Will be false if pokémon is blacklisted_

- **blacklist**: Whether the pokémon is in the blacklist `[true / false]`.
- **appraised**: Whether the pokémon has been appraised or not `[true / false]`.
- **id**: The pokémon pokedex ID.
- **cp**: The pokémon CP.
- **max_hp**: The pokémon max hp.
- **dust_cost**: The dust cost to power up.
- **level**: The pokémon level `[1-40]`
- **fast_move**: The pokémon fast move.

    _Usually only visible on fully evolved pokémon_

- **special_move**: The pokémon special/charged move.

    _Usually only visible on fully evolved pokémon_

- **gender**: The pokémon gender `[1 = male / 2 = female]`.

_Conditions also support the following operators:_

- **lt**: Less than
- **le**: Less than or equal to
- **eq**: Equal to
- **ne**: Not equal to
- **ge**: Greater than or equal to
- **gt**: Greater than
- **in**: In list
- **not_in**: Not in list

**Actions:**

- `rename: "string"`

    Allows you to specify your own name for the pokémon.

    - The `{calcy}` variable uses the renaming scheme you defined on CalcyIV.

    - In addition, you can use any of the above conditions as variables, for example `{name} {iv}`.

- `favorite:`

    Favorite the pokémon

- `appraise:`

    Appraise the pokémon

### Ruleset examples

**Check [docs/actions](docs/actions) for fully featured examples. Also, check [ACTIONS.md](docs/actions/ACTIONS.md) for a sorting table of special characters, for those who'd like to sort by A-Z in a custom order.**

1. Faster rename run by skipping rename on pokémon with <90% IVs. Rename any pokémon that failed to scan as ".FAILED" so you know which ones failed to scan, and which ones are skipped as trash.
    ```yaml
    actions:
      - conditions:
          success: false
        actions:
          rename: ".FAILED"
      - conditions:
          iv_max__ge: 90
        actions:
          rename: "{calcy}"
    ```

2. Rename bad IV Abra, Gastly and Machop to ".TRADE" so you can trade them later.
    ```yaml
        - conditions:
            name__in:
              - Abra
              - Gastly
              - Machop
            iv_max__lt: 90
          actions:
            rename: ".TRADE"
    ```

3. Rename babies pokémons with a custom syntax, bypassing Calcy's renaming scheme. A 78IV Magby would become "♥ Magby78".
    ```yaml
    - conditions:
        name__in:
          - Pichu
          - Togepi
          - Igglybuff
          - Cleffa
          - Elekid
          - Smoochum
          - Magby
          - Budew
          - Wynaut
          - Tyrogue
          - Azurill
      actions:
        rename: "♥ {name}{iv_avg}"
    ```

# _(now, a decent)_ FAQ
1. It taps in the wrong locations / doesn't work / automatically called my mother:

    You probably need to edit the `locations:` in config.yaml, the defaults are for a 1080p phone. **You can find where the spots are supposed to be in [docs/locations](docs/locations)!**

    To find out the coordinates, enable *Pointer Location* in your phone's *Developer Settings*. If you're lazy like me, just type the code below with your phone connected:

    - To enable:
        ```bash
        adb shell content insert --uri content://settings/system --bind name:s:pointer_location --bind value:i:1
            # If that doesn't work, use this:
        adb shell settings put system pointer_location 1
        ```

    - To disable
        ```bash
        adb shell content insert --uri content://settings/system --bind name:s:pointer_location --bind value:i:0
            # If that doesn't work, use this:
        adb shell settings put system pointer_location 0
        ```

2. It's not pasting the pokémon's name!!1one

    Unfortunately, the paste key event doesn't work on older versions of Android. Use the `--nopaste` argument to paste it by tapping (make sure you edit the `locations:` accordingly).

3. It's going too fast for my phone! :O

    This is being developed and tested on a OnePlus 3T and a Google Pixel, so the script runs quite fast _(until the phone gets hot, that is)_. You can slow it down by increasing the `waits:` in config.yaml.

4. Can it do multiple phones at the same time?

    Sure, you just have to run multiple instances. Run `adb devices` to get the device ids for your phones, then run multiple instances of the script with --device_id=XXXXX

5. _I don't even know what a regular expression is!_ How can I keep my Calcy string *and* use the script, without needing to ask for help on the [Discord](https://discord.gg/skUAWKg)?

    **TL;DR: there's a GIF below, run the command from step 4 and follow the image.**

    There's a neat trick in which you add a lot of spaces to the end of Calcy's string followed by `IV%Range$`. This make it so whenever you paste the pokémon's name in the game, you don't see anything after the spacesbecause of 12-char limitation. If you want to try it out, do as follow:

    1. Connect your phone to your computer (check with `adb devices`)

    2. Make sure `clipper` service is running on your phone (check with `adb shell am broadcast -a clipper.get`)

    3. Open CalcyIV, go to the *Renaming* section and put the cursor at the end of your string.

    4. Run the following commands (if the latter doesn't work, just _'paste'_ on your device manually):
        ```bash
        adb shell am broadcast -a clipper.set -e text $'\u2003\u2003\u2003\u2003\u2003'
        adb shell input keyevent KEYCODE_PASTE
        ```

    6. Add **IV% RANGE** after the spaces. Repeat the process for the *Not fully evolved:* section as well.

    7. Change your `iv_regexes:` to the following:
        ```yaml
        iv_regexes:
            - ^.+  +(?P<iv>\d+)$
            - ^.+  +(?P<iv_min>\d+)\-(?P<iv_max>\d+)$
        ```

    8. Done! Oh no, wait, there's that GIF! :)

        ![](docs/tutorial_spaces.gif?raw=true)