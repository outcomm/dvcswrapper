#import sys, logging
#
#def catch_all(exc_type, exc_value, traceback):
#    logging.getLogger(__name__).error(exc_value, exc_info=(exc_type, exc_value, traceback))
#
#sys.excepthook = catch_all

class DVCSException(Exception):
    def __init__(self, message, *args, **kwargs):
        super(DVCSException, self).__init__(message)
        for k, v in kwargs.items():
            setattr(self, k, v)


class DVCSWrapper(object):
    def __init__(self, repo_path, vcs='mercurial.hg'):
        """
            factory for sublclasses, loads classes dynamically
            from vcs.vcs.Vcs
        """
        self.repo_path = repo_path
        try:
            klass = vcs.split('.')[1].capitalize()
            module = __import__(vcs, globals(), locals(), fromlist=[klass])
            self.__class__ = getattr(module, klass)
        except:
            raise

    def clone(self, remote_path):
        raise NotImplementedError

    def branch(self, name):
        raise NotImplementedError

    def add(self, *args):
        raise NotImplementedError

    def commit(self, message, user=None, addremove=True, files=None):
        raise NotImplementedError

    def merge(self, branch=None, revision=None, **kwargs):
        raise NotImplementedError

    def push(self, **kwargs):
        """
        returns {'files': 0, 'changesets': 0, 'changes': 0}
        """
        raise NotImplementedError

    def pull(self, branch=None, *args):
        """
        returns {'files': 0, 'changesets': 0, 'changes': 0}
        """
        raise NotImplementedError

    def update(self, branch=None, revision=None, clean=True, **kwargs):
        raise NotImplementedError

    def init_repo(self):
        raise NotImplementedError

    def status(self, *args):
        """
        returns {'added': [], 'modified': [], 'missing': [], 'not_versioned': [], 'removed': []}
        """
        raise NotImplementedError

    def log(self, branch=None):
        """
        return {'branch':[dict(date,revhash,author,message,files)]}
        """
        raise NotImplementedError

    def user_commits(self, user, limit=None, **kwargs):
        raise NotImplementedError

    def changed_between_nodes(self, start, end):
        raise NotImplementedError

    def branches(self, **kwargs):
        """
        returns {'active': [], 'inactive': [], 'closed': [], 'all':[] }
        """
        raise NotImplementedError

    def branch_revisions(self, branch, **kwargs):
        """
        returns [(date,revhash,author,message),]
        """
        raise NotImplementedError

    def diff_unified(self, path, identifier=None, **kwargs):
        """
        returns unified diff
        """
        raise NotImplementedError

    def diff_html(self, path, identifier=None, **kwargs):
        """
        returns html diff
        """
        raise NotImplementedError

    def has_new_changesets(self, branch=None):
        """
        returns boolean
        """
        raise NotImplementedError

    def get_new_changesets(self, branch=None):
        raise NotImplementedError

    def get_changed_files(self, start_node, end_node):
        """
        returns [(node,[removed,added,modified])
        """
        raise NotImplemented

    def get_head(self, branch=None):
        """
        returns dict(node,rev,node_short,message,author,branch,)
        """
        raise NotImplemented