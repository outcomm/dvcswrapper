import os, tempfile, shutil, datetime
from unittest import TestCase
import re
from ..wrapper import DVCSException, DVCSWrapper

try:
    import simplejson as json
except ImportError:
    import json

TMP = tempfile.gettempdir()

CURR_DIR = os.path.dirname(os.path.realpath(__file__))

REMOTE_REPO = os.path.join(CURR_DIR, 'hgtestrepo')


LOCAL_REPO = os.path.join(TMP, 'hgtests', 'local_clone')
DUMMY_REPO = os.path.join(TMP, 'hgtests', 'dummy')
DUMMY_REPO_COPY = DUMMY_REPO + '_copy'
DUMMY_REPO_COPY2 = DUMMY_REPO_COPY + '2'
TEST_FILE = 'test_file.txt'


def touch(path):
    with file(path, 'a'):
        os.utime(path, None)


def rmrf(path):
    try: shutil.rmtree(path)
    except: pass


class HgTests(TestCase):
    @classmethod
    def setUpClass(cls):
        rmrf(LOCAL_REPO)
        DVCSWrapper(LOCAL_REPO).clone(REMOTE_REPO) #local clone

    def setUp(self):
        pass

    def tearDown(self):
        rmrf(DUMMY_REPO)
        rmrf(DUMMY_REPO_COPY)
        rmrf(DUMMY_REPO_COPY2)

    def _init_repo(self, path):
        hg = DVCSWrapper(path)
        hg.init_repo()
        return hg

    def _mk_local_repo(self, to=DUMMY_REPO):
        hg = DVCSWrapper(to)
        hg.clone(remote_path=LOCAL_REPO)
        return hg

    def test_init(self):
        self.assertFalse(DVCSWrapper(DUMMY_REPO).init_repo())
        self.assertRaises(DVCSException, DVCSWrapper(DUMMY_REPO).init_repo)


    def test_clone(self):
        out = DVCSWrapper(DUMMY_REPO).clone(remote_path=LOCAL_REPO)
        self.assertTrue(out)
        self.assertRaises(DVCSException, DVCSWrapper(DUMMY_REPO).clone, remote_path=LOCAL_REPO)


    def test_add(self):
        hg = self._init_repo(DUMMY_REPO)
        new_file = os.path.join(DUMMY_REPO, TEST_FILE)
        touch(new_file)
        self.assertRaises(hg.add(new_file))
        self.assertRaises(hg.add(new_file))
        self.assertRaises(hg.add())

        self.assertRaises(DVCSException, hg.add, 'asd')

    def test_commit(self):
        hg = self._init_repo(DUMMY_REPO)
        new_file = os.path.join(DUMMY_REPO, TEST_FILE)
        touch(new_file)
        self.assertRaises(hg.add(new_file))
        hg.commit('msg')
        new_file = os.path.join(DUMMY_REPO, TEST_FILE + '2')
        touch(new_file)
        hg.commit('msg', user='olah', files=[new_file])
        self.assertRaises(DVCSException, hg.commit, 'msg', files=['blah']) # file not there
        self.assertRaises(DVCSException, hg.commit, 'msg') # nothing added

    def test_up(self):
        hg = self._init_repo(DUMMY_REPO)
        touch(os.path.join(DUMMY_REPO, TEST_FILE))
        hg.commit('msg')
        hg.update(revision=0)
        self.assertRaises(DVCSException, hg.update, revision=2000)

    def test_branch(self):
        hg = self._init_repo(DUMMY_REPO)
        self.assertTrue(hg.branch('test'))

    def test_branch_name(self):
        hg = self._init_repo(DUMMY_REPO)
        self.assertEqual(hg.branch(''), 'default')


    def test_merge(self):
        hg = self._init_repo(DUMMY_REPO)
        new_file = os.path.join(DUMMY_REPO, TEST_FILE)
        with open(new_file, "w") as f:
            f.write('fap fap fap')
        hg.commit('new branch test')

        hg.branch('test')
        with open(new_file, "a+") as f:
            f.write('\nfap second line')
        hg.commit('new branch test')

        hg.update(branch='default') #back to default
        hg.merge(branch='test')

        self.assertEqual(2, len(open(new_file, "r").readlines()))

    def test_conflict_merge(self):
        hg = self._mk_local_repo()

        hg.branch('test')

        def conflict_file(name):

            with open(name, "w") as f:
                f.write('fap fap fap')
            hg.commit('new test')

            hg.update(branch='default', clean=False) #back to default

            with open(name, "w") as f:
                f.write('second time')
            hg.commit('new test')

            hg.update(branch='test', clean=False) #back to default
            with open(name, "w") as f:
                f.write('lastafarae')
            hg.commit('new trest')

        conflict_file(os.path.join(DUMMY_REPO, TEST_FILE))
        conflict_file(os.path.join(DUMMY_REPO, 'segundo_compai'))

        hg.update(branch='default', clean=False)
        merge = hg.merge(branch='test')
        json_outputs = re.findall(r'\{"base".*\}', merge)
        to_merge = []
        for o in json_outputs:
            merge = json.loads(o)
            self.assertIsNotNone(merge)
            self.assertIsNotNone(merge['base'])
            self.assertIsNotNone(merge['local'])
            self.assertIsNotNone(merge['other'])
            self.assertIsNotNone(merge['tar'])


    def test_push_pull(self):
        hg = self._mk_local_repo()
        self.assertDictEqual({'files': 0, 'changesets': 0, 'changes': 0}, hg.push())

        #copy the cloned repo
        hg = DVCSWrapper(DUMMY_REPO_COPY)
        hg.clone(DUMMY_REPO)
        #copy again the cloned repo
        hg_copy = DVCSWrapper(DUMMY_REPO_COPY2)
        hg_copy.clone(DUMMY_REPO_COPY)

        with open(os.path.join(DUMMY_REPO_COPY, TEST_FILE), 'a+') as f:
            f.write('fap')
        hg.commit('fap')
        self.assertDictEqual({'files': 1, 'changesets': 1, 'changes': 1}, hg.push())

        self.assertDictEqual({'files': 1, 'changesets': 1, 'changes': 1}, hg_copy.pull())
        self.assertEquals({'files': 0, 'changesets': 0, 'changes': 0}, hg_copy.pull(branch='default'))


    def test_status(self):
        hg = self._mk_local_repo()
        st = hg.status()
        self.assertEqual({'added': [], 'missing': [], 'removed': [], 'modified': [], 'not_versioned': []}, st)

        new_file = os.path.join(DUMMY_REPO, 'asd')
        touch(new_file)
        hg.add(new_file)

        with open(os.path.join(DUMMY_REPO, TEST_FILE), 'a+') as f:
            f.write('fap')

        st = hg.status()
        self.assertEqual(
                {'added': ['asd'], 'missing': [], 'removed': [], 'modified': [], 'not_versioned': ['test_file.txt']},
            st)

    def test_user_commits(self):
        hg = self._mk_local_repo()
        hg.update(revision=5)
        log = list(hg.user_commits('lahola', limit=1))
        self.assertEquals([
                {'mess': 'gos knows', 'date': datetime.datetime(2012, 3, 2, 15, 59, 36), 'short': 'bc841aa8bbb1',
                 'node': 'bc841aa8bbb1cf6519670192857aeab484a48b56', 'author': 'JUDr.PhDr.Mgr. et Mgr.Henryk Lahola'}],
            log)

    def test_changed_between_nodes(self):
        hg = self._mk_local_repo()
        expects = {'added': ['closed', 'meh'], 'missing': [], 'removed': [],
                   'modified': [], 'not_versioned': []}
        self.assertDictEqual(expects, hg.changed_between_nodes(0, 2))

    def test_log(self):
        assert False

    def test_repo_log(self):
        hg = self._mk_local_repo()
        log = hg.repo_log()
        self.assertEquals('690216eee7b291ac9dca0164d660576bdba51d47', log['default'][-1]['node'])

    def test_list_branches(self):
        hg = self._mk_local_repo()
        branches = hg.branches()
        self.assertEquals(sorted(['active', 'inactive', 'closed', 'all']), sorted(branches.keys()))
        self.assertTrue('inactive' in branches['inactive'])
        self.assertTrue('closed' in branches['closed'])
        self.assertTrue('default' in branches['active'])

    def test_branch_revisions(self):
        hg = self._mk_local_repo()
        revs = list(hg.branch_revisions('default'))
        self.assertEquals(
            dict(date=datetime.datetime(2012, 3, 2, 15, 49, 1), node='690216eee7b291ac9dca0164d660576bdba51d47',
                author='Jan Florian <starenka0@gmail.com>', mess='first'), revs[-1])

    def test_udiff(self):
        hg = self._mk_local_repo()
        hg.update(revision=6)
        expects = """diff -r 43ada45cd836 -r bc841aa8bbb1 one
--- a/one	Fri Mar 02 16:31:27 2012 +0100
+++ b/one	Fri Mar 02 15:59:36 2012 +0100
@@ -1,1 +0,0 @@
-dummy"""
        self.assertEquals(expects, hg.diff_unified('one', identifier='6:5'))

    def test_htmldiff(self):
        #hg = self._mk_local_repo()
        #hg.update(revision=6)
        #hg.diff_html('one', identifier='6:5')
        assert False

    def test_has_new_changesets(self):
        hg = self._mk_local_repo()
        self.assertFalse(hg.has_new_changesets())

        new_file = os.path.join(DUMMY_REPO, TEST_FILE + '3')
        touch(new_file)
        hg.commit('Always look good. Always!', user='brogrammer', files=[new_file])
        hg2 = self._mk_local_repo(DUMMY_REPO_COPY)
        hg.push()
        self.assertTrue(hg2.has_new_changesets())

    def test_get_new_changesets(self):
        hg = self._mk_local_repo()
        self.assertFalse(hg.get_new_changesets())

        new_file = os.path.join(DUMMY_REPO, TEST_FILE + '4')
        touch(new_file)
        hg.commit('Always look good. Always!', user='brogrammer', files=[new_file])
        hg2 = self._mk_local_repo(DUMMY_REPO_COPY)
        hg.push()
        last = hg2.get_new_changesets()[-1]
        self.assertEquals(('Always look good. Always!', 'brogrammer'), (last['mess'], last['author']))

