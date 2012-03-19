import re, os, datetime
from collections import defaultdict

from .. import utils
from ..wrapper import DVCSWrapper, DVCSException

try:
    from django.conf import settings
except ImportError:
    import settings

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

class Hg(DVCSWrapper):
    """
    "Command line is the API, it won't change." [hg@irc.freenode.net]
    """
    RE_PUSH_PULL_OUT = re.compile(
        r'added (?P<changesets>\d+) changesets with (?P<changes>\d+) changes to (?P<files>\d+) files')
    RE_SPLIT_LOG = re.compile(r'\t{2}')
    NO_PUSH_PULL = {'files': 0, 'changesets': 0, 'changes': 0}

    #TODO rename ``use_repo_path``
    def _command(self, command, *args, **kwargs):
        use_repo_path = kwargs.get('use_repo_path', True)
        repo_path = '-R %s' % self.repo_path if use_repo_path else ''
        config = getattr(settings, 'HG_CONFIG', '')
        cmd = '%(prepend)s %(hg_binary)s %(repo_path)s %(config)s %(command)s %(args)s' % dict(
            prepend=kwargs.get('prepend', ''),
            hg_binary=getattr(settings, 'HG_BINARY', 'hg'),
            repo_path=repo_path,
            config='--config %s' % config if config else '',
            command=command,
            args=' '.join(args))
        return utils.shell(cmd, ignore_return_code=kwargs.get('ignore_return_code', False))

    def clone(self, remote_path):
        return self._command('clone', remote_path, self.repo_path, use_repo_path=False)

    def branch(self, name):
        return self._command('branch', name)

    def add(self, *args):
        if not args:
            args = ['%s' % os.path.join(self.repo_path, '*'), ]
        return self._command('add', *args)


    #TODO conflict handling
    def commit(self, message, user=None, addremove=True, files=None):
        files = files if files else []
        args = ['-m "%s"' % message,
                '%s' % '--addremove' if addremove else '',
                '%s' % '--user %s' % user if user else '',
                ' '.join(files)
        ]
        return self._command('commit', *args)


    def merge(self, branch=None, revision=None):
        if revision and branch:
            raise DVCSException('If revision is specified, branch cannot be set.')
        args = ['%s' % branch if branch else '',
                '%s' % '--rev %s' % revision if revision else '',
                "--config merge-tools.e.args='$base $local $other $output'",
                "--config merge-tools.e.priority=1000",
                "--config merge-tools.e.executable=%s" % os.path.join(SCRIPT_DIR, 'mergetool.py'),
                "--config merge-tools.e.premerge=True",
                "--noninteractive",
                ]

        return self._command('merge', *args)


    def push(self, **kwargs):
        """
        HG specific command `new_branch` set to True
        """
        try:
            out = self._command('push',
                '--new-branch' if kwargs.get('new_branch', False) else ''
            )
        except DVCSException, e:
            if e.code == 1 and 'no changes found' in e.stdout:
                return self.NO_PUSH_PULL
            raise e
        return self._parse_push_pull_out(out)


    def pull(self, branch=None, *args):
        if branch:
            args = list(args)
            args.append('--branch %s' % branch)
        try:
            out = self._command('pull', *args)
        except DVCSException, e:
            if e.code == 1 and 'no changes found' in e.stdout:
                return self.NO_PUSH_PULL
            raise e
        return self._parse_push_pull_out(out)

    def _parse_push_pull_out(self, out):
        search = re.search(self.RE_PUSH_PULL_OUT, out)
        if search is None:
            return self.NO_PUSH_PULL
        counts = search.groupdict(self.NO_PUSH_PULL)
        for k, v in counts.items():
            counts[k] = int(v)
        return counts

    def update(self, branch=None, revision=None, clean=True, **kwargs):
        if revision and branch:
            raise DVCSException('If revision is specified, branch cannot be set.')
        args = ['%s' % branch if branch else '',
                '%s' % '--rev %s' % revision if revision else '',
                '-C' if clean else '',
                ]
        return self._command('update', *args)


    def init_repo(self):
        return self._command('init', self.repo_path, use_repo_path=False)

    def status(self, *args):
        out = self._command('status', *args).strip()
        map = {'A': 'added', '!': 'missing', 'M': 'modified', 'R': 'removed', '?': 'not_versioned'}
        #default empty set
        changes = {'added': [], 'modified': [], 'missing': [], 'not_versioned': [], 'removed': []}
        if not out:
            return changes
        lines = out.split("\n")
        status_split = re.compile("^(.) (.*)$")

        for change, path in [status_split.match(x).groups() for x in lines]:
            changes.setdefault(map[change], []).append(path)
        return changes


    def log(self, identifier=None, limit=None, template=None, **kwargs):
        args = ['log']
        if identifier: args.append(['-r', str(identifier)])
        if limit: args.append(['-l', str(limit)])
        if template: args.append(['--template', str(template)])
        for k, v in kwargs.items():
            args.extend([k, v])
        return self._command(*args)


    def repo_log(self):
        template = '{branch}\t\t{node}\t\t{node|short}\t\t{date|isodatesec}\t\t{author}\t\t{files}\t\t{rev}\t\t{desc}\n'
        out = self._command('log', "--template='%s'" % template)

        log = defaultdict(list)
        for one in out.splitlines():
            branch, node, short, date, author, files, rev, mess = re.split(self.RE_SPLIT_LOG, one)
            rev = dict(node=node, short=short, date=datetime.datetime.strptime(date[:-6], '%Y-%m-%d %H:%M:%S'),
                author=author, mess=mess
            )
            log[branch].append(rev)
        return log

    def user_commits(self, user, limit=None, **kwargs):
        args = {'-u': user,
                '--template': '"{branch}\t\t{node}\t\t{node|short}\t\t{date|isodatesec}\t\t{author}\t\t{files}\t\t{rev}\t\t{desc}\n"'}
        if limit:
            args.update({'-l': str(limit)})
        args.update(kwargs)
        out = self.log(**args)

        for one in out.splitlines():
            branch, node, short, date, author, files, rev, mess = re.split(self.RE_SPLIT_LOG, one)
            yield dict(node=node, short=short, date=datetime.datetime.strptime(date[:-6], '%Y-%m-%d %H:%M:%S'),
                author=author, mess=mess
            )

    def changed_between_nodes(self, start, end):
        return self.status(*['--rev', '%s:%s' % (str(start), str(end))])

    def branches(self, **kwargs):
        out = self._command('branches', '-c')

        branches = {'active': [], 'inactive': [], 'closed': [], 'all':[]}
        re_line = re.compile(r'\s+')
        for line in out.splitlines():
            line = re.split(re_line, line)
            try:
                status = line[2][1:-1]
            except IndexError:
                status = 'active'
            branches[status].append(line[0])
            branches['all'].append(line[0])

        #sort'em
        for k, v in branches.iteritems():
            branches[k] = sorted(v)
        return branches

    def branch_revisions(self, branch, **kwargs):
        template = '{node}\t\t{node|short}\t\t{date|isodatesec}\t\t{author}\t\t{files}\t\t{rev}\t\t{desc}\n'
        out = self._command('log', '-b %s' % branch, "--template='%s'" % template)
        for one in out.splitlines():
            node, short, date, author, files, rev, mess = re.split(self.RE_SPLIT_LOG, one)
            yield dict(date=datetime.datetime.strptime(date[:-6], '%Y-%m-%d %H:%M:%S'), node=node, author=author,
                mess=mess)

    def diff_unified(self, path, identifier=None, **kwargs):
        args = [os.path.join(self.repo_path, path)]
        if identifier:
            args.append('-r %s' % str(identifier))
        out = self._command('diff', *args)
        return out

    def diff_html(self, path, identifier=None, **kwargs):
        args = [os.path.join(self.repo_path, path)]
        if identifier:
            args.append('-r %s' % str(identifier))
        out = self._command(
            '--config extensions.hgext.extdiff="" extdiff -p %s' % os.path.join(SCRIPT_DIR, 'difftool.py'), *args,
            ignore_return_code=True) #@FIXME more sexy
        return out

    def has_new_changesets(self, branch=None):
        ret = False
        try:
            ret = bool(self._command('incoming', '-b %s' % branch if branch else ''))
        except DVCSException, e:
            if e.code != 1:
                raise

        return ret

    def get_new_changesets(self, branch=None):
        revs = []
        try:
            template = '{node}\t\t{date|isodatesec}\t\t{author}\t\t{desc}\n'
            out = self._command('incoming', '--template="%s"' % template, '-b %s' % branch if branch else '')
            for one in out.splitlines()[2:]: #skip "comparing with" meh and "searching for changes"
                node, date, author, mess = re.split(self.RE_SPLIT_LOG, one)
                revs.append(
                    dict(date=datetime.datetime.strptime(date[:-6], '%Y-%m-%d %H:%M:%S'), node=node, author=author,
                        mess=mess))
        except DVCSException, e:
            if e.code != 1: #no changsets
                raise

        return revs
