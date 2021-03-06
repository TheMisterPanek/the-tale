
import smart_imports

smart_imports.all()


E = 0.001


class Worker(utils_workers.BaseWorker):
    GET_CMD_TIMEOUT = 10
    STOP_SIGNAL_REQUIRED = False

    def initialize(self):
        return conf.settings.ENABLE_WORKER_HIGHLEVEL

    def cmd_initialize(self, turn_number, worker_id):
        self.send_cmd('initialize', {'turn_number': turn_number, 'worker_id': worker_id})

    def process_initialize(self, turn_number, worker_id):
        self.clean_queues()  # it is bad solution, but it allow to clean queues after tests

        if self.initialized:
            self.logger.warn('highlevel already initialized, do reinitialization')

        self.initialized = True
        self.worker_id = worker_id
        self.turn_number = turn_number

        self.logger.info('HIGHLEVEL INITIALIZED')

        amqp_environment.environment.workers.supervisor.cmd_answer('initialize', self.worker_id)

    def cmd_next_turn(self, turn_number):
        return self.send_cmd('next_turn', data={'turn_number': turn_number})

    def process_next_turn(self, turn_number):

        sync_data_sheduled = None
        sync_data_required = False

        self.turn_number += 1

        if turn_number != self.turn_number:
            raise exceptions.WrongHighlevelTurnNumber(expected_turn_number=self.turn_number, new_turn_number=turn_number)

        if self.turn_number % c.MAP_SYNC_TIME == 0:
            sync_data_required = True
            sync_data_sheduled = True

        if self.turn_number % (bills_conf.settings.BILLS_PROCESS_INTERVAL / c.TURN_DELTA) == 0:
            if self.apply_bills():
                sync_data_required = True
                sync_data_sheduled = False

        if sync_data_required:
            self.sync_data(sheduled=sync_data_sheduled)
            self.update_map()

    def update_map(self):
        self.logger.info('initialize map update')
        amqp_environment.environment.workers.game_long_commands.cmd_update_map()

    def cmd_stop(self):
        return self.send_cmd('stop')

    def process_stop(self):
        self.sync_data()

        self.initialized = False

        amqp_environment.environment.workers.supervisor.cmd_answer('stop', self.worker_id)

        self.stop_required = True
        self.logger.info('HIGHLEVEL STOPPED')

    @places_storage.places.postpone_version_update
    @places_storage.buildings.postpone_version_update
    @persons_storage.persons.postpone_version_update
    def sync_data(self, sheduled=True):

        self.logger.info('sync data')

        call_after_transaction = []

        with django_transaction.atomic():
            self.logger.info('sync data transaction started')

            if sheduled:
                try:
                    politic_power_logic.sync_power()
                    places_logic.sync_fame()
                    places_logic.sync_money()
                except tt_api_exceptions.TTAPIError as e:
                    sentry_sdk.capture_exception(e)
                    self.logger.exception('Error while syncing powers')

                # обрабатывает работы только во время запланированного обновления
                # поскольку при остановке игры нельзя будет обработать команды для героев
                # (те уже будут сохраняться в базу, рабочие логики будут недоступны)
                for person in persons_storage.persons.all():
                    call_after_transaction.extend(jobs_logic.update_job(person.job, person.id))

                for place in places_storage.places.all():
                    call_after_transaction.extend(jobs_logic.update_job(place.job, place.id))

                frontier_places = [place for place in places_storage.places.all() if place.is_frontier]
                core_places = [place for place in places_storage.places.all() if not place.is_frontier]

                places_logic.sync_power_economic(frontier_places,
                                                 max_economic=c.PLACE_MAX_FRONTIER_ECONOMIC)
                places_logic.sync_power_economic(core_places,
                                                 max_economic=c.PLACE_MAX_ECONOMIC)

                places_logic.sync_money_economic(frontier_places,
                                                 max_economic=c.PLACE_MAX_FRONTIER_ECONOMIC)
                places_logic.sync_money_economic(core_places,
                                                 max_economic=c.PLACE_MAX_ECONOMIC)

                places_logic.update_effects()

                for place in places_storage.places.all():
                    place.attrs.sync_size(c.MAP_SYNC_TIME_HOURS)
                    place.attrs.set_area(map_storage.cells.place_area(place.id))

                    place.sync_race()
                    place.sync_habits()
                    place.update_heroes_habits()

                    # must be last operation to display and use real data
                    place.refresh_attributes()

                    place.mark_as_updated()

            places_storage.places.save_all()
            persons_storage.persons.save_all()

        self.logger.info('sync data transaction completed')

        self.logger.info('after transaction operations number: {number}'.format(number=len(call_after_transaction)))

        for operation in call_after_transaction:
            operation()

        self.logger.info('sync data completed')

    def validate_bills(self):
        for active_bill_id in bills_prototypes.BillPrototype.get_active_bills_ids():
            bill = bills_prototypes.BillPrototype.get_by_id(active_bill_id)
            if not bill.has_meaning():
                bill.stop()

    def apply_bills(self):
        self.logger.info('apply bills')

        self.validate_bills()

        applied = False

        for applied_bill_id in bills_prototypes.BillPrototype.get_applicable_bills_ids():
            bill = bills_prototypes.BillPrototype.get_by_id(applied_bill_id)

            if bill.is_delayed:
                continue

            if bill.state.is_VOTING:
                applied = bill.apply() or applied

            self.validate_bills()

        self.logger.info('apply bills completed')

        return applied
