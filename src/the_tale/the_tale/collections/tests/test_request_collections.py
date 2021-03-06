
import smart_imports

smart_imports.all()


class BaseRequestTests(utils_testcase.TestCase):

    def setUp(self):
        super(BaseRequestTests, self).setUp()

        game_logic.create_test_map()

        self.account_1 = self.accounts_factory.create_account()
        self.account_2 = self.accounts_factory.create_account()
        self.account_3 = self.accounts_factory.create_account()
        self.account_4 = self.accounts_factory.create_account()

        self.account_1_items = prototypes.AccountItemsPrototype.get_by_account_id(self.account_1.id)
        self.account_2_items = prototypes.AccountItemsPrototype.get_by_account_id(self.account_2.id)
        self.account_3_items = prototypes.AccountItemsPrototype.get_by_account_id(self.account_3.id)

        group_edit_kit = utils_permissions.sync_group('edit kit', ['collections.edit_kit'])
        group_edit = utils_permissions.sync_group('edit collection', ['collections.edit_collection'])
        group_edit_item = utils_permissions.sync_group('edit item', ['collections.edit_item'])
        group_moderate = utils_permissions.sync_group('moderate collection', ['collections.moderate_collection'])
        group_moderate_kit = utils_permissions.sync_group('moderate kit', ['collections.moderate_kit'])
        group_moderate_item = utils_permissions.sync_group('moderate item', ['collections.moderate_item'])

        group_edit_kit.user_set.add(self.account_2._model)
        group_edit.user_set.add(self.account_2._model)
        group_edit_item.user_set.add(self.account_2._model)
        group_moderate.user_set.add(self.account_3._model)
        group_moderate_kit.user_set.add(self.account_3._model)
        group_moderate_item.user_set.add(self.account_3._model)

        self.collection_1 = prototypes.CollectionPrototype.create(caption='collection_1', description='description_1')
        self.collection_2 = prototypes.CollectionPrototype.create(caption='collection_2', description='description_2', approved=True)

        self.kit_1 = prototypes.KitPrototype.create(collection=self.collection_1, caption='kit_1', description='description_1')
        self.kit_2 = prototypes.KitPrototype.create(collection=self.collection_2, caption='kit_2', description='description_2', approved=True)

        self.item_1_1 = prototypes.ItemPrototype.create(kit=self.kit_1, caption='item_1_1', text='item_text_1_1')
        self.item_1_2 = prototypes.ItemPrototype.create(kit=self.kit_1, caption='item_1_2', text='item_text_1_2', approved=True)
        self.item_2_1 = prototypes.ItemPrototype.create(kit=self.kit_2, caption='item_2_1', text='item_text_2_1', approved=True)


class CollectionVisibilityAllMixin(object):

    def test_visible_collections__all(self):
        self.request_login(self.account_2.email)
        self.check_html_ok(self.request_html(self.test_url), texts=[self.collection_1.caption,
                                                                    self.collection_2.caption])


class CollectionVisibilityApprovedMixin(CollectionVisibilityAllMixin):

    def test_visible_collections__aproved_only(self):
        self.request_login(self.account_1.email)
        self.check_html_ok(self.request_html(self.test_url), texts=[(self.collection_1.caption, 0),
                                                                    self.collection_2.caption])


class CollectionsIndexTests(BaseRequestTests, CollectionVisibilityAllMixin):

    def setUp(self):
        super(CollectionsIndexTests, self).setUp()
        self.test_url = utils_urls.url('collections:collections:', account=self.account_1.id)

    def test_redirect__redirect(self):
        self.request_login(self.account_3.email)
        self.check_redirect(utils_urls.url('collections:collections:'), utils_urls.url('collections:collections:', account=self.account_3.id))

    def test_success__moderator(self):
        self.request_login(self.account_2.email)
        self.check_html_ok(self.request_html(self.test_url),
                           texts=[('pgf-add-collection-button', 1),
                                  self.collection_1.caption,
                                  self.collection_2.caption])

    def test_without_account(self):
        self.check_html_ok(self.request_html(utils_urls.url('collections:collections:')),
                           texts=[('pgf-add-collection-button', 0),
                                  ('pgf-last-items', 0),
                                  (self.collection_1.caption, 0),
                                  self.collection_2.caption])

    def test_account__no_last_items(self):
        self.check_html_ok(self.request_html(self.test_url),
                           texts=[('pgf-add-collection-button', 0),
                                  ('pgf-last-items', 1),
                                  ('pgf-no-last-items-message', 1)])

    def test_account__has_last_items(self):
        self.account_1_items.add_item(self.item_2_1)
        self.account_1_items.save()

        self.check_html_ok(self.request_html(self.test_url),
                           texts=[('collections.collections.no_edit_rights', 0),
                                  ('pgf-last-items', 1),
                                  ('pgf-no-last-items-message', 0),
                                  ('item_2_1', 1)])

    def test_last_items__anonymous(self):
        self.account_1_items.add_item(self.item_2_1)
        self.account_1_items.save()

        self.check_html_ok(self.request_html(self.test_url),
                           texts=[('collections.collections.no_edit_rights', 0),
                                  ('pgf-last-items', 1),
                                  ('pgf-no-last-items-message', 0),
                                  ('item_2_1', 1),
                                  ('item_text_2_1', 0)])

    def test_last_items__account_without_item(self):
        self.account_1_items.add_item(self.item_2_1)
        self.account_1_items.save()

        self.request_login(self.account_4.email)
        self.check_html_ok(self.request_html(self.test_url),
                           texts=[('collections.collections.no_edit_rights', 0),
                                  ('pgf-last-items', 1),
                                  ('pgf-no-last-items-message', 0),
                                  ('item_2_1', 1),
                                  ('item_text_2_1', 0)])

    def test_last_items__account_with_item(self):
        self.account_1_items.add_item(self.item_2_1)
        self.account_3_items.add_item(self.item_2_1)

        self.account_1_items.save()
        self.account_3_items.save()

        self.request_login(self.account_3.email)
        self.check_html_ok(self.request_html(self.test_url),
                           texts=[('collections.collections.no_edit_rights', 0),
                                  ('pgf-last-items', 1),
                                  ('pgf-no-last-items-message', 0),
                                  ('item_2_1', 1),
                                  ('item_text_2_1', 1)])

    def test_last_items__editor(self):
        self.account_1_items.add_item(self.item_2_1)
        self.account_1_items.save()

        self.request_login(self.account_2.email)
        self.check_html_ok(self.request_html(self.test_url),
                           texts=[('collections.collections.no_edit_rights', 0),
                                  ('pgf-last-items', 1),
                                  ('pgf-no-last-items-message', 0),
                                  ('item_2_1', 1),
                                  ('item_text_2_1', 1)])


class CollectionsNewTests(BaseRequestTests, CollectionVisibilityAllMixin):

    def setUp(self):
        super(CollectionsNewTests, self).setUp()
        self.test_url = utils_urls.url('collections:collections:new')

    def test_login_required(self):
        self.check_redirect(self.test_url, accounts_logic.login_page_url(self.test_url))

    def test_edit_rights_required(self):
        self.request_login(self.account_1.email)
        self.check_html_ok(self.request_html(self.test_url),
                           texts=[('collections.collections.no_edit_rights', 1)])

    def test_success(self):
        self.request_login(self.account_2.email)
        self.check_html_ok(self.request_html(self.test_url),
                           texts=[('collections.collections.no_edit_rights', 0)])


class CollectionsCreateTests(BaseRequestTests):

    def setUp(self):
        super(CollectionsCreateTests, self).setUp()
        self.test_url = utils_urls.url('collections:collections:create')

    def get_post_data(self):
        return {'caption': 'caption_3',
                'description': 'description_3'}

    def test_login_required(self):
        self.check_ajax_error(self.post_ajax_json(self.test_url, self.get_post_data()),
                              'common.login_required')
        self.assertEqual(prototypes.CollectionPrototype._db_all().count(), 2)

    def test_edit_rights_required(self):
        self.request_login(self.account_1.email)
        self.check_ajax_error(self.post_ajax_json(self.test_url, self.get_post_data()),
                              'collections.collections.no_edit_rights')
        self.assertEqual(prototypes.CollectionPrototype._db_all().count(), 2)

    def test_form_errors(self):
        self.request_login(self.account_2.email)
        self.check_ajax_error(self.post_ajax_json(self.test_url, {}),
                              'collections.collections.create.form_errors')
        self.assertEqual(prototypes.CollectionPrototype._db_all().count(), 2)

    def test_success(self):
        self.request_login(self.account_2.email)

        self.check_ajax_ok(self.post_ajax_json(self.test_url, self.get_post_data()))
        self.assertEqual(prototypes.CollectionPrototype._db_all().count(), 3)

        collection = prototypes.CollectionPrototype._db_get_object(2)

        self.assertFalse(collection.approved)
        self.assertEqual(collection.caption, 'caption_3')
        self.assertEqual(collection.description, 'description_3')


class CollectionsShowTests(BaseRequestTests, CollectionVisibilityApprovedMixin):

    def setUp(self):
        super(CollectionsShowTests, self).setUp()
        self.test_url = utils_urls.url('collections:collections:show', self.collection_2.id, account=self.account_1.id)

    def test_redirect__redirect(self):
        self.request_login(self.account_3.email)
        self.check_redirect(utils_urls.url('collections:collections:show', self.collection_2.id), utils_urls.url('collections:collections:show', self.collection_2.id, account=self.account_3.id))

    def test_success__no_approved_kits(self):
        prototypes.KitPrototype._db_all().update(approved=False)
        storage.kits.refresh()

        self.check_html_ok(self.request_html(self.test_url),
                           texts=[self.collection_2.caption,
                                  (self.kit_2.caption, 0),
                                  (self.collection_1.caption, 0),
                                  (self.kit_1.caption, 0),
                                  ('pgf-no-kits-message', 1)])

    def test_success(self):
        self.request_login(self.account_2.email)
        self.check_html_ok(self.request_html(self.test_url),
                           texts=[self.collection_2.caption,
                                  self.kit_2.caption,
                                  (self.kit_1.caption, 0),
                                  ('pgf-no-kits-message', 0)])

    def test_access_restricted(self):
        self.check_html_ok(self.request_html(utils_urls.url('collections:collections:show', self.collection_1.id)),
                           status_code=404,
                           texts=[(self.collection_1.caption, 0),
                                  (self.kit_1.caption, 0),
                                  (self.collection_2.caption, 0),
                                  (self.kit_2.caption, 0),
                                  ('pgf-no-kits-message', 0),
                                  ('collections.collections.not_approved', 1)])

    def test_no_kits_in_collection(self):
        prototypes.ItemPrototype._db_all().delete()
        prototypes.KitPrototype._db_all().delete()

        storage.items.refresh()
        storage.kits.refresh()

        self.check_html_ok(self.request_html(self.test_url),
                           texts=[self.collection_2.caption,
                                  (self.kit_2.caption, 0),
                                  (self.collection_1.caption, 0),
                                  (self.kit_1.caption, 0),
                                  ('pgf-no-kits-message', 1)])

    def test_buttons__anonymouse(self):
        self.check_html_ok(self.request_html(self.test_url), texts=[('pgf-new-kit-button', 0),
                                                                    ('pgf-edit-collection-button', 0),
                                                                    ('pgf-approve-collection-button', 0),
                                                                    ('pgf-new-item-button', 0),
                                                                    ('pgf-edit-kit-button', 0),
                                                                    ('pgf-approve-kit-button', 0),
                                                                    ('pgf-disapprove-kit-button', 0),
                                                                    ('pgf-edit-item-button', 0),
                                                                    ('pgf-approve-item-button', 0),
                                                                    ('pgf-disapprove-item-button', 0),
                                                                    ('pgf-disapprove-collection-button', 0)])

    def test_buttons__no_rights(self):
        self.check_html_ok(self.request_html(self.test_url), texts=[('pgf-new-kit-button', 0),
                                                                    ('pgf-edit-collection-button', 0),
                                                                    ('pgf-approve-collection-button', 0),
                                                                    ('pgf-new-item-button', 0),
                                                                    ('pgf-edit-kit-button', 0),
                                                                    ('pgf-approve-kit-button', 0),
                                                                    ('pgf-disapprove-kit-button', 0),
                                                                    ('pgf-edit-item-button', 0),
                                                                    ('pgf-approve-item-button', 0),
                                                                    ('pgf-disapprove-item-button', 0),
                                                                    ('pgf-disapprove-collection-button', 0)])

    def test_buttons__edit_rights(self):
        self.request_login(self.account_2.email)
        self.check_html_ok(self.request_html(self.test_url), texts=[('pgf-new-kit-button', 1),
                                                                    ('pgf-edit-collection-button', 0),
                                                                    ('pgf-approve-collection-button', 0),
                                                                    ('pgf-new-item-button', 1),
                                                                    ('pgf-edit-kit-button', 1),
                                                                    ('pgf-approve-kit-button', 0),
                                                                    ('pgf-disapprove-kit-button', 0),
                                                                    ('pgf-edit-item-button', 0),
                                                                    ('pgf-approve-item-button', 0),
                                                                    ('pgf-disapprove-item-button', 0),
                                                                    ('pgf-disapprove-collection-button', 0)])

        self.collection_2.approved = False
        self.collection_2.save()

        self.check_html_ok(self.request_html(self.test_url), texts=[('pgf-new-kit-button', 1),
                                                                    ('pgf-edit-collection-button', 1),
                                                                    ('pgf-approve-collection-button', 0),
                                                                    ('pgf-new-item-button', 1),
                                                                    ('pgf-edit-kit-button', 1),
                                                                    ('pgf-approve-kit-button', 0),
                                                                    ('pgf-disapprove-kit-button', 0),
                                                                    ('pgf-edit-item-button', 0),
                                                                    ('pgf-approve-item-button', 0),
                                                                    ('pgf-disapprove-item-button', 0),
                                                                    ('pgf-disapprove-collection-button', 0)])

    def test_buttons__moderate_rights(self):
        self.request_login(self.account_3.email)
        self.check_html_ok(self.request_html(self.test_url), texts=[('pgf-new-kit-button', 1),
                                                                    ('pgf-edit-collection-button', 1),
                                                                    ('pgf-approve-collection-button', 0),
                                                                    ('pgf-new-item-button', 1),
                                                                    ('pgf-edit-kit-button', 1),
                                                                    ('pgf-approve-kit-button', 0),
                                                                    ('pgf-disapprove-kit-button', 1),
                                                                    ('pgf-edit-item-button', 1),
                                                                    ('pgf-approve-item-button', 0),
                                                                    ('pgf-disapprove-item-button', 1),
                                                                    ('pgf-disapprove-collection-button', 1)])
        self.collection_2.approved = False
        self.collection_2.save()

        self.kit_2.approved = False
        self.kit_2.save()

        self.item_2_1.approved = False
        self.item_2_1.save()

        self.check_html_ok(self.request_html(self.test_url), texts=[('pgf-new-kit-button', 1),
                                                                    ('pgf-edit-collection-button', 1),
                                                                    ('pgf-approve-collection-button', 1),
                                                                    ('pgf-new-item-button', 1),
                                                                    ('pgf-edit-kit-button', 1),
                                                                    ('pgf-approve-kit-button', 1),
                                                                    ('pgf-disapprove-kit-button', 0),
                                                                    ('pgf-edit-item-button', 1),
                                                                    ('pgf-approve-item-button', 1),
                                                                    ('pgf-disapprove-item-button', 0),
                                                                    ('pgf-disapprove-collection-button', 0)])

    def test_item_show__anonymous(self):
        self.account_1_items.add_item(self.item_2_1)
        self.account_1_items.save()

        self.check_html_ok(self.request_html(self.test_url), texts=[self.item_2_1.caption,
                                                                    (self.item_2_1.text, 0)])

    def test_item_show__account_without_item(self):

        self.account_1_items.add_item(self.item_2_1)
        self.account_1_items.save()

        self.request_login(self.account_4.email)

        self.check_html_ok(self.request_html(self.test_url), texts=[self.item_2_1.caption,
                                                                    (self.item_2_1.text, 0)])

    def test_item_show__account_with_item(self):
        self.account_1_items.add_item(self.item_2_1)
        self.account_1_items.save()

        self.account_3_items.add_item(self.item_2_1)
        self.account_3_items.save()

        self.request_login(self.account_3.email)

        self.check_html_ok(self.request_html(self.test_url), texts=[self.item_2_1.caption,
                                                                    self.item_2_1.text])

    def test_item_show__moderator(self):
        self.account_1_items.add_item(self.item_2_1)
        self.account_1_items.save()

        self.request_login(self.account_2.email)

        self.check_html_ok(self.request_html(self.test_url), texts=[self.item_2_1.caption,
                                                                    self.item_2_1.text])

    def test_unapproved_item__anonymous(self):
        item = prototypes.ItemPrototype.create(kit=self.kit_2, caption='item_2_2', text='item_text_2_2', approved=False)

        self.account_1_items.add_item(item)
        self.account_1_items.save()

        self.check_html_ok(self.request_html(self.test_url), texts=[(item.caption, 0),
                                                                    (item.text, 0)])

    def test_unapproved_item__loginned(self):
        item = prototypes.ItemPrototype.create(kit=self.kit_2, caption='item_2_2', text='item_text_2_2', approved=False)

        self.account_1_items.add_item(item)
        self.account_1_items.save()

        self.request_login(self.account_1.email)

        self.check_html_ok(self.request_html(self.test_url), texts=[(item.caption, 0),
                                                                    (item.text, 0)])

    def test_unapproved_item__moderator(self):
        item = prototypes.ItemPrototype.create(kit=self.kit_2, caption='item_2_2', text='item_text_2_2', approved=False)

        self.account_1_items.add_item(item)
        self.account_1_items.save()

        self.request_login(self.account_2.email)

        self.check_html_ok(self.request_html(self.test_url), texts=[(item.caption, 1),
                                                                    (item.text, 1)])


class CollectionsEditTests(BaseRequestTests, CollectionVisibilityAllMixin):

    def setUp(self):
        super(CollectionsEditTests, self).setUp()
        self.test_url = utils_urls.url('collections:collections:edit', self.collection_1.id)

    def test_login_required(self):
        self.check_redirect(self.test_url, accounts_logic.login_page_url(self.test_url))

    def test_edit_rights_required(self):
        self.request_login(self.account_1.email)
        self.check_html_ok(self.request_html(self.test_url),
                           texts=(('collections.collections.no_edit_rights', 1)))

    def test_moderate_rights_required(self):
        prototypes.CollectionPrototype._db_all().update(approved=True)
        storage.collections.refresh()

        self.request_login(self.account_2.email)
        self.check_html_ok(self.request_html(self.test_url),
                           texts=(('collections.collections.no_edit_rights', 1)))

    def test_success__for_edit(self):
        self.request_login(self.account_2.email)
        self.check_html_ok(self.request_html(self.test_url),
                           texts=[self.collection_1.caption,
                                  self.collection_1.description])

    def test_success__for_moderate(self):
        prototypes.CollectionPrototype._db_all().update(approved=True)
        storage.collections.refresh()

        self.request_login(self.account_3.email)
        self.check_html_ok(self.request_html(self.test_url),
                           texts=[self.collection_1.caption,
                                  self.collection_1.description])


class CollectionsUpdateTests(BaseRequestTests):

    def setUp(self):
        super(CollectionsUpdateTests, self).setUp()
        self.test_url = utils_urls.url('collections:collections:update', self.collection_1.id)

    def get_post_data(self):
        return {'caption': 'collection_edited',
                'description': 'description_edited'}

    def test_login_required(self):
        self.check_ajax_error(self.post_ajax_json(self.test_url, self.get_post_data()), 'common.login_required')

    def test_edit_rights_required(self):
        self.request_login(self.account_1.email)
        self.check_ajax_error(self.post_ajax_json(self.test_url, self.get_post_data()),
                              'collections.collections.no_edit_rights')

        self.collection_1.reload()
        self.assertEqual(self.collection_1.caption, 'collection_1')
        self.assertEqual(self.collection_1.description, 'description_1')

    def test_moderate_rights_required(self):
        prototypes.CollectionPrototype._db_all().update(approved=True)
        storage.collections.refresh()

        self.request_login(self.account_2.email)
        self.check_ajax_error(self.post_ajax_json(self.test_url, self.get_post_data()),
                              'collections.collections.no_edit_rights')
        self.collection_1.reload()
        self.assertEqual(self.collection_1.caption, 'collection_1')
        self.assertEqual(self.collection_1.description, 'description_1')

    def test_form_errors(self):
        self.request_login(self.account_2.email)
        self.check_ajax_error(self.post_ajax_json(self.test_url, {}),
                              'collections.collections.update.form_errors')

        self.collection_1.reload()
        self.assertEqual(self.collection_1.caption, 'collection_1')
        self.assertEqual(self.collection_1.description, 'description_1')

    def test_success__for_edit(self):
        self.request_login(self.account_2.email)
        self.check_ajax_ok(self.post_ajax_json(self.test_url, self.get_post_data()))

        self.collection_1.reload()
        self.assertEqual(self.collection_1.caption, 'collection_edited')
        self.assertEqual(self.collection_1.description, 'description_edited')

    def test_success__for_moderate(self):
        prototypes.CollectionPrototype._db_all().update(approved=True)
        storage.collections.refresh()

        self.request_login(self.account_3.email)
        self.check_ajax_ok(self.post_ajax_json(self.test_url, self.get_post_data()))

        self.collection_1.reload()
        self.assertEqual(self.collection_1.caption, 'collection_edited')
        self.assertEqual(self.collection_1.description, 'description_edited')


class CollectionsApproveTests(BaseRequestTests):

    def setUp(self):
        super(CollectionsApproveTests, self).setUp()
        self.approve_url = utils_urls.url('collections:collections:approve', self.collection_1.id)

    def test_login_required(self):
        self.check_ajax_error(self.post_ajax_json(self.approve_url), 'common.login_required')

    def test_moderate_rights_required(self):
        self.request_login(self.account_2.email)
        self.check_ajax_error(self.post_ajax_json(self.approve_url), 'collections.collections.no_moderate_rights')

    def test_success(self):
        self.request_login(self.account_3.email)
        self.assertFalse(self.collection_1.approved)
        self.check_ajax_ok(self.post_ajax_json(self.approve_url))
        self.collection_1.reload()
        self.assertTrue(self.collection_1.approved)


class CollectionsDisapproveTests(BaseRequestTests):

    def setUp(self):
        super(CollectionsDisapproveTests, self).setUp()
        self.disapprove_url = utils_urls.url('collections:collections:disapprove', self.collection_1.id)

    def test_login_required(self):
        self.check_ajax_error(self.post_ajax_json(self.disapprove_url), 'common.login_required')

    def test_moderate_rights_required(self):
        self.request_login(self.account_2.email)
        self.check_ajax_error(self.post_ajax_json(self.disapprove_url), 'collections.collections.no_moderate_rights')

    def test_success(self):
        prototypes.CollectionPrototype._db_all().update(approved=True)
        storage.collections.refresh()
        self.collection_1.reload()

        self.request_login(self.account_3.email)

        self.assertTrue(self.collection_1.approved)
        self.check_ajax_ok(self.post_ajax_json(self.disapprove_url))
        self.collection_1.reload()
        self.assertFalse(self.collection_1.approved)
