# ../wcs/modules/races/undead_scourge/__init__.py

# ============================================================================
# >> IMPORTS
# ============================================================================
# Python Imports
#   Random
from random import randint

# Source.Python Imports
#   Effects
from effects.base import TempEntity
#   Engines
from engines.precache import Model
#   Mathlib
from mathlib import Vector
#   Message
from messages import TextMsg

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

vampiric_aura_leech_message = TextMsg(settings.strings['vampiric_aura leech'])
vampiric_aura_max_message = TextMsg(settings.strings['vampiric_aura max'])
unholy_aura_message = SayText2(settings.strings['unholy_aura message'])
levitation_message = SayText2(settings.strings['levitation message'])

max_health = settings.get_game_entry('max_health')

spawncmd_effect_model = Model(settings.get_game_entry('spawncmd_effect'))
vampiric_aura_effect_0_model = Model(settings.get_game_entry('vampiric_aura_effect_0'))
vampiric_aura_effect_1_model = Model(settings.get_game_entry('vampiric_aura_effect_1'))
vampiric_aura_effect_2_model = Model(settings.get_game_entry('vampiric_aura_effect_2'))
vampiric_aura_effect_3_model = Model(settings.get_game_entry('vampiric_aura_effect_3'))

spawncmd_effect = TempEntity('BeamRingPoint', halo=spawncmd_effect_model, model=spawncmd_effect_model, start_radius=10, life_time=3.6, start_width=10, end_width=10, fade_length=50, amplitude=2, red=155, green=0, blue=0, alpha=255, speed=2)
vampiric_aura_effect_0 = TempEntity('BeamPoints', halo=vampiric_aura_effect_0_model, model=vampiric_aura_effect_0_model, life_time=0.5, start_width=10, end_width=10, red=255, green=0, blue=0, alpha=255)
vampiric_aura_effect_1 = TempEntity('BeamPoints', halo=vampiric_aura_effect_1_model, model=vampiric_aura_effect_1_model, life_time=0.5, start_width=10, end_width=10, red=255, green=0, blue=0, alpha=255)
vampiric_aura_effect_2 = TempEntity('BeamPoints', halo=vampiric_aura_effect_2_model, model=vampiric_aura_effect_2_model, life_time=0.5, start_width=2, end_width=2, red=255, green=255, blue=255, alpha=255)
vampiric_aura_effect_3 = TempEntity('BeamRingPoint', halo=vampiric_aura_effect_3_model, model=vampiric_aura_effect_3_model, start_radius=1, end_radius=10, life_time=0.5, start_width=40, end_width=40, fade_length=500, amplitude=255, red=255, green=0, blue=0, alpha=100, speed=255)


# ============================================================================
# >> RACE CALLBACKS
# ============================================================================
@Command
def spawncmd(event, wcsplayer):
    vector = Vector(*wcsplayer.player.origin)
    vector.z += 5

    for end_radius in (40, 50, 60, 70, 80, 90):
        spawncmd_effect.create(wcsplayer.index, center=vector, end_radius=end_radius)

        vector.z += 10


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
                    value = randint(4, 21)
                    value = value if health + value <= max_health else health + value - max_health

                    attacker.health = health + value

                    vampiric_aura_leech_message.send(wcsplayer.index, value=value)
                else:
                    vampiric_aura_max_message.send(wcsplayer.index, value=max_health)


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
