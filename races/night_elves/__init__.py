# ../wcs/modules/races/night_elves/__init__.py

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

# WCS Imports
#   Helpers
from ....core.helpers.overwrites import SayText2
#   Modules
from ....core.modules.races.calls import command
from ....core.modules.races.manager import race_manager
#   Players
from ....core.players.entity import Player
from ....core.players.filters import PlayerReadyIter


# ============================================================================
# >> GLOBAL VARIABLES
# ============================================================================
settings = race_manager.find(__name__)

_delays = defaultdict(list)

entangling_roots_count_message = SayText2(settings.strings['entangling_roots count'])
entangling_roots_failed_message = SayText2(settings.strings['entangling_roots failed'])
entangling_roots_block_attacker_message = SayText2(settings.strings['entangling_roots block attacker'])
entangling_roots_block_victim_message = SayText2(settings.strings['entangling_roots block victim'])

spawncmd_effect = settings.get_effect_entry('spawncmd')
thorns_aura_0_effect = settings.get_effect_entry('thorns_aura_0')
thorns_aura_1_effect = settings.get_effect_entry('thorns_aura_1')
trueshot_aura_0_effect = settings.get_effect_entry('trueshot_aura_0')
trueshot_aura_1_effect = settings.get_effect_entry('trueshot_aura_1')
trueshot_aura_2_effect = settings.get_effect_entry('trueshot_aura_2')
entangling_roots_0_effect = settings.get_effect_entry('entangling_roots_0')
entangling_roots_1_effect = settings.get_effect_entry('entangling_roots_1')
entangling_roots_2_effect = settings.get_effect_entry('entangling_roots_2')
entangling_roots_3_effect = settings.get_effect_entry('entangling_roots_3')
entangling_roots_4_effect = settings.get_effect_entry('entangling_roots_4')


# ============================================================================
# >> RACE CALLBACKS
# ============================================================================
@command
def spawncmd(event, wcsplayer):
    vector = Vector(*wcsplayer.player.origin)

    vector.z += 20
    spawncmd_effect.create(delay=0.2, center=vector)

    vector.z += 10
    spawncmd_effect.create(delay=0.3, center=vector)


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

    if skill_name == 'evasion':
        chance = config['chance']

        kwargs['min_chance'] = chance[0]
        kwargs['max_chance'] = chance[-1]
    elif skill_name == 'thorns_aura':
        chance = config['chance']
        multiplier = config['multiplier']

        kwargs['min_chance'] = chance[0]
        kwargs['max_chance'] = chance[-1]
        kwargs['min_multiplier'] = multiplier[0] * 100
        kwargs['max_multiplier'] = multiplier[-1] * 100
    elif skill_name == 'trueshot_aura':
        chance = config['chance']
        multiplier = config['multiplier']

        kwargs['min_chance'] = chance[0]
        kwargs['max_chance'] = chance[-1]
        kwargs['min_multiplier'] = multiplier[0] * 100
        kwargs['max_multiplier'] = multiplier[-1] * 100
    elif skill_name == 'entangling_roots':
        radius = config['radius']
        duration = config['duration']

        kwargs['min_radius'] = radius[0]
        kwargs['max_radius'] = radius[-1]
        kwargs['min_duration'] = duration[0]
        kwargs['max_duration'] = duration[-1]


# ============================================================================
# >> SKILL CALLBACKS
# ============================================================================
@command(event='pre_player_victim')
def evasion(event, wcsplayer, variables):
    if randint(0, 100) <= variables['chance']:
        event['info'].damage = 0


@command(event='player_victim')
def thorns_aura(event, wcsplayer, variables):
    if randint(0, 100) <= variables['chance']:
        victim = wcsplayer.player

        if not victim.dead:
            wcsattacker = Player.from_userid(event['attacker'])
            wcsattacker.take_damage(event['dmg_health'] * variables['multiplier'], wcsplayer.index, 'night_elves-thorns_aura')

            vector1 = Vector(*victim.origin)
            vector2 = Vector(*wcsattacker.player.origin)

            vector1.z += 15
            vector2.z += 15
            thorns_aura_0_effect.create(start_point=vector1, end_point=vector2)
            thorns_aura_1_effect.create(start_point=vector1, end_point=vector2)


@command(event='pre_player_attacker')
def trueshot_aura(event, wcsplayer, variables):
    if randint(0, 100) <= variables['chance']:
        wcsvictim = Player.from_userid(event['userid'])
        wcsvictim.take_delayed_damage(event['info'].damage * variables['multiplier'], wcsplayer.index, 'night_elves-trueshot_aura')

        vector1 = Vector(*wcsplayer.player.origin)
        vector2 = Vector(*wcsvictim.player.origin)

        vector1.z += 10
        trueshot_aura_0_effect.create(center=vector1)

        vector1.z += 10
        vector2.z += 20
        trueshot_aura_1_effect.create(start_point=vector1, end_point=vector2)

        vector1.z += 10
        trueshot_aura_2_effect.create(center=vector1)


@command(event='player_ability')
def entangling_roots_on(event, wcsplayer, variables):
    player = wcsplayer.player

    if not player.dead:
        team = player.team_index

        if team >= 2:
            radius = variables['radius']

            targets = []
            immune = 0

            vector = Vector(*player.origin)

            # TODO: Check if there's a wall between the two players
            for target, wcstarget in PlayerReadyIter(['alive', 'ct' if team == 2 else 't']):
                if wcstarget.data.get('ulti_immunity', False):
                    immune += 1

                    entangling_roots_block_victim_message.send(target.index)
                else:
                    vector2 = target.origin
                    distance = vector.get_distance(vector2)

                    if distance <= radius:
                        targets.append((wcstarget, Vector(*vector2)))

            if immune:
                entangling_roots_block_attacker_message.send(wcsplayer.index, count=immune)

            if targets:
                wcsplayer.skills['entangling_roots'].reset_cooldown()

                vector.z += 35

                duration = variables['duration']

                for (wcstarget, vector2) in targets:
                    stuck = wcstarget.data.get('stuck', 0)

                    if not stuck:
                        if not wcstarget.data.get('noclip'):
                            wcstarget.player.move_type = MoveType.NONE

                    wcstarget.data['stuck'] = stuck + 1

                    delay = Delay(duration, _reset_root, (wcstarget, ))
                    delay.args += (delay, )
                    _delays[wcstarget].append(delay)

                    vector2.z += 10
                    entangling_roots_0_effect.create(center=vector2)

                    vector2.z += 15
                    entangling_roots_1_effect.create(center=vector2)

                    vector2.z += 10
                    entangling_roots_2_effect.create(start_point=vector, end_point=vector2)
                    entangling_roots_3_effect.create(start_point=vector, end_point=vector2)
                    entangling_roots_4_effect.create(start_point=vector, end_point=vector2)

                entangling_roots_count_message.send(wcsplayer.index, count=len(targets))
            else:
                entangling_roots_failed_message.send(wcsplayer.index)


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
def _reset_root(wcsplayer, delay):
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
