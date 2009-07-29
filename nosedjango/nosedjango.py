"""
nose plugin for easy testing of django projects and apps. Sets up a test
database (or schema) and installs apps from test settings file before tests
are run, and tears the test database (or schema) down after all tests are run.
"""

import os, sys
import re

from nose.plugins import Plugin
import nose.case

# Force settings.py pointer
# search the current working directory and all parent directories to find
# the settings file
from nose.importer import add_path
if not 'DJANGO_SETTINGS_MODULE' in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from django.core.management import setup_environ

import re
NT_ROOT = re.compile(r"^[a-zA-Z]:\\$")
def get_SETTINGS_PATH():
    '''
    Hunt down the settings.py module by going up the FS path
    '''
    cwd = os.getcwd()
    settings_filename = '%s.py' % (
        os.environ['DJANGO_SETTINGS_MODULE'].split('.')[-1]
        )
    while cwd:
        if settings_filename in os.listdir(cwd):
            break
        cwd = os.path.split(cwd)[0]
        if os.name == 'nt' and NT_ROOT.match(cwd):
            return None
        elif cwd == '/':
            return None
    return cwd

SETTINGS_PATH = get_SETTINGS_PATH()

def _dummy(*args, **kwargs):
    """Dummy function that replaces the transaction functions"""
    return

class NoseDjango(Plugin):
    """
    Enable to set up django test environment before running all tests, and
    tear it down after all tests. If the django database engine in use is not
    sqlite3, one or both of --django-test-db or django-test-schema must be
    specified.

    Note that your django project must be on PYTHONPATH for the settings file
    to be loaded. The plugin will help out by placing the nose working dir
    into sys.path if it isn't already there, unless the -P
    (--no-path-adjustment) argument is set.
    """
    name = 'django'

    def disable_transaction_support(self, transaction):
        self.orig_commit = transaction.commit
        self.orig_rollback = transaction.rollback
        self.orig_savepoint_commit = transaction.savepoint_commit
        self.orig_savepoint_rollback = transaction.savepoint_rollback
        self.orig_enter = transaction.enter_transaction_management
        self.orig_leave = transaction.leave_transaction_management

        transaction.commit = _dummy
        transaction.rollback = _dummy
        transaction.savepoint_commit = _dummy
        transaction.savepoint_rollback = _dummy
        transaction.enter_transaction_management = _dummy
        transaction.leave_transaction_management = _dummy

    def restore_transaction_support(self, transaction):
        transaction.commit = self.orig_commit
        transaction.rollback = self.orig_rollback
        transaction.savepoint_commit = self.orig_savepoint_commit
        transaction.savepoint_rollback = self.orig_savepoint_rollback
        transaction.enter_transaction_management = self.orig_enter
        transaction.leave_transaction_management = self.orig_leave

    def configure(self, options, conf):
        Plugin.configure(self, options, conf)
        self.verbosity = conf.verbosity

    def begin(self):
        """Create the test database and schema, if needed, and switch the
        connection over to that database. Then call install() to install
        all apps listed in the loaded settings module.
        """
        # Add the working directory (and any package parents) to sys.path
        # before trying to import django modules; otherwise, they won't be
        # able to find project.settings if the working dir is project/ or
        # project/..

        if not SETTINGS_PATH:
            sys.stderr.write("Can't find Django settings file!\n")
            # short circuit if no settings file can be found
            return

        if self.conf.addPaths:
            map(add_path, self.conf.where)

        add_path(SETTINGS_PATH)
        sys.path.append(SETTINGS_PATH)
        from django.conf import settings

        # Some Django code paths evaluate differently
        # between DEBUG and not DEBUG.  Example of this include the url
        # dispatcher when 404's are hit.  Django's own test runner forces DEBUG
        # to be off.
        settings.DEBUG = False

        from django.core import mail
        self.mail = mail
        from django.core import management
        from django.test.utils import setup_test_environment
        from django.db import connection

        self.old_db = settings.DATABASE_NAME

        # setup the test env for each test case
        setup_test_environment()
        connection.creation.create_test_db(verbosity=self.verbosity)

        # exit the setup phase and let nose do it's thing

    def afterTest(self, test):
        # Restore transaction support on tests
        from django.conf import settings
        from django.db import connection, transaction
        transaction_support = True
        if hasattr(test.context, 'use_transaction'):
            transaction_support = test.context.use_transaction
        if hasattr(settings, 'DISABLE_TRANSACTION_MANAGEMENT'):
            # Do not use transactions if user has forbidden usage.
            # Assume that the database supports them anyway.
            transaction_support = not settings.DISABLE_TRANSACTION_MANAGEMENT

        if transaction_support:
            self.restore_transaction_support(transaction)
            transaction.rollback()
            transaction.leave_transaction_management()
            # If connection is not closed Postgres can go wild with
            # character encodings.
            connection.close()

    def beforeTest(self, test):

        if not SETTINGS_PATH:
            # short circuit if no settings file can be found
            return

        # This is a distinctive difference between the NoseDjango
        # test runner compared to the plain Django test runner.
        # Django uses the standard unittest framework and resets the
        # database between each test *suite*.  That usually resolves
        # into a test module.
        #
        # The NoseDjango test runner will reset the database between *every*
        # test case.  This is more in the spirit of unittesting where there is
        # no state information passed between individual tests.

        from django.core.management import call_command
        from django.core.urlresolvers import clear_url_caches
        from django.conf import settings
        from django.db import connection, transaction

        transaction_support = True
        if hasattr(test.context, 'use_transaction'):
            transaction_support = test.context.use_transaction
        if hasattr(settings, 'DISABLE_TRANSACTION_MANAGEMENT'):
            # Do not use transactions if user has forbidden usage.
            # Assume that the database supports them anyway.
            transaction_support = not settings.DISABLE_TRANSACTION_MANAGEMENT
        self.mail.outbox = []
        if transaction_support:
            transaction.enter_transaction_management()
            transaction.managed(True)
            self.disable_transaction_support(transaction)

        else:
            call_command('flush', verbosity=0, interactive=False)

        if isinstance(test, nose.case.Test) and \
            isinstance(test.test, nose.case.MethodTestCase) and \
            hasattr(test.context, 'fixtures'):
                # We have to use this slightly awkward syntax due to the fact
                # that we're using *args and **kwargs together.
                call_command('loaddata', *test.context.fixtures, **{'verbosity': 0})

        if isinstance(test, nose.case.Test) and \
            isinstance(test.test, nose.case.MethodTestCase) and \
            hasattr(test.context, 'urls'):
                # We have to use this slightly awkward syntax due to the fact
                # that we're using *args and **kwargs together.
                self.old_urlconf = settings.ROOT_URLCONF
                settings.ROOT_URLCONF = self.urls
                clear_url_caches()


    def finalize(self, result=None):
        """
        Clean up any created database and schema.
        """
        if not SETTINGS_PATH:
            # short circuit if no settings file can be found
            return

        from django.test.utils import teardown_test_environment
        from django.db import connection
        from django.conf import settings
        connection.creation.destroy_test_db(self.old_db, verbosity=self.verbosity)
        teardown_test_environment()

        if hasattr(self, 'old_urlconf'):
            settings.ROOT_URLCONF = self.old_urlconf
            clear_url_caches()

