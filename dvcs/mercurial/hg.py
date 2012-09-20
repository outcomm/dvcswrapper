import re, os
from collections import defaultdict
from xml.etree import ElementTree

from dateutil.parser import parse as dateutil_parse

from .. import utils
from ..wrapper import DVCSWrapper, DVCSException

try:
    from django.conf import settings
except ImportError:
    import settings

DIR_SCRIPT = os.path.dirname(os.path.realpath(__file__))

class Hg(DVCSWrapper):
    """
    "Command line is the API, it won't change." [hg@irc.freenode.net]
    """
    RE_PUSH_PULL_OUT = re.compile(
        r'added (?P<changesets>\d+) changesets with (?P<changes>\d+) changes to (?P<files>\d+) files')
    NO_PUSH_PULL = {'files': 0, 'changesets': 0, 'changes': 0}

    #TODO rename ``use_repo_path``
    def _command(self, command, *args, **kwargs):
        hg_binary = getattr(settings, 'HG_BINARY', 'hg')
        '''
            this allows to override default hg binary for certain commands. f.e if you need to log remote repo
            HG_COMMANDS_WITH_OTHER_BINARY = ['log']
            HG_OTHER_BINARY = 'ssh -C remote.server hg'
        '''

        if command in getattr(settings,'HG_COMMANDS_WITH_OTHER_BINARY', []):
            hg_binary = getattr(settings,'HG_OTHER_BINARY', hg_binary)

        use_repo_path = kwargs.get('use_repo_path', True)
        repo_path = '-R %s' % self.repo_path if use_repo_path else ''
        config = getattr(settings, 'HG_CONFIG', '')
        cmd = '%(prepend)s %(hg_binary)s %(repo_path)s %(config)s %(command)s %(args)s' % dict(
            prepend=kwargs.get('prepend', ''),
            hg_binary=hg_binary,
            repo_path=repo_path,
            config='--config %s' % config if config else '',
            command=command,
            args=' '.join(args))
        return utils.shell(cmd, ignore_return_code=kwargs.get('ignore_return_code', False))

    def _parse_date(self, date):
        return dateutil_parse(date)

    def _parse_log(self, xml):
        try:
            tree = ElementTree.XML(xml)
            as_list, as_dict = [], defaultdict(list)

            for one in tree.findall('logentry'):
                branch = one.find('branch')
                item = dict(branch=branch.text if branch is not None else 'default', files=[],
                    rev=one.attrib['revision'],
                    node=one.attrib['node'], short=one.attrib['node'][:12], tags=[])

                for el in one:
                    if el.tag == 'branch':
                        item['branch'] = el.text
                    elif el.tag == 'msg':
                        item['mess'] = u'%s' % el.text
                    elif el.tag == 'author':
                        item['author'] = u'%s <%s>' % (el.text, el.attrib['email'])
                    elif el.tag == 'date':
                        item['date'] = self._parse_date(el.text)
                    elif el.tag == 'paths':
                        item['files'] = [f.text for f in el.findall('path')]
                    elif el.tag == 'tag':
                        item['tags'] = [el.text]
                as_list.append(item)
                as_dict[item['branch']].append(item)
        except Exception, e:
            raise DVCSException('Log parsing failed: %s' % e)
        return as_list, as_dict

    def _parse_push_pull_out(self, out):
        search = re.search(self.RE_PUSH_PULL_OUT, out)
        if search is None:
            return self.NO_PUSH_PULL
        counts = search.groupdict(self.NO_PUSH_PULL)
        for k, v in counts.items():
            counts[k] = int(v)
        return counts


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


    def merge(self, branch=None, revision=None, **kwargs):
        if revision and branch:
            raise DVCSException('If revision is specified, branch cannot be set.')
        args = ['%s' % branch if branch else '',
                '%s' % '--rev %s' % revision if revision else '',
                "--config merge-tools.e.args='$base $local $other $output'",
                "--config merge-tools.e.priority=1000",
                "--config merge-tools.e.executable=%s" % os.path.join(DIR_SCRIPT, 'mergetool.py'),
                "--config merge-tools.e.premerge=True",
                "--noninteractive",
                "--preview" if kwargs.get('preview', False) else '',
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

    def log(self, branch=None):
        args = ['--style xml', '--verbose']
        if branch:
            args.append('--branch %s' % branch)
        out = self._command('log', *args)
        log = self._parse_log(out)

        return log

    def user_commits(self, user, limit=None, **kwargs):
        args = ['-u %s' % user, '--style xml']
        if limit:
            args.append('-l %s' % str(limit))

        out = self._command('log', *args)
        return self._parse_log(out)[0]

    def changed_between_nodes(self, start, end):
        return self.status(*['--rev', '%s:%s' % (str(start), str(end))])

    def branches(self, **kwargs):
        out = self._command('branches', '-c')

        branches = {'active': [], 'inactive': [], 'closed': [], 'all': []}
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
        out = self._command('log', '-b %s' % branch, '--style xml')
        return self._parse_log(out)[0]

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
            '--config extensions.hgext.extdiff="" extdiff -p %s' % os.path.join(DIR_SCRIPT, 'difftool.py'), *args,
            ignore_return_code=True) #@FIXME more sexy
        return out

    def has_new_changesets(self, branch=None):
        ret = False
        try:
            ret = bool(self._command('incoming', '--branch %s' % branch if branch else ''))
        except DVCSException, e:
            if e.code != 1:
                raise
        return ret

    def get_new_changesets(self, branch=None):
        revs = []
        try:
            out = self._command('incoming', '--style xml', '-b %s' % branch if branch else '')
            return self._parse_log(''.join(out.splitlines()[2:]))[0]
        except DVCSException, e:
            if e.code != 1: #no changsets
                raise

    def get_changed_files(self, start_node, end_node):
        try:
            out = self._command('log', '--verbose', '--style xml', '--rev %s:%s' % (start_node or '', end_node))
            log = self._parse_log(out)[0]
            return [(one['node'], one['files']) for one in log]
        except DVCSException:
            raise

    def get_head(self, branch=None):
        args = ['-l1', '--style xml']
        if branch:
            args.append('-b %s' % branch)

        try:
            out = self._command('log', *args)
            return self._parse_log(out)[0][0]
        except DVCSException:
            raise