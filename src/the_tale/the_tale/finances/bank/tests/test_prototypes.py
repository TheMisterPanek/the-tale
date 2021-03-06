
import smart_imports

smart_imports.all()


class AccountPrototypeTests(utils_testcase.TestCase, helpers.BankTestsMixin):

    def setUp(self):
        super(AccountPrototypeTests, self).setUp()
        self.entity_id = 2
        self.account = prototypes.AccountPrototype.create(entity_type=relations.ENTITY_TYPE.GAME_ACCOUNT, entity_id=self.entity_id, currency=relations.CURRENCY_TYPE.PREMIUM)

    def test_create(self):
        self.assertEqual(self.account.entity_type, relations.ENTITY_TYPE.GAME_ACCOUNT)
        self.assertEqual(self.account.entity_id, self.entity_id)
        self.assertEqual(self.account.currency, relations.CURRENCY_TYPE.PREMIUM)
        self.assertEqual(self.account.amount, 0)

    def test_duplicate_account(self):
        self.assertRaises(django_db.IntegrityError, prototypes.AccountPrototype.create, entity_type=relations.ENTITY_TYPE.GAME_ACCOUNT, entity_id=self.entity_id, currency=relations.CURRENCY_TYPE.PREMIUM)

    def test_account_with_different_currency(self):
        prototypes.AccountPrototype.create(entity_type=relations.ENTITY_TYPE.GAME_ACCOUNT, entity_id=self.entity_id, currency=relations.CURRENCY_TYPE.NORMAL)
        self.assertEqual(prototypes.AccountPrototype._model_class.objects.filter(entity_id=self.entity_id).count(), 2)

    def test_account_with_different_entity_type(self):
        prototypes.AccountPrototype.create(entity_type=relations.ENTITY_TYPE.GAME_LOGIC, entity_id=self.entity_id, currency=relations.CURRENCY_TYPE.PREMIUM)
        self.assertEqual(prototypes.AccountPrototype._model_class.objects.filter(entity_id=self.entity_id).count(), 2)

    def test_amount_real_account(self):
        self.account.amount += 100
        self.account.amount -= 10
        self.assertEqual(self.account.amount, 90)

    def test_amount__infinit_account(self):
        self.assertTrue(relations.ENTITY_TYPE.GAME_LOGIC.is_infinite)
        account = prototypes.AccountPrototype.create(entity_type=relations.ENTITY_TYPE.GAME_LOGIC, entity_id=self.entity_id, currency=relations.CURRENCY_TYPE.PREMIUM)
        old_amount = account.amount

        account.amount += 100
        account.amount -= 10

        self.assertEqual(account.amount, old_amount)

    def test_get_for_or_create__create(self):
        prototypes.AccountPrototype.get_for_or_create(entity_type=relations.ENTITY_TYPE.GAME_LOGIC, entity_id=self.entity_id, currency=relations.CURRENCY_TYPE.PREMIUM)
        self.assertEqual(prototypes.AccountPrototype._model_class.objects.filter(entity_id=self.entity_id).count(), 2)

    def test_get_for_or_create__get(self):
        prototypes.AccountPrototype.get_for_or_create(entity_type=relations.ENTITY_TYPE.GAME_ACCOUNT, entity_id=self.entity_id, currency=relations.CURRENCY_TYPE.PREMIUM)
        self.assertEqual(prototypes.AccountPrototype._model_class.objects.filter(entity_id=self.entity_id).count(), 1)

    def test_has_money__test_amount_less_then_zero(self):
        self.assertTrue(self.account.has_money(-9999999999999999999))

    def _create_incoming_invoice(self, amount, state=relations.INVOICE_STATE.FROZEN):
        invoice = prototypes.InvoicePrototype.create(recipient_type=self.account.entity_type,
                                                     recipient_id=self.account.entity_id,
                                                     sender_type=relations.ENTITY_TYPE.GAME_LOGIC,
                                                     sender_id=0,
                                                     currency=relations.CURRENCY_TYPE.PREMIUM,
                                                     amount=amount,
                                                     description_for_sender='incoming invoice for sender',
                                                     description_for_recipient='incoming invoice for recipient',
                                                     operation_uid='incoming-operation-uid')
        invoice.state = state
        invoice.save()

    def _create_outcoming_invoice(self, amount, state=relations.INVOICE_STATE.FROZEN):
        invoice = prototypes.InvoicePrototype.create(sender_type=self.account.entity_type,
                                                     sender_id=self.account.entity_id,
                                                     recipient_type=relations.ENTITY_TYPE.GAME_LOGIC,
                                                     recipient_id=0,
                                                     currency=relations.CURRENCY_TYPE.PREMIUM,
                                                     amount=amount,
                                                     description_for_sender='outcoming invoice for sender',
                                                     description_for_recipient='outcoming invoice for recipient',
                                                     operation_uid='outcoming-operation-uid')
        invoice.state = state
        invoice.save()

    def test_has_money__incoming_money_freezed(self):
        self.account.amount = 100

        self._create_incoming_invoice(amount=100)

        self._create_incoming_invoice(amount=-1000, state=relations.INVOICE_STATE.CONFIRMED)
        self._create_incoming_invoice(amount=-1000, state=relations.INVOICE_STATE.REQUESTED)

        self.assertTrue(self.account.has_money(50))
        self.assertTrue(self.account.has_money(100))
        self.assertFalse(self.account.has_money(150))
        self.assertFalse(self.account.has_money(151))

        self._create_incoming_invoice(amount=-60)

        self.assertTrue(self.account.has_money(40))
        self.assertFalse(self.account.has_money(41))

    def test_has_money__outcoming_money_freezed(self):
        self.account.amount = 150

        self._create_outcoming_invoice(amount=100)

        self._create_incoming_invoice(amount=-1000, state=relations.INVOICE_STATE.CONFIRMED)
        self._create_incoming_invoice(amount=-1000, state=relations.INVOICE_STATE.REQUESTED)

        self.assertTrue(self.account.has_money(50))
        self.assertFalse(self.account.has_money(51))

        self._create_outcoming_invoice(amount=-60)

        self.assertTrue(self.account.has_money(50))
        self.assertFalse(self.account.has_money(51))

    def test_has_money__all_money_freezed(self):
        self.account.amount = 10000
        self._create_incoming_invoice(amount=1)
        self._create_incoming_invoice(amount=-10)
        self._create_outcoming_invoice(amount=100)
        self._create_outcoming_invoice(amount=-1000)

        self.assertTrue(self.account.has_money(10000 - 10 - 100))
        self.assertFalse(self.account.has_money(10000 - 10 - 100 + 1))

    def test_get_history_list(self):

        invoices = self.create_entity_history(self.account.entity_id)

        self.assertEqual([invoice.id for invoice in self.account.get_history_list()],
                         [invoice.id for invoice in invoices])


class InvoicePrototypeTests(utils_testcase.TestCase, helpers.BankTestsMixin):

    def setUp(self):
        super(InvoicePrototypeTests, self).setUp()
        self.recipient_id = 3
        self.sender_id = 8
        self.amount = 317

    def test_create(self):
        invoice = self.create_invoice()

        self.assertTrue(invoice.recipient_type.is_GAME_ACCOUNT)
        self.assertEqual(invoice.recipient_id, self.recipient_id)
        self.assertTrue(invoice.sender_type.is_GAME_LOGIC)
        self.assertEqual(invoice.sender_id, self.sender_id)
        self.assertEqual(invoice.amount, self.amount)
        self.assertTrue(invoice.state.is_REQUESTED)
        self.assertTrue(invoice.currency.is_PREMIUM)

    def test_create__forced(self):
        invoice = self.create_invoice(force=True)

        self.assertTrue(invoice.recipient_type.is_GAME_ACCOUNT)
        self.assertEqual(invoice.recipient_id, self.recipient_id)
        self.assertTrue(invoice.sender_type.is_GAME_LOGIC)
        self.assertEqual(invoice.sender_id, self.sender_id)
        self.assertEqual(invoice.amount, self.amount)
        self.assertTrue(invoice.state.is_FORCED)
        self.assertTrue(invoice.currency.is_PREMIUM)

    def check_freeze(self, recipient_type, sender_type, amount, initial_accounts_number=0, recipient_amount=0, sender_amount=0):
        self.assertEqual(prototypes.AccountPrototype._model_class.objects.all().count(), initial_accounts_number)

        invoice = self.create_invoice(recipient_type=recipient_type, sender_type=sender_type, amount=amount)
        invoice.freeze()
        self.assertTrue(invoice.state.is_FROZEN)

        self.assertEqual(prototypes.AccountPrototype._model_class.objects.all().count(), 2)

        recipient = prototypes.AccountPrototype(model=prototypes.AccountPrototype._model_class.objects.all().order_by('created_at')[0])
        self.assertEqual(recipient.amount, recipient_amount)
        self.assertEqual(recipient.entity_type, recipient_type)
        self.assertEqual(recipient.entity_id, self.recipient_id)
        self.assertTrue(recipient.currency.is_PREMIUM)

        sender = prototypes.AccountPrototype(model=prototypes.AccountPrototype._model_class.objects.all().order_by('created_at')[1])
        self.assertEqual(sender.amount, sender_amount)
        self.assertEqual(sender.entity_type, sender_type)
        self.assertEqual(sender.entity_id, self.sender_id)
        self.assertTrue(sender.currency.is_PREMIUM)

    def test_freeze__for_infinite_sender(self):
        self.check_freeze(recipient_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                          sender_type=relations.ENTITY_TYPE.GAME_LOGIC,
                          amount=100,
                          recipient_amount=0,
                          sender_amount=conf.settings.INFINIT_MONEY_AMOUNT)

    def test_freeze__for_infinite_recipient(self):
        self.check_freeze(recipient_type=relations.ENTITY_TYPE.GAME_LOGIC,
                          sender_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                          amount=-100,
                          recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                          sender_amount=0)

    def test_freeze__for_infinite_both(self):
        self.check_freeze(recipient_type=relations.ENTITY_TYPE.GAME_LOGIC,
                          sender_type=relations.ENTITY_TYPE.GAME_LOGIC,
                          amount=100,
                          recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                          sender_amount=conf.settings.INFINIT_MONEY_AMOUNT)
        self.check_freeze(recipient_type=relations.ENTITY_TYPE.GAME_LOGIC,
                          sender_type=relations.ENTITY_TYPE.GAME_LOGIC,
                          amount=-100,
                          initial_accounts_number=2,
                          recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                          sender_amount=conf.settings.INFINIT_MONEY_AMOUNT)

    def test_freeze__for_noninfinite_both(self):
        recipient = prototypes.AccountPrototype.create(entity_type=relations.ENTITY_TYPE.GAME_ACCOUNT, entity_id=self.recipient_id, currency=relations.CURRENCY_TYPE.PREMIUM)
        recipient.amount = 100
        recipient.save()

        sender = prototypes.AccountPrototype.create(entity_type=relations.ENTITY_TYPE.GAME_ACCOUNT, entity_id=self.sender_id, currency=relations.CURRENCY_TYPE.PREMIUM)
        sender.amount = 100
        sender.save()

        self.check_freeze(recipient_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                          sender_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                          amount=100,
                          initial_accounts_number=2,
                          recipient_amount=100,
                          sender_amount=100)

        self.check_freeze(recipient_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                          sender_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                          amount=-50,
                          initial_accounts_number=2,
                          recipient_amount=100,
                          sender_amount=100)

    def check_reject(self, recipient_type, sender_type, amount, initial_accounts_number=0, processed_accounts_number=2, recipient_amount=0, sender_amount=0):
        self.assertEqual(prototypes.AccountPrototype._model_class.objects.all().count(), initial_accounts_number)

        invoice = self.create_invoice(recipient_type=recipient_type, sender_type=sender_type, amount=amount)
        invoice.freeze()
        self.assertTrue(invoice.state.is_REJECTED)

        self.assertEqual(prototypes.AccountPrototype._model_class.objects.all().count(), processed_accounts_number)

        if processed_accounts_number == 0:
            return

        recipient = prototypes.AccountPrototype(model=prototypes.AccountPrototype._model_class.objects.all().order_by('created_at')[0])
        self.assertEqual(recipient.amount, recipient_amount)
        self.assertEqual(recipient.entity_type, recipient_type)
        self.assertEqual(recipient.entity_id, self.recipient_id)
        self.assertTrue(recipient.currency.is_PREMIUM)

        if processed_accounts_number == 1:
            return

        sender = prototypes.AccountPrototype(model=prototypes.AccountPrototype._model_class.objects.all().order_by('created_at')[1])
        self.assertEqual(sender.amount, sender_amount)
        self.assertEqual(sender.entity_type, sender_type)
        self.assertEqual(sender.entity_id, self.sender_id)
        self.assertTrue(sender.currency.is_PREMIUM)

    def test_freeze__reject_for_infinit_recipient(self):
        self.check_reject(recipient_type=relations.ENTITY_TYPE.GAME_LOGIC,
                          sender_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                          amount=100,
                          recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                          sender_amount=0,
                          processed_accounts_number=2)

    def test_freeze__reject_for_infinit_sender(self):
        self.check_reject(recipient_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                          sender_type=relations.ENTITY_TYPE.GAME_LOGIC,
                          amount=-100,
                          recipient_amount=0,
                          processed_accounts_number=1)

    def test_freeze__reject_for_infinit_both(self):
        # always successed
        pass

    def test_freeze__reject_for_noninfinit_both(self):
        self.check_reject(recipient_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                          sender_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                          amount=-50,
                          processed_accounts_number=1)

        self.check_reject(recipient_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                          sender_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                          amount=100,
                          initial_accounts_number=1,
                          processed_accounts_number=2)

    def test_reject__not_reqested_state(self):
        invoice = self.create_invoice()
        invoice.state = relations.INVOICE_STATE.CONFIRMED
        self.assertRaises(exceptions.BankError, invoice.freeze)

    def check_confirm(self, recipient_type, sender_type, initial_recipient_amount, initial_sender_amount, amount, result_recipient_amount, result_sender_amount):
        recipient = prototypes.AccountPrototype.get_for_or_create(entity_type=recipient_type, entity_id=self.recipient_id, currency=relations.CURRENCY_TYPE.PREMIUM)
        recipient.amount = initial_recipient_amount
        recipient.save()

        sender = prototypes.AccountPrototype.get_for_or_create(entity_type=sender_type, entity_id=self.sender_id, currency=relations.CURRENCY_TYPE.PREMIUM)
        sender.amount = initial_sender_amount
        sender.save()

        invoice = self.create_invoice(recipient_type=recipient_type,
                                      recipient_id=self.recipient_id,
                                      sender_type=sender_type,
                                      sender_id=self.sender_id,
                                      amount=amount)
        invoice.freeze()
        self.assertTrue(invoice.state.is_FROZEN)

        recipient.reload()
        sender.reload()

        self.assertEqual(recipient.amount, initial_recipient_amount)
        self.assertEqual(sender.amount, initial_sender_amount)

        invoice.confirm()

        recipient.reload()
        sender.reload()

        self.assertEqual(recipient.amount, result_recipient_amount)
        self.assertEqual(sender.amount, result_sender_amount)

        self.assertTrue(invoice.state.is_CONFIRMED)

    def test_confirm__noninfinit(self):
        self.check_confirm(recipient_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                           sender_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                           initial_recipient_amount=1000,
                           initial_sender_amount=1000,
                           amount=299,
                           result_recipient_amount=1299,
                           result_sender_amount=701)

        self.check_confirm(recipient_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                           sender_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                           initial_recipient_amount=1000,
                           initial_sender_amount=1000,
                           amount=-299,
                           result_recipient_amount=701,
                           result_sender_amount=1299)

    def test_confirm__infinit_sender(self):
        self.check_confirm(recipient_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                           sender_type=relations.ENTITY_TYPE.GAME_LOGIC,
                           initial_recipient_amount=1000,
                           initial_sender_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           amount=299,
                           result_recipient_amount=1299,
                           result_sender_amount=conf.settings.INFINIT_MONEY_AMOUNT)

        self.check_confirm(recipient_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                           sender_type=relations.ENTITY_TYPE.GAME_LOGIC,
                           initial_recipient_amount=1000,
                           initial_sender_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           amount=-299,
                           result_recipient_amount=701,
                           result_sender_amount=conf.settings.INFINIT_MONEY_AMOUNT)

    def test_confirm__infinit_recipient(self):
        self.check_confirm(recipient_type=relations.ENTITY_TYPE.GAME_LOGIC,
                           sender_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                           initial_recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           initial_sender_amount=1000,
                           amount=299,
                           result_recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           result_sender_amount=701)

        self.check_confirm(recipient_type=relations.ENTITY_TYPE.GAME_LOGIC,
                           sender_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                           initial_recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           initial_sender_amount=1000,
                           amount=-299,
                           result_recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           result_sender_amount=1299)

    def test_confirm__infinit_both(self):
        self.check_confirm(recipient_type=relations.ENTITY_TYPE.GAME_LOGIC,
                           sender_type=relations.ENTITY_TYPE.GAME_LOGIC,
                           initial_recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           initial_sender_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           amount=299,
                           result_recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           result_sender_amount=conf.settings.INFINIT_MONEY_AMOUNT)

        self.check_confirm(recipient_type=relations.ENTITY_TYPE.GAME_LOGIC,
                           sender_type=relations.ENTITY_TYPE.GAME_LOGIC,
                           initial_recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           initial_sender_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           amount=-299,
                           result_recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           result_sender_amount=conf.settings.INFINIT_MONEY_AMOUNT)

    def test_confirm__not_frozen_state(self):
        invoice = self.create_invoice()
        self.assertRaises(exceptions.BankError, invoice.confirm)

    def check_force(self, recipient_type, sender_type, initial_recipient_amount, initial_sender_amount, amount, result_recipient_amount, result_sender_amount):

        invoice = self.create_invoice(recipient_type=recipient_type, sender_type=sender_type, amount=amount)
        invoice.freeze()
        self.assertTrue(invoice.state.is_FROZEN)

        self.assertEqual(prototypes.AccountPrototype._model_class.objects.all().count(), 2)

        recipient = prototypes.AccountPrototype(model=prototypes.AccountPrototype._model_class.objects.all().order_by('created_at')[0])
        self.assertEqual(recipient.amount, initial_recipient_amount)
        self.assertEqual(recipient.entity_type, recipient_type)
        self.assertEqual(recipient.entity_id, self.recipient_id)
        self.assertTrue(recipient.currency.is_PREMIUM)

        sender = prototypes.AccountPrototype(model=prototypes.AccountPrototype._model_class.objects.all().order_by('created_at')[1])
        self.assertEqual(sender.amount, initial_sender_amount)
        self.assertEqual(sender.entity_type, sender_type)
        self.assertEqual(sender.entity_id, self.sender_id)
        self.assertTrue(sender.currency.is_PREMIUM)

        invoice = self.create_invoice(recipient_type=recipient_type,
                                      recipient_id=self.recipient_id,
                                      sender_type=sender_type,
                                      sender_id=self.sender_id,
                                      amount=amount,
                                      force=True)
        invoice.force()
        self.assertTrue(invoice.state.is_CONFIRMED)

        recipient.reload()
        sender.reload()

        self.assertEqual(recipient.amount, result_recipient_amount)
        self.assertEqual(sender.amount, result_sender_amount)

    def test_force__noninfinit(self):
        self.check_confirm(recipient_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                           sender_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                           initial_recipient_amount=1000,
                           initial_sender_amount=1000,
                           amount=299,
                           result_recipient_amount=1299,
                           result_sender_amount=701)

        self.check_confirm(recipient_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                           sender_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                           initial_recipient_amount=1000,
                           initial_sender_amount=1000,
                           amount=-299,
                           result_recipient_amount=701,
                           result_sender_amount=1299)

    def test_force__infinit_sender(self):
        self.check_confirm(recipient_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                           sender_type=relations.ENTITY_TYPE.GAME_LOGIC,
                           initial_recipient_amount=1000,
                           initial_sender_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           amount=299,
                           result_recipient_amount=1299,
                           result_sender_amount=conf.settings.INFINIT_MONEY_AMOUNT)

        self.check_confirm(recipient_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                           sender_type=relations.ENTITY_TYPE.GAME_LOGIC,
                           initial_recipient_amount=1000,
                           initial_sender_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           amount=-299,
                           result_recipient_amount=701,
                           result_sender_amount=conf.settings.INFINIT_MONEY_AMOUNT)

    def test_force__infinit_recipient(self):
        self.check_confirm(recipient_type=relations.ENTITY_TYPE.GAME_LOGIC,
                           sender_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                           initial_recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           initial_sender_amount=1000,
                           amount=299,
                           result_recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           result_sender_amount=701)

        self.check_confirm(recipient_type=relations.ENTITY_TYPE.GAME_LOGIC,
                           sender_type=relations.ENTITY_TYPE.GAME_ACCOUNT,
                           initial_recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           initial_sender_amount=1000,
                           amount=-299,
                           result_recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           result_sender_amount=1299)

    def test_force__infinit_both(self):
        self.check_confirm(recipient_type=relations.ENTITY_TYPE.GAME_LOGIC,
                           sender_type=relations.ENTITY_TYPE.GAME_LOGIC,
                           initial_recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           initial_sender_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           amount=299,
                           result_recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           result_sender_amount=conf.settings.INFINIT_MONEY_AMOUNT)

        self.check_confirm(recipient_type=relations.ENTITY_TYPE.GAME_LOGIC,
                           sender_type=relations.ENTITY_TYPE.GAME_LOGIC,
                           initial_recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           initial_sender_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           amount=-299,
                           result_recipient_amount=conf.settings.INFINIT_MONEY_AMOUNT,
                           result_sender_amount=conf.settings.INFINIT_MONEY_AMOUNT)

    def test_force__not_frozen_state(self):
        invoice = self.create_invoice()
        self.assertRaises(exceptions.BankError, invoice.confirm)

    def test_cancel(self):
        invoice = self.create_invoice()
        invoice.freeze()
        invoice.cancel()
        self.assertTrue(invoice.state.is_CANCELED)

    def test_cancel__raise_if_wrong_state(self):
        invoice = self.create_invoice()
        invoice.state = relations.INVOICE_STATE.random(exclude=(relations.INVOICE_STATE.REQUESTED,
                                                                relations.INVOICE_STATE.FROZEN,
                                                                relations.INVOICE_STATE.REJECTED))
        self.assertRaises(exceptions.BankError, invoice.cancel)

    def test_cancel__do_nothing_if_rejected(self):
        invoice = self.create_invoice()
        invoice.state = relations.INVOICE_STATE.REJECTED

        invoice.cancel()

        self.assertTrue(invoice.state.is_REJECTED)

    def test_reset_all(self):
        for state in relations.INVOICE_STATE.records:
            invoice = self.create_invoice()
            invoice.state = state
            invoice.save()

        prototypes.InvoicePrototype.reset_all()

        self.assertEqual(prototypes.InvoicePrototype._model_class.objects.filter(state=relations.INVOICE_STATE.RESETED).count(), len(relations.INVOICE_STATE.records) - 4)
        self.assertEqual(prototypes.InvoicePrototype._model_class.objects.filter(state=relations.INVOICE_STATE.CONFIRMED).count(), 1)
        self.assertEqual(prototypes.InvoicePrototype._model_class.objects.filter(state=relations.INVOICE_STATE.CANCELED).count(), 1)
        self.assertEqual(prototypes.InvoicePrototype._model_class.objects.filter(state=relations.INVOICE_STATE.REJECTED).count(), 1)
        self.assertEqual(prototypes.InvoicePrototype._model_class.objects.filter(state=relations.INVOICE_STATE.FORCED).count(), 1)

    def test_get_unprocessed_invoice_success(self):
        for state in relations.INVOICE_STATE.records:
            if not (state.is_REQUESTED or state.is_FORCED):
                continue

            invoice = self.create_invoice(state=state)
            self.assertEqual(prototypes.InvoicePrototype.get_unprocessed_invoice().id, invoice.id)
            prototypes.InvoicePrototype._db_all().delete()

    def test_get_unprocessed_invoice__no_invoice(self):
        for state in relations.INVOICE_STATE.records:
            if state.is_REQUESTED or state.is_FORCED:
                continue
            self.create_invoice(state=state)

        self.assertEqual(prototypes.InvoicePrototype.get_unprocessed_invoice(), None)

    def test_check_frozen_expired_invoices__wrong_state(self):
        for state in relations.INVOICE_STATE.records:
            if state.is_FROZEN:
                continue

            self.create_invoice(state=state)
            self.assertFalse(prototypes.InvoicePrototype.check_frozen_expired_invoices())
            prototypes.InvoicePrototype._db_all().delete()

    def test_check_frozen_expired_invoices__wrong_time(self):
        self.create_invoice(state=relations.INVOICE_STATE.FROZEN)
        self.assertFalse(prototypes.InvoicePrototype.check_frozen_expired_invoices())

    def test_check_frozen_expired_invoices__exist(self):
        invoice = self.create_invoice(state=relations.INVOICE_STATE.FROZEN)
        prototypes.InvoicePrototype._db_filter(id=invoice.id).update(updated_at=datetime.datetime.now() - conf.settings.FROZEN_INVOICE_EXPIRED_TIME)
        self.assertTrue(prototypes.InvoicePrototype.check_frozen_expired_invoices())
