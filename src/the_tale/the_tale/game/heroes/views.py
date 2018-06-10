
from django.core.urlresolvers import reverse

from questgen import relations as questgen_relations

from dext.common.utils import views as dext_views
from dext.views import handler, validator, validate_argument

from the_tale.amqp_environment import environment

from the_tale.common.utils.resources import Resource
from the_tale.common.utils.decorators import login_required
from the_tale.common.postponed_tasks.prototypes import PostponedTaskPrototype

from the_tale.accounts.prototypes import AccountPrototype
from the_tale.accounts.clans.prototypes import ClanPrototype

from the_tale.game.balance import constants as c

from the_tale.game import relations as game_relations

from the_tale.game import names
from the_tale.game.relations import HABIT_TYPE

from the_tale.game.cards import cards

from . import postponed_tasks
from . import relations
from . import forms
from . import conf
from . import meta_relations
from . import logic

from the_tale.game.heroes.habilities import relations as habilities_relations


###############################
# new view processors
###############################

class CurrentHeroProcessor(dext_views.BaseViewProcessor):
    def preprocess(self, context):
        if not context.account.is_authenticated:
            context.account_hero = None
            return

        context.account_hero = logic.load_hero(account_id=context.account.id)


class HeroProcessor(dext_views.ArgumentProcessor):
    def parse(self, context, raw_value):
        try:
            hero_id = int(raw_value)
        except ValueError:
            self.raise_wrong_format()

        return logic.load_hero(account_id=hero_id)


def split_list(items):
    half = (len(items)+1)//2
    left = items[:half]
    right = items[half:]
    if len(left) > len(right):
        right.append(None)
    return list(zip(left, right))


class HeroResource(Resource):

    @validate_argument('hero', lambda hero_id: logic.load_hero(hero_id=int(hero_id)), 'heroes', 'Неверный идентификатор героя')
    def initialize(self, hero=None, *args, **kwargs):
        super(HeroResource, self).initialize(*args, **kwargs)
        self.hero = hero
        self.can_moderate_heroes = self.account.has_perm('accounts.moderate_account')

    @property
    def is_owner(self): return self.account and self.account.id == self.hero.account_id

    @validator(code='heroes.not_owner', message='Вы не являетесь владельцем данного аккаунта')
    def validate_ownership(self, *args, **kwargs): return self.is_owner

    @validator(code='heroes.moderator_rights_required', message='Вы не являетесь модератором')
    def validate_moderator_rights(self, *args, **kwargs): return self.can_moderate_heroes

    @handler('', method='get')
    def index(self):
        return self.redirect('/')

    @login_required
    @handler('my-hero', method='get')
    def my_hero(self):
        hero = logic.load_hero(account_id=self.account.id)
        return self.redirect(reverse('game:heroes:show', args=[hero.id]))

    @handler('#hero', name='show', method='get')
    def hero_page(self):
        abilities = sorted(self.hero.abilities.all, key=lambda x: x.NAME)
        battle_active_abilities = [a for a in abilities if a.type.is_BATTLE and a.activation_type.is_ACTIVE] # pylint: disable=W0110
        battle_passive_abilities = [a for a in abilities if a.type.is_BATTLE and a.activation_type.is_PASSIVE]# pylint: disable=W0110
        nonbattle_abilities = [a for a in abilities if a.type.is_NONBATTLE]# pylint: disable=W0110
        companion_abilities = [a for a in abilities if a.type.is_COMPANION]# pylint: disable=W0110

        edit_name_form = forms.EditNameForm(initial=forms.EditNameForm.get_initials(hero=self.hero))

        master_account = AccountPrototype.get_by_id(self.hero.account_id)

        master_clan = None
        if master_account.clan_id is not None:
            master_clan = ClanPrototype.get_by_id(master_account.clan_id)

        return self.template('heroes/hero_page.html',
                             {'battle_active_abilities': battle_active_abilities,
                              'battle_passive_abilities': battle_passive_abilities,
                              'nonbattle_abilities': nonbattle_abilities,
                              'companion_abilities': companion_abilities,
                              'heroes_settings': conf.heroes_settings,
                              'hero_meta_object': meta_relations.Hero.create_from_object(self.hero),
                              'is_owner': self.is_owner,
                              'edit_name_form': edit_name_form,
                              'master_account': master_account,
                              'master_clan': master_clan,
                              'EQUIPMENT_SLOT': relations.EQUIPMENT_SLOT,
                              'PREFERENCE_TYPE': relations.PREFERENCE_TYPE,
                              'ABILITY_TYPE': habilities_relations.ABILITY_TYPE,
                              'HABIT_TYPE': HABIT_TYPE,
                              'CARD_TYPE': cards.CARD,
                              'QUEST_OPTION_MARKERS': questgen_relations.OPTION_MARKERS,
                              'HABITS_BORDER': c.HABITS_BORDER} )

    @login_required
    @validate_ownership()
    @handler('#hero', 'choose-ability-dialog', method='get')
    def choose_ability_dialog(self):
        return self.template('heroes/choose_ability.html',
                             {'CARD_TYPE': cards.CARD,
                              'hero': self.hero} )

    @login_required
    @validate_argument('preference', lambda value: relations.PREFERENCE_TYPE(int(value)), 'heroes', 'Неверный идентификатор предпочтения')
    @handler('#hero', 'preference-info-dialog', method='get')
    def preference_info_dialog(self, preference):
        favorite_items = {slot: self.hero.equipment.get(slot)
                          for slot in relations.EQUIPMENT_SLOT.records
                          if self.hero.equipment.get(slot) is not None}

        return self.template('heroes/preferences/dialog.html',
                             {'hero': self.hero,
                              'preference': preference,
                              'EQUIPMENT_SLOT': relations.EQUIPMENT_SLOT,
                              'RISK_LEVEL': relations.RISK_LEVEL,
                              'COMPANION_DEDICATION': relations.COMPANION_DEDICATION,
                              'COMPANION_EMPATHY': relations.COMPANION_EMPATHY,
                              'ENERGY_REGENERATION': relations.ENERGY_REGENERATION,
                              'ARCHETYPE': game_relations.ARCHETYPE,
                              'favorite_items': favorite_items,
                              'change_preferences_card': cards.CARD.CHANGE_PREFERENCE})

    @login_required
    @validate_ownership()
    @handler('#hero', 'change-hero', method='post')
    def change_hero(self):
        edit_name_form = forms.EditNameForm(self.request.POST)

        if not edit_name_form.is_valid():
            return self.json_error('heroes.change_name.form_errors', edit_name_form.errors)

        change_task = postponed_tasks.ChangeHeroTask(hero_id=self.hero.id,
                                                     name=edit_name_form.c.name,
                                                     race=edit_name_form.c.race,
                                                     gender=edit_name_form.c.gender)

        task = PostponedTaskPrototype.create(change_task)

        environment.workers.supervisor.cmd_logic_task(self.account.id, task.id)

        return self.json_processing(task.status_url)

    @login_required
    @validate_moderator_rights()
    @handler('#hero', 'reset-name', method='post')
    def reset_name(self):
        change_task = postponed_tasks.ChangeHeroTask(hero_id=self.hero.id,
                                     name=names.generator().get_name(self.hero.race, self.hero.gender),
                                     race=self.hero.race,
                                     gender=self.hero.gender)

        task = PostponedTaskPrototype.create(change_task)

        environment.workers.supervisor.cmd_logic_task(self.hero.account_id, task.id)

        return self.json_processing(task.status_url)

    @login_required
    @validate_moderator_rights()
    @handler('#hero', 'force-save', method='post')
    def force_save(self):
        environment.workers.supervisor.cmd_force_save(account_id=self.hero.account_id)
        return self.json_ok()

    @login_required
    @validate_ownership()
    @handler('#hero', 'choose-ability', method='post')
    def choose_ability(self, ability_id):

        choose_task = postponed_tasks.ChooseHeroAbilityTask(hero_id=self.hero.id, ability_id=ability_id)

        task = PostponedTaskPrototype.create(choose_task)

        environment.workers.supervisor.cmd_logic_task(self.account.id, task.id)

        return self.json_processing(task.status_url)
