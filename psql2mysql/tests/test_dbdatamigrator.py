#
# coding=utf8
#

# (c) Copyright 2018, SUSE LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

try:
    import mock
except ImportError:
    from unittest import mock

from collections import namedtuple
import unittest

import psql2mysql


class TestDbDataMigrator(unittest.TestCase):

    @mock.patch('psql2mysql.cfg.CONF')
    def test_fallback(self, cfg_mock):
        cfg_mock.source = 'source://uri'
        cfg_mock.target = 'target://uri'
        dbdatamigrator = psql2mysql.DbDataMigrator(None, None, None)
        self.assertEqual(dbdatamigrator.src_uri, 'source://uri')
        self.assertEqual(dbdatamigrator.target_uri, 'target://uri')

    @mock.patch('psql2mysql.DbWrapper')
    def test_setup(self, dbwrapper_mock):
        dbwrapper_mock.connect.return_value = None
        dbdatamigrator = psql2mysql.DbDataMigrator(None, 'source', 'target')
        dbdatamigrator.setup()
        calls = (mock.call('source'), mock.call().connect(),
                 mock.call('target'), mock.call().connect())
        dbwrapper_mock.assert_has_calls(calls)

    def test_migrate_no_tables(self):
        dbdatamigrator = psql2mysql.DbDataMigrator(None, 'source', 'target')
        dbdatamigrator.src_db = mock.MagicMock()
        dbdatamigrator.target_db = mock.MagicMock()
        dbdatamigrator.src_db.getSortedTables.return_value = []
        with self.assertRaises(psql2mysql.SourceDatabaseEmpty):
            dbdatamigrator.migrate()
        dbdatamigrator.src_db.getSortedTables.return_value = ['foo']
        dbdatamigrator.target_db.getTables.return_value = []
        with self.assertRaises(psql2mysql.TargetDatabaseEmpty):
            dbdatamigrator.migrate()

    def test_migrate_skipped_tables(self):
        dbdatamigrator = psql2mysql.DbDataMigrator(None, 'source', 'target')
        dbdatamigrator.src_db = mock.MagicMock()
        dbdatamigrator.target_db = mock.MagicMock()
        table = namedtuple('Table', ['name', 'columns'])
        alembic_migration = table('alembic_migration', [])
        migrate_version = table('migrate_version', [])
        dbdatamigrator.src_db.getSortedTables.return_value = [
            alembic_migration, migrate_version]
        dbdatamigrator.target_db.getTables.return_value = {
            'alembic_migration': alembic_migration,
            'migrate_version': migrate_version}
        dbdatamigrator.migrate()
        dbdatamigrator.src_db.readTableRows.assert_not_called()

    def test_migrate(self):
        dbdatamigrator = psql2mysql.DbDataMigrator(None, 'source', 'target')
        table = namedtuple('Table', ['name', 'columns'])
        foo = table('foo', [])
        table_result = namedtuple('TableResult', ['returns_rows', 'rowcount'])
        dbdatamigrator.src_db = mock.MagicMock()
        dbdatamigrator.src_db.getSortedTables.return_value = [foo]
        dbdatamigrator.src_db.readTableRows.return_value = table_result(
            ['foo', 'bar'], 1)
        dbdatamigrator.target_db = mock.MagicMock()
        dbdatamigrator.target_db.getTables.return_value = {'foo': foo}
        dbdatamigrator.target_db.getSortedTables.return_value = [foo]
        dbdatamigrator.migrate()
        dbdatamigrator.src_db.readTableRows.assert_called_with(foo)
        dbdatamigrator.target_db.clearTable.assert_called_with(foo)
        dbdatamigrator.target_db.writeTableRows.assert_called_once()
