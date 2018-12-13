# ../wcs/modules/races/human_alliance/__init__.py

# ============================================================================
# >> IMPORTS
# ============================================================================
# Python Imports
#   Collections
from collections import defaultdict
#   Itertools
from itertools import chain
#   Random
from random import randint

# Source.Python Imports
#   Entities
from entities.constants import MoveType
#   Events
from events import Event
#   Listeners
from listeners.tick import Delay
#   Mathlib
from mathlib import Vector
#   Message
from messages import HudMsg

# WCS Imports
#   Helpers
from ....core.helpers.overwrites import SayText2
#   Modules
from ....core.modules.races.calls import command
from ....core.modules.races.manager import race_manager
#   Players
from ....core.players.entity import Player


# ============================================================================
# >> GLOBAL VARIABLES
# ============================================================================
settings = race_manager.find(__name__)

_delays = defaultdict(list)

invisibility_message = SayText2(settings.strings['invisibility message'])
devotion_aura_message = SayText2(settings.strings['devotion_aura message'])
bash_attacker_message = HudMsg(settings.strings['bash attacker'], y=0.2)
bash_victim_message = HudMsg(settings.strings['bash victim'], y=0.2)
teleport_failed_message = SayText2(settings.strings['teleport failed'])

spawncmd_effect = settings.get_effect_entry('spawncmd')
bash_effect_0 = settings.get_effect_entry('bash_0')
bash_effect_1 = settings.get_effect_entry('bash_1')
teleport_effect_0 = settings.get_effect_entry('teleport_0')
teleport_effect_1 = settings.get_effect_entry('teleport_1')
teleport_effect_2 = settings.get_effect_entry('teleport_2')
teleport_effect_3 = settings.get_effect_entry('teleport_3')


# ============================================================================
# >> RACE CALLBACKS
# ============================================================================
@command
def spawncmd(event, wcsplayer):
    vector = Vector(*wcsplayer.player.origin)

    for (start_radius, end_radius, speed) in ((40, 60, 1), (80, 100, 1), (60, 80, 2)):
        spawncmd_effect.create(center=vector, start_radius=start_radius, end_radius=end_radius, speed=speed)

        vector.z += 12


@command
def disconnectcmd(event, wcsplayer):
    delays = _delays.pop(wcsplayer, None)

    if delays is not None:
        for delay in delays:
            if delay.running:
                delay.cancel()


@command
def on_skill_desc(wcsplayer, skill_name, kwargs):
    config = settings.config['skills'][skill_name]['variables']

    if skill_name == 'invisibility':
        invisible = config['invisible']

        kwargs['min_invisible'] = (255 - invisible[0]) / 255 * 100
        kwargs['max_invisible'] = (255 - invisible[-1]) / 255 * 100
    elif skill_name == 'devotion_aura':
        health = config['health']

        kwargs['min_health'] = health[0]
        kwargs['max_health'] = health[-1]
    elif skill_name == 'bash':
        chance = config['chance']

        kwargs['min_chance'] = chance[0]
        kwargs['max_chance'] = chance[-1]
    elif skill_name == 'teleport':
        range_ = config['range']
        cooldown = settings.config['skills'][skill_name]['cooldown']

        kwargs['min_range'] = range_[0]
        kwargs['max_range'] = range_[-1]
        kwargs['min_cooldown'] = cooldown[0]
        kwargs['max_cooldown'] = cooldown[-1]


# ============================================================================
# >> SKILL CALLBACKS
# ============================================================================
@command(event='player_spawn')
def invisibility(event, wcsplayer, variables):
    wcsplayer.player.color.a = variables['invisible']

    invisibility_message.send(wcsplayer.index)


@command(event='player_spawn')
def devotion_aura(event, wcsplayer, variables):
    wcsplayer.player.health += variables['health']

    devotion_aura_message.send(wcsplayer.index, value=variables['health'])


@command(event='player_attacker')
def bash(event, wcsplayer, variables):
    if randint(0, 100) <= variables['chance']:
        wcsvictim = Player.from_userid(event['userid'])
        stuck = wcsvictim.data.get('stuck', 0)

        if not stuck:
            if not wcsvictim.data.get('noclip'):
                wcsvictim.player.move_type = MoveType.NONE

        wcsvictim.data['stuck'] = stuck + 1

        delay = Delay(1, _reset_bash, (wcsvictim, ))
        delay.args += (delay, )
        _delays[wcsvictim].append(delay)

        bash_attacker_message.send(wcsplayer.index, name=wcsvictim.name)
        bash_victim_message.send(wcsvictim.index, name=wcsplayer.name)

        vector1 = Vector(*wcsplayer.player.origin)
        vector2 = Vector(*wcsvictim.player.origin)

        vector1.z += 20
        vector2.z += 20
        bash_effect_0.create(start_point=vector1, end_point=vector2)

        vector2.z += 5
        bash_effect_1.create(center=vector2)


@command(event='player_ability')
def teleport_on(event, wcsplayer, variables):
    player = wcsplayer.player

    vector1 = Vector(*player.origin)
    vector2 = Vector(*player.view_coordinates)

    if variables['range'] >= vector1.get_distance(vector2):
        vector2 -= vector1
        vector2 *= 2
        player.set_property_vector('m_vecBaseVelocity', vector2)

        wcsplayer.skills['teleport'].reset_cooldown()

        vector1.z += 25
        teleport_effect_0.create(origin=vector1)
        teleport_effect_1.create(mins=vector1, maxs=vector1)
        teleport_effect_2.create(origin=vector1)
        teleport_effect_3.create(center=vector1)
    else:
        teleport_failed_message.send(wcsplayer.index)


# ============================================================================
# >> EVENTS
# ============================================================================
@Event('round_start')
def round_start(event):
    for delay in chain.from_iterable(_delays.values()):
        delay()

    _delays.clear()


# ============================================================================
# >> HELPER FUNCTIONS
# ============================================================================
def _reset_bash(wcsplayer, delay):
    if wcsplayer.online:
        wcsplayer.data['stuck'] -= 1

        if not wcsplayer.data['stuck']:
            if not wcsplayer.data.get('noclip'):
                if wcsplayer.data.get('jetpack'):
                    wcsplayer.player.move_type = MoveType.FLY
                else:
                    wcsplayer.player.move_type = MoveType.WALK

    _delays[wcsplayer].remove(delay)

    if not _delays[wcsplayer]:
        del _delays[wcsplayer]
