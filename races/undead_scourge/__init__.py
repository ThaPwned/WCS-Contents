# ../wcs/modules/races/undead_scourge/__init__.py

# ============================================================================
# >> IMPORTS
# ============================================================================
# Python Imports
#   Random
from random import randint

# Source.Python Imports
#   Mathlib
from mathlib import Vector
#   Message
from messages import HudMsg

# WCS Imports
#   Helpers
from ....core.helpers.overwrites import SayText2
#   Modules
from ....core.modules.races.calls import Command
from ....core.modules.races.manager import race_manager
#   Players
from ....core.players.entity import Player
from ....core.players.filters import PlayerReadyIter


# ============================================================================
# >> GLOBAL VARIABLES
# ============================================================================
settings = race_manager.find(__name__)

vampiric_aura_leech_message = HudMsg(settings.strings['vampiric_aura leech'], y=0.20)
unholy_aura_message = SayText2(settings.strings['unholy_aura message'])
levitation_message = SayText2(settings.strings['levitation message'])

max_health = settings.config['skills']['vampiric_aura']['other']['max_health']
min_health_gain = settings.config['skills']['vampiric_aura']['other']['min_health_gain']
max_health_gain = settings.config['skills']['vampiric_aura']['other']['max_health_gain']

spawncmd_effect = settings.get_effect_entry('spawncmd')
vampiric_aura_effect_0 = settings.get_effect_entry('vampiric_aura_0')
vampiric_aura_effect_1 = settings.get_effect_entry('vampiric_aura_1')
vampiric_aura_effect_2 = settings.get_effect_entry('vampiric_aura_2')
vampiric_aura_effect_3 = settings.get_effect_entry('vampiric_aura_3')


# ============================================================================
# >> RACE CALLBACKS
# ============================================================================
@Command
def spawncmd(event, wcsplayer):
    vector = Vector(*wcsplayer.player.origin)
    vector.z += 5

    for end_radius in (40, 50, 60, 70, 80, 90):
        spawncmd_effect.create(center=vector, end_radius=end_radius)

        vector.z += 10


@Command
def on_skill_desc(wcsplayer, skill_name, kwargs):
    config = settings.config['skills'][skill_name]['variables']

    if skill_name == 'vampiric_aura':
        chance = config['chance']

        kwargs['min_chance'] = chance[0]
        kwargs['max_chance'] = chance[-1]
        kwargs['min_health'] = min_health_gain
        kwargs['max_health'] = max_health_gain
    elif skill_name == 'unholy_aura':
        speed = config['speed']

        kwargs['min_speed'] = (speed[0] - 1) * 100
        kwargs['max_speed'] = (speed[-1] - 1) * 100
    elif skill_name == 'levitation':
        gravity = config['gravity']

        kwargs['min_gravity'] = (1 - gravity[0]) * 100
        kwargs['max_gravity'] = (1 - gravity[-1]) * 100
    elif skill_name == 'suicide_bomber':
        chance = config['chance']
        magnitude = config['magnitude']
        radius = config['radius']

        kwargs['min_chance'] = chance[0]
        kwargs['max_chance'] = chance[-1]
        kwargs['min_magnitude'] = magnitude[0]
        kwargs['max_magnitude'] = magnitude[-1]
        kwargs['min_radius'] = radius[0]
        kwargs['max_radius'] = radius[-1]


# ============================================================================
# >> SKILL CALLBACKS
# ============================================================================
@Command
def vampiric_aura(event, wcsplayer, variables):
    if randint(0, 100) <= variables['chance']:
        wcsvictim = Player.from_userid(event['userid'])
        victim = wcsvictim.player

        if not victim.dead:
            attacker = wcsplayer.player

            if not attacker.dead:
                vector1 = Vector(*victim.origin)
                vector2 = Vector(*attacker.origin)

                vector1.z += 20
                vector2.z += 20
                vampiric_aura_effect_0.create(start_point=vector1, end_point=vector2)
                vampiric_aura_effect_1.create(start_point=vector1, end_point=vector2)
                vampiric_aura_effect_2.create(start_point=vector1, end_point=vector2)

                vector2.z += 8
                vampiric_aura_effect_3.create(center=vector2)

                health = attacker.health

                if health < max_health:
                    value = randint(min_health_gain, max_health_gain)
                    value = value if health + value <= max_health else health + value - max_health

                    attacker.health = health + value

                    vampiric_aura_leech_message.send(wcsplayer.index, value=value)


@Command
def unholy_aura(event, wcsplayer, variables):
    wcsplayer.player.speed = variables['speed']

    value = variables['speed'] * 100 - 100

    unholy_aura_message.send(wcsplayer.index, value=value)


@Command
def levitation(event, wcsplayer, variables):
    wcsplayer.player.gravity = variables['gravity']

    value = variables['gravity'] * 100

    levitation_message.send(wcsplayer.index, value=value)


@Command
def suicide_bomber(event, wcsplayer, variables):
    if randint(0, 100) <= variables['chance']:
        vector = wcsplayer.player.origin
        magnitude = variables['magnitude']
        radius = variables['radius']

        damage = magnitude * radius

        # TODO: Check if there's a wall between the two players
        for target, wcstarget in PlayerReadyIter(['alive', 'ct' if wcsplayer.player.team_index == 2 else 't']):
            if not wcstarget.data.get('ulti_immunity', False):
                distance = vector.get_distance(target.origin)

                if distance <= radius:
                    wcstarget.take_damage(damage / distance, wcsplayer.index, 'undead_scourge-suicide_bomber')
