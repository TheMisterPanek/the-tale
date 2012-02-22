# -*- coding: utf-8 -*-

import random

from dext.utils import s11n

from game.journal.template import NounFormatter, GENDER

from ..heroes.prototypes import BASE_ATTRIBUTES
from ..heroes.habilities import AbilitiesPrototype

class MobException(Exception): pass


class MobPrototype(object):

    def __init__(self):
        pass

    @property
    def health_percents(self): return float(self.health) / self.max_health

    def get_basic_damage(self):
        return self.power * (1 + random.uniform(-self.damage_dispersion, self.damage_dispersion))

    def strike_by(self, percents):
        self.health = max(0, self.health - self.max_health * percents)

    def kill(self):
        pass

    def get_loot(self):
        from ..artifacts.constructors import ArtifactConstructorPrototype
        return ArtifactConstructorPrototype.generate_loot(self.loot_list, self.level)

    def get_formatter(self):
        return NounFormatter(data=self.name_forms, gender=self.gender)

    def serialize(self):
        return s11n.to_json({'name': self.name,
                             'name_forms': self.name_forms,
                             'gender': self.gender,
                             'initiative': self.battle_speed,
                             'max_health': self.max_health,
                             'damage_dispersion': self.damage_dispersion,
                             'power': self.power,
                             'level': self.level,
                             'health': self.health,
                             'loot_list': self.loot_list,
                             'abilities': self.abilities.serialize()})

    @classmethod
    def deserialize(cls, data_string):
        data = s11n.from_json(data_string)
        if not data:
            return None

        mob = cls()
        mob.name = data.get('name', u'осколок прошлого')
        mob.name_forms = data.get('name_forms', [mob.name, mob.name, mob.name, mob.name, mob.name, mob.name])
        mob.gender = data.get('gender', GENDER.MASCULINE)
        mob.battle_speed = data.get('initiative', 5)
        mob.health = data.get('health', 1)
        mob.max_health = data.get('max_health', mob.health + 1)
        mob.damage_dispersion = data.get('damage_dispersion', 0)
        mob.power = data.get('power', 0)
        mob.level = data.get('level', 1)

        mob.loot_list = data.get('loot_list', [])
        mob.abilities = AbilitiesPrototype.deserialize(data.get('abilities', '[]'))

        return mob

    @classmethod
    def construct(cls,
                  level, 
                  NAME, 
                  NAME_FORMS,
                  GENDER,
                  HEALTH_RELATIVE_TO_HERO, 
                  INITIATIVE,
                  DAMAGE_DISPERSION,
                  POWER_PER_LEVEL,
                  ABILITIES,
                  LOOT_LIST):
        mob = cls()
        mob.name = NAME
        mob.name_forms = NAME_FORMS
        mob.gender = GENDER
        mob.battle_speed = INITIATIVE
        mob.max_health = int(BASE_ATTRIBUTES.get_max_health(level) * HEALTH_RELATIVE_TO_HERO)
        mob.damage_dispersion = DAMAGE_DISPERSION
        mob.power = POWER_PER_LEVEL * level
        mob.level = level
        mob.health = mob.max_health
        mob.loot_list = LOOT_LIST
        mob.abilities = AbilitiesPrototype(abilities=ABILITIES)

        return mob


    def ui_info(self):
        return { 'name': self.name,
                 'health': self.health_percents }
