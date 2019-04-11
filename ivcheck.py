#!/usr/bin/env python3.7
import argparse
import asyncio
import logging
import operator
import os.path
import re
from sys import platform

import yaml
from colorlog import ColoredFormatter

from pokemonlib import PokemonGo


def in_func(a, b):
    return a in b

def not_in_func(a, b):
    return a not in b

ops = {
    'lt': operator.lt,
    'le': operator.le,
    'eq': operator.eq,
    'ne': operator.ne,
    'ge': operator.ge,
    'gt': operator.gt,
    'in': in_func,
    'not_in': not_in_func,
}

logger = logging.getLogger('ivcheck')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = ColoredFormatter('%(log_color)s[%(asctime)s] %(log_color)s%(levelname)-8s%(reset)s | %(log_color)s%(message)s%(reset)s', datefmt='%I:%M:%S %p')
ch.setFormatter(formatter)
logger.addHandler(ch)

RE_CALCY_IV = re.compile(r"^.\/MainService\(\s*\d+\): Received values: Id: -{0,1}\d+ {0,1}\({0,1}(?P<name>[^\(\)]+){0,1}\){0,1}, Nr: (?P<id>-{0,1}\d+), CP: (?P<cp>-{0,1}\d+), Max HP: (?P<max_hp>-{0,1}\d+), Dust cost: (?P<dust_cost>-{0,1}\d+), Level: (?P<level>\-{0,1}[\d\.]+), FastMove (?P<fast_move>.+), SpecialMove (?P<special_move>.+), SpecialMove2 (?P<special_move2>.+),Gender (?P<gender>\-{0,1}\d+), catchYear (?P<catch_year>.+), Level-up (true|false):$")
RE_RED_BAR = re.compile(r"^.+\(\s*\d+\): Screenshot #\d has red error box at the top of the screen$")
RE_SUCCESS = re.compile(r"^.+\(\s*\d+\): calculateScanOutputData finished after \d+ms$")
RE_SCAN_INVALID = re.compile(r"^.+\(\s*\d+\): Scan invalid.+$")
RE_SCAN_TOO_SOON = re.compile(r"^.+\(\s*\d+\): Detected power-up screen$")

NAME_MAX_LEN = 12

NUMBER_SETS = [
    [chr(9450)] + [chr(i) for i in range(9312, 9332)] + [chr(i) for i in range(12881, 12896)] + [chr(i) for i in range(12977, 12992)],  # white circled digits "⓪"
    [chr(9471)] + [chr(i) for i in range(10102, 10112)] + [chr(i) for i in range(9451, 9461)],  # blank circled digits "⓿"
    [chr(8304)] + [chr(185)] + [chr(178)] + [chr(179)] + [chr(i) for i in range(8308, 8314)],  # superscripted digits: "    "
    [chr(i) for i in range(8320, 8329)],  # subscripted digits: "₁"
    [chr(i) for i in range(48, 58)] + [chr(i) for i in range(65, 71)]  # hexadecimal *digits* (yes, they are digits.)
]

CALCY_STRING = '\xa0'*NAME_MAX_LEN + '$CatchDate$|$Lucky$|$ATT$|$DEF$|$HP$|$Gender$|$Trade$|$IV%Min$|$IV%Max$|$AttIV$|$DefIV$|$HpIV$|$FaMove$|$SpMove$|$Appraised$|$Legacy$'

def gender_filter(c):
    if c == chr(9794):
        return 'M'
    elif c == chr(9792):
        return 'F'
    return 'U'

def int_filter(c):
    try:
        return int(c)
    except ValueError:
        pass
    for number_set in NUMBER_SETS:
        try:
            chars = [number_set.index(char) for char in c]
        except ValueError:
            pass
        else:
            return int(''.join(map(str, chars)))
    raise ValueError('Unrecognised number format %s', c)

def bool_filter(c):
    if c:
        return True
    return False

CALCY_VARIABLES = [
    ['catch_year', None],
    ['lucky', bool_filter],
    ['attack', int_filter],
    ['defense', int_filter],
    ['hp', int_filter],
    ['gender', gender_filter],
    ['trade', bool_filter],
    ['iv_min', int_filter],
    ['iv_max', int_filter],
    ['attack_iv', int_filter],
    ['defense_iv', int_filter],
    ['hp_iv', int_filter],
    ['fast_move', None],
    ['charge_move', None],
    ['appraised', bool_filter],
    ['legacy', bool_filter],
]

CALCY_SUCCESS = 0
CALCY_RED_BAR = 1
CALCY_SCAN_INVALID = 2
CALCY_SCAN_TOO_SOON = 3

class Loader(yaml.SafeLoader):
    def __init__(self, stream):
        self._root = os.path.split(stream.name)[0]
        super(Loader, self).__init__(stream)

    def include(self, node):
        filename = os.path.join(self._root, self.construct_scalar(node))
        with open(filename, 'r') as f:
            return yaml.load(f, Loader)

Loader.add_constructor('!include', Loader.include)

class Main:
    def __init__(self, args):
        self.args = args
        self.use_fallback_screenshots = False

    async def hue_affinity(self, im, hue1, hue2):
        '''Checks the affinity, in percentual terms,
        of the average median im hue against hue1 and
        hue2.

        Input values are in range 0-255, instead of
        the common 0-360° used for HSL and HSV images.

        Arguments:
            image {Image}   -- PIL.Image
            hue1  {int}     -- 0-255
            hue2  {int}     -- 0-255

        Returns:
            {tuple}   -- A tuple containing the relative
                         percentages lenghts of the arcs
                         between im's median hue against
                         hue1 and hue2, respectively.
        '''
        ## Image filtering mumbojumbo
        im = im.quantize()
        im = im.resize((1, 1))
        im = im.convert('HSV')
        pixel = im.getpixel((0, 0))

        ## Gets us one only int, the average hue of the image
        hue = pixel[0]

        ## The Angles
        # The modulus makes it a polar function, i.e.:
        # everything that overflows or underflows 255
        # becomes the difference, so we don't need to
        # translate values nor calculate distances :)
        a1 = abs(hue-hue1) % 255
        a2 = abs(hue-hue2) % 255

        # This is just for giggles
        confidence = (1 - (min(a1, a2) / max(a1, a2))) * 100

        logger.info('Detected H: %s (%i%% of H1: %s | %i%% of H2: %s) with a confidence of %i%%', hue, a1, hue1, a2, hue2, confidence)

        if a1 < a2:
            return True
            # return ((((a1 + hue) / hue) - 1) * 100, (((a2 + hue) / hue) - 1) * 100)
        if a2 < a1:
            return False
            # return ((((a1 + hue) / hue) - 1) * 100, (((a2 + hue) / hue) - 1) * 100)
        raise Exception("Well you got unlucky boy, it's right on the middle")

    async def tap(self, location):
        await self.p.tap(*self.config['locations'][location])
        if location in self.config['waits']:
            logger.info('Waiting ' + str(self.config['waits'][location]) + ' seconds after ' + str(self.config['locations'][location]) + '...')
            await asyncio.sleep(self.config['waits'][location])

    async def tap_and_hold(self, location, duration):
        await self.p.swipe(
            self.config['locations'][location][0],
            self.config['locations'][location][1],
            self.config['locations'][location][0],
            self.config['locations'][location][1],
            duration
        )
        if location in self.config['waits']:
            logger.info('Waiting ' + str(self.config['waits'][location]) + ' seconds after ' + str(self.config['locations'][location]) + '...')
            await asyncio.sleep(self.config['waits'][location])

    async def swipe(self, location, duration):
        await self.p.swipe(
            self.config['locations'][location][0],
            self.config['locations'][location][1],
            self.config['locations'][location][2],
            self.config['locations'][location][3],
            duration
        )
        if location in self.config['waits']:
            logger.info('Waiting ' + str(self.config['waits'][location]) + ' seconds after ' + str(self.config['locations'][location]) + '...')
            await asyncio.sleep(self.config['waits'][location])

    async def setup(self):
        self.p = PokemonGo()
        if self.args.device_id is None:
            await self.p.get_device()
        else:
            await self.p.set_device(self.args.device_id)
        if self.args.copy_calcy:
            await self.p.send_intent("clipper.set", extra_values=[["text", CALCY_STRING]])
            return False

        path = "config.yaml"
        device_path = await self.p.get_device()+".yaml"
        if self.args.config is None and os.path.exists(device_path):
            path = device_path
        elif self.args.config is not None:
            path = self.args.config

        with open(path, "r") as f:
            self.config = yaml.load(f, Loader)
        await self.p.start_logcat()

    async def start(self):
        if await self.setup() is False:
            return
        count = 0
        num_errors = 0
        while True:
            # This loop also needs refactoring
            blacklist = False
            state, values = await self.check_pokemon()

            if values and values["name"] in self.config["blacklist"]:
                blacklist = True
            elif state == CALCY_SUCCESS:
                num_errors = 0
            elif state == CALCY_RED_BAR:
                continue
            elif state == CALCY_SCAN_TOO_SOON:
                num_errors += 1  # uses the same variable as CALCY_SCAN_INVALID, as they'll never happen simultaneously
                if num_errors < args.max_retries:
                    logger.warning("Waiting three seconds and trying again (attempt #%s)", num_errors)
                    await asyncio.sleep(3)
                    continue
                logger.warning("Failed %s times in a row, trying to close a potencially stuck rename dialog...", num_errors)
                num_errors = 0
                await self.tap('rename_ok')
                continue
            elif state == CALCY_SCAN_INVALID:
                num_errors += 1
                if num_errors < args.max_retries:
                    await asyncio.sleep(0.1)  # waits a bit between each scan, otherwise goes too fast
                                        # sometimes the pokemon takes around a second to make the arc-level visible
                    continue
                num_errors = 0

            values["success"] = True if state == CALCY_SUCCESS and blacklist is False else False
            values["blacklist"] = blacklist
            try:
                # This try/except should go somehow on the if block above probably
                values["appraised"] = True if values["appraised"] is True else False
            except KeyError:
                values["appraised"] = False

            actions = await self.get_actions(values)

            if "appraise" in actions:
                await self.tap("pokemon_menu_button")
                await self.tap("appraise_button")
                await self.p.send_intent("tesmath.calcy.ACTION_ANALYZE_SCREEN", "tesmath.calcy/.IntentReceiver", [["silentMode", True], ["--user", self.args.user]])
                for _ in range(0, 4):  # we can do it four times before beggining to screencap
                    await self.tap("continue_appraisal")
                while await self.check_appraising():
                    await self.tap("continue_appraisal")
                await self.tap("calcy_appraisal_save_button")
                values["appraised"] = True
                clipboard, clipboard_values = await self.get_data_from_clipboard()
                values = {**values, **clipboard_values}
                values["calcy"] = clipboard
                actions = await self.get_actions(values)
                await self.tap("dismiss_calcy")

            if "get_moves" in actions:
                # If calcyiv already has both moves, then skip this action
                if values['fast_move'] == '' or values['charge_move'] == '' or values['fast_move'] == 'err' or values['charge_move'] == 'err':
                    logger.warning("Scrolling down...")
                    await self.swipe('scroll_to_moves', 500)
                    moves_state, moves_values = await self.check_pokemon()
                    if 'calcy' in moves_values:
                        values['calcy'] = moves_values['calcy']
                    logger.warning("Scrolling up again...")
                    await self.swipe('scroll_to_top', 500)

            if "rename" in actions:
                if values["success"] is False:
                    await self.tap('close_calcy_dialog')  # it gets in the way
                await self.tap('rename')
                if actions.get("rename", "{calcy}") != "{calcy}": # Don't bother setting clipboard if we don't need to change it
                    await self.p.send_intent("clipper.set", extra_values=[["text", actions["rename"].format(**values)]])

                if args.touch_paste:
                    await self.tap_and_hold('edit_box', 600)
                    await self.tap('paste')
                else:
                    await self.p.key('KEYCODE_PASTE')  # Paste into rename
                await self.p.key('KEYCODE_TAB')
                await self.p.key('KEYCODE_ENTER')
                await self.tap('rename_ok')

            if "favorite" in actions:
                if not await self.check_favorite():
                    logger.info('Favoriting pokemon...')
                    await self.tap('favorite_button')
            count += 1
            if args.stop_after is not None and count >= args.stop_after:
                logger.info("Stop_after reached, stopping")
                return
            await self.tap('next')


    async def get_data_from_clipboard(self):
        clipboard = await self.p.get_clipboard()
        logger.debug('Device clipboard is: %s', clipboard)

        try:
            calcy, data = clipboard.split('\xa0'*NAME_MAX_LEN)
        except ValueError:
            logger.error('Received clipboard data that does not contain 12 non-breaking spaces, did you run --copy-calcy and paste onto the end of your calcy rename settings? Clipboard data follows')
            logger.error(repr(clipboard))
            raise
        data = data.split('|')
        values = {}
        for i, item in enumerate(CALCY_VARIABLES):
            name, function = item
            if function is None:
                values[name] = data[i]
            else:
                values[name] = function(data[i])
        values['iv_avg'] = int((values['iv_min'] + values['iv_max']) / 2)
        values['iv'] = values['iv_min'] if values['iv_min'] == values['iv_max'] else None

        return calcy, values

    async def check_appraising(self):
        """
        Not the best check, just search the area
        for white pixels
        """
        screencap = await self.p.screencap()
        crop = screencap.crop(self.config['locations']['appraisal_box'])
        rgb_im = crop.convert('RGB')
        width, height = rgb_im.size
        colors = [(255, 255, 255)]

        color_count = 0
        for x in range(1, width):
            for y in range(1, height):
                c = rgb_im.getpixel((x, y))
                if c in colors:
                    color_count += 1
        return color_count > 100000


    async def check_favorite(self):
        """Searches the favorite_button_box area for
        yellow pixels, and returns True if more than
        40% of the pixels are indeed yellow. Also, if
        the first check results in 0%, it checks twice,
        in case some pokémon might have covered the
        favorite button.

        Returns:
            bool -- True if pokémon was already favorited, False otherwise
        """

        ratio = None
        for _ in range(0, 2):
            screencap = await self.p.screencap()
            crop = screencap.crop(self.config['locations']['favorite_button_box'])
            rgb_im = crop.convert('RGB')
            width, height = rgb_im.size
            colors = [
                (244, 192, 13),
                (239, 182, 8),
                (246, 193, 14),
                (240, 184, 9),
                (248, 198, 16),
                (241, 184, 10),
                (243, 188, 11),
                (244, 191, 13),
                (242, 188, 11),
                (242, 186, 10),
                (243, 189, 11),
                (244, 191, 12),
                (243, 189, 12),
                (241, 186, 10),
                (247, 197, 15),
                (247, 196, 15),
                (244, 190, 12),
                (245, 193, 13),
                (246, 194, 14),
                (246, 195, 14),
                (241, 185, 10),
                (240, 183, 9),
                (242, 187, 11),
                (245, 192, 13),
            ]
            color_count = 0
            total_count = 0
            for x in range(1, width):
                for y in range(1, height):
                    c = rgb_im.getpixel((x, y))
                    if c in colors:
                        color_count += 1
                    total_count += 1

            ratio = color_count / total_count
            if color_count != 0:
                break

        logger.debug('Found %s yellow pixels from a total of %s pixels (%i%%).', color_count, total_count, 100 * ratio)
        return ratio > 0.4

    async def get_actions(self, values):
        for ruleset in self.config["actions"]:
            conditions = ruleset.get("conditions", {})
            # Check if we need to read the clipboard
            passed = True
            for key, item in conditions.items():
                operator = None
                if "__" in key:
                    key, operator = key.split("__")

                if isinstance(values[key], str):
                    if values[key].isnumeric():
                        values[key] = int(values[key])
                    else:
                        try:
                            values[key] = float(values[key])
                        except ValueError:
                            pass

                if key not in values:
                    passed = False
                    break
                if operator is not None:
                    if operator not in ops:
                        raise Exception("Unknown operator {}".format(operator))
                    operation = ops.get(operator)
                    if not operation(values[key], item):
                        passed = False
                        break
                elif values[key] != conditions[key]:
                    passed = False
                    break
            if passed:
                logger.debug('Condition matched against ' + str(ruleset.get("conditions", {})))
                return ruleset.get("actions", {})
        return {}

    async def check_pokemon(self):
        await self.p.send_intent("tesmath.calcy.ACTION_ANALYZE_SCREEN", "tesmath.calcy/.IntentReceiver", [["silentMode", True], ["--user", self.args.user]])
        red_bar = False
        values = {}
        while True:
            # TODO: This block's logic is not trivial, maybe a refactoring would help
            line = await self.p.read_logcat()
            if args.verbose:
                logger.debug("logcat line received: %s", line)

            match = RE_CALCY_IV.match(line)
            if match:
                values = match.groupdict()
                state = CALCY_SUCCESS
                if values["name"] == 'err':
                    logger.error("Got 'err' as name, we're probably going too fast. If you get this error often, try raising 'waits -> rename_ok' in config.yaml")
                    return CALCY_SCAN_TOO_SOON, values
                elif values["cp"] == "-1" or values["level"] == "-1.0":
                    logger.error("Couldnt detect CP (got %s) or arc-level (got %s)", values["cp"], values["level"])
                elif red_bar is True:
                    logger.error("RE_CALCY_IV matched and red_bar is True")
                    state = CALCY_RED_BAR
                    return state, values
                else:
                    clipboard, clipboard_values = await self.get_data_from_clipboard()
                    values = {**values, **clipboard_values}
                    values["calcy"] = clipboard
                    logger.warning(values)
                    return state, values

            match = RE_RED_BAR.match(line)
            if match:
                logger.error("RE_RED_BAR matched")
                red_bar = True

            match = RE_SCAN_INVALID.match(line)
            if match:
                if red_bar:
                    logger.error("RE_SCAN_INVALID matched and red_bar is True")
                    return CALCY_RED_BAR, values
                logger.error("RE_SCAN_INVALID matched, raising CalcyIVError")
                return CALCY_SCAN_INVALID, values

            match = RE_SCAN_TOO_SOON.match(line)
            if match:
                values = None
                logger.error("RE_SCAN_TOO_SOON matched, we're probably going too fast. If you get this error often, try raising 'waits -> rename_ok' in config.yaml")
                return CALCY_SCAN_TOO_SOON, values


if __name__ == '__main__':
    if platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    parser = argparse.ArgumentParser(description='Pokemon go renamer')
    parser.add_argument('--device-id', type=str, default=None,
                        help='Optional, if not specified the phone is automatically detected. Useful only if you have multiple phones connected. Use adb devices to get a list of ids.')
    parser.add_argument('--max-retries', type=int, default=5,
                        help='Maximum retries, set to 0 for unlimited.')
    parser.add_argument('--config', type=str, default=None,
                        help='Config file location.')
    parser.add_argument('--touch-paste', default=False, action='store_true',
                        help='Use touch instead of keyevent for paste.')
    parser.add_argument('--user', type=int, default=0,
                        help='Use a cloned CalcyIV from a different phone user. Useful for sandboxing apps like Island, where you could run two instances simultaneously.')
    parser.add_argument('--pid-name', default=None, type=str,
                        help='Create pid file')
    parser.add_argument('--pid-dir', default=None, type=str,
                        help='Change default pid directory')
    parser.add_argument('--stop-after', default=None, type=int,
                        help='Stop after X pokemon')
    parser.add_argument('--copy-calcy', default=False, action='store_true',
                        help='Copy calcy IV renaming string')
    parser.add_argument('--verbose', '-v', default=False, action='store_true',
                        help='Enables dumping of the device logcat. Spams quite a lot.')
    args = parser.parse_args()
    if args.pid_name is not None:
        from pid import PidFile
        with PidFile(args.pid_name, args.pid_dir) as p:
            asyncio.run(Main(args).start())
    else:
        asyncio.run(Main(args).start())

