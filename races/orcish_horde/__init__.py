# ../wcs/modules/races/orcish_horde/__init__.py

# ============================================================================
# >> IMPORTS
# ============================================================================
# Python Imports
#   Random
from random import randint
#   Time
from time import time

# Source.Python Imports
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
from ....core.modules.races.calls import Command
from ....core.modules.races.manager import race_manager
#   Players
from ....core.players.entity import Player
from ....core.players.filters import PlayerReadyIter


# ============================================================================
# >> GLOBAL VARIABLES
# ============================================================================
settings = race_manager.find(__name__)

_delays = {}

reincarnation_counter_message = HudMsg(settings.strings['reincarnation counter'], y=0.2)
reincarnation_complete_message = HudMsg(settings.strings['reincarnation complete'], y=0.2)
reincarnation_initialize_message = SayText2(settings.strings['reincarnation initialize'])
chain_lightning_count_message = SayText2(settings.strings['chain_lightning count'])
chain_lightning_failed_message = SayText2(settings.strings['chain_lightning failed'])
chain_lightning_block_attacker_message = SayText2(settings.strings['chain_lightning block attacker'])
chain_lightning_block_victim_message = SayText2(settings.strings['chain_lightning block victim'])

critical_strike_effect = settings.get_effect_entry('critical_strike')
critical_grenade_0_effect = settings.get_effect_entry('critical_grenade_0')
critical_grenade_1_effect = settings.get_effect_entry('critical_grenade_1')
critical_grenade_2_effect = settings.get_effect_entry('critical_grenade_2')
reincarnation_effect = settings.get_effect_entry('reincarnation')
chain_lightning_0_effect = settings.get_effect_entry('chain_lightning_0')
chain_lightning_1_effect = settings.get_effect_entry('chain_lightning_1')
chain_lightning_2_effect = settings.get_effect_entry('chain_lightning_2')


# ============================================================================
# >> RACE CALLBACKS
# ============================================================================
@Command
def roundstartcmd(event, wcsplayer):
    wcsplayer.data['vengeance'] = True


@Command
def spawncmd(event, wcsplayer):
    delay = _delays.pop(wcsplayer, None)

    if delay is not None:
        if delay.running:
            delay.cancel()


@Command
def disconnectcmd(event, wcsplayer):
    delay = _delays.pop(wcsplayer, None)

    if delay is not None:
        if delay.running:
            delay.cancel()


@Command
def on_skill_desc(wcsplayer, skill_name, kwargs):
    config = settings.config['skills'][skill_name]['variables']

    if skill_name == 'critical_strike':
        chance = config['chance']
        multiplier = config['multiplier']

        kwargs['min_chance'] = chance[0]
        kwargs['max_chance'] = chance[-1]
        kwargs['min_multiplier'] = multiplier[0] * 100
        kwargs['max_multiplier'] = multiplier[-1] * 100
    elif skill_name == 'critical_grenade':
        chance = config['chance']
        multiplier = config['multiplier']

        kwargs['min_chance'] = chance[0]
        kwargs['max_chance'] = chance[-1]
        kwargs['min_multiplier'] = multiplier[0] * 100
        kwargs['max_multiplier'] = multiplier[-1] * 100
    elif skill_name == 'reincarnation':
        chance = config['chance']

        kwargs['min_chance'] = chance[0]
        kwargs['max_chance'] = chance[-1]
    elif skill_name == 'chain_lightning':
        max_targets = config['max_targets']
        radius = config['radius']
        damage = config['damage']

        kwargs['min_targets'] = max_targets[0]
        kwargs['max_targets'] = max_targets[-1]
        kwargs['min_radius'] = radius[0]
        kwargs['max_radius'] = radius[-1]
        kwargs['min_damage'] = damage[0]
        kwargs['max_damage'] = damage[-1]


# ============================================================================
# >> SKILL CALLBACKS
# ============================================================================
@Command
def critical_strike(event, wcsplayer, variables):
    if randint(0, 100) <= variables['chance']:
        userid = event['userid']
        wcsvictim = Player.from_userid(userid)

        wcsvictim.take_delayed_damage(event['info'].damage * variables['multiplier'], wcsplayer.index, 'orcish_horde-critical_strike')

        vector1 = Vector(*wcsplayer.player.origin)
        vector2 = Vector(*wcsvictim.player.origin)

        vector1.z += 20
        vector2.z += 20
        critical_strike_effect.create(start_point=vector1, end_point=vector2)


@Command
def critical_grenade(event, wcsplayer, variables):
    if event['weapon'] == 'hegrenade_projectile':
        if randint(0, 100) <= variables['chance']:
            userid = event['userid']
            wcsvictim = Player.from_userid(userid)

            wcsvictim.take_delayed_damage(event['info'].damage * variables['multiplier'], wcsplayer.index, 'orcish_horde-critical_grenade')

            vector = Vector(*wcsvictim.player.origin)

            vector.z += 15
            critical_grenade_0_effect.create(center=vector)

            vector.z += 20
            critical_grenade_1_effect.create(center=vector)

            vector.z += 20
            critical_grenade_2_effect.create(center=vector)


@Command
def reincarnation(event, wcsplayer, variables):
    if wcsplayer.data.get('vengeance'):
        if randint(0, 100) <= variables['chance']:
            wcsplayer.data['vengeance'] = False

            reincarnation_initialize_message.send(wcsplayer.index)

            vector = Vector(*wcsplayer.player.origin)

            _reincarnate_delay(wcsplayer, 3, vector)

            reincarnation_effect.create(center=vector)


@Command
def chain_lightning_on(event, wcsplayer, variables):
    player = wcsplayer.player

    if not player.dead:
        team = player.team_index

        if team >= 2:
            max_targets = variables['max_targets']
            radius = variables['radius']

            targets = []
            immune = 0

            vector = Vector(*player.origin)

            # TODO: Check if there's a wall between the two players
            for target, wcstarget in PlayerReadyIter(['alive', 'ct' if wcsplayer.player.team_index == 2 else 't']):
                if wcstarget.data.get('ulti_immunity', False):
                    immune += 1

                    chain_lightning_block_victim_message.send(target.index)
                else:
                    vector2 = target.origin
                    distance = vector.get_distance(vector2)

                    if distance <= radius:
                        targets.append((wcstarget, Vector(*vector2)))

                        max_targets -= 1

                        if not max_targets:
                            break

            if immune:
                chain_lightning_block_attacker_message.send(wcsplayer.index, count=immune)

            if targets:
                wcsplayer.skills['chain_lightning'].reset_cooldown()

                vector.z += 35

                damage = variables['damage']

                for (wcstarget, vector2) in targets:
                    wcstarget.take_damage(damage, wcsplayer.index, 'orcish_horde-chain_lightning')

                    vector2.z += 35
                    chain_lightning_0_effect.create(start_point=vector, end_point=vector2)
                    chain_lightning_1_effect.create(start_point=vector, end_point=vector2)
                    chain_lightning_2_effect.create(start_point=vector, end_point=vector2)

                chain_lightning_count_message.send(wcsplayer.index, count=len(targets))
            else:
                chain_lightning_failed_message.send(wcsplayer.index)


# ============================================================================
# >> HELPER FUNCTIONS
# ============================================================================
def _reincarnate_delay(wcsplayer, counter, vector):
    if counter:
        reincarnation_counter_message.send(wcsplayer.index, count=counter)

        counter -= 1

        _delays[wcsplayer] = Delay(1, _reincarnate_delay, (wcsplayer, counter, vector))
    else:
        reincarnation_complete_message.send(wcsplayer.index)

        player = wcsplayer.player

        player.spawn()
        player.teleport(origin=vector)
