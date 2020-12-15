from copy import deepcopy
import dotbot
import glob
from os import path
import re
from string import Template
import subprocess

''' TODO just some things to remember
- support for different crypto providers (plugin architechture?)

'''

''' Parameters
both|provider|program that will handle encryption/decryption|
both|targets|If omitted, empty, or null, read files to encrypt from default list file, './secrets/targets'. If string, read files to encrypt from value instead of default list file. If array, use values as files to encrypt. (default: omitted)|
'''

'''YAML
- defaults:
    - encrypt:
        provider: gpg
        archive: secrets.gpg|override file name
        gpg-implementor: gpg|alternative gpg program
        key: ~|ASK|gpg recipient
        targets: targets|override file name|array

- decrypt: ~

- encrypt: ~
'''

class _EncryptProvider(object):

    def __init__(self, dotbot_context, dotbot_log, config):
        self._config = config
        self._context = dotbot_context
        self._log = dotbot_log

    def handle_decrypt(self):
        raise NotImplementedError

    def handle_encrypt(self):
        raise NotImplementedError


class GpgProvider(_EncryptProvider):
    _cmd_encrypt = "tar -cf - $targets | $gpg_implementor $gpg_options --yes --output $archive"

    _defaults = {
        'archive': 'secrets.gpg',
        'gpg-implementor': 'gpg', # or a different program that provides a 'gpg' like experience
        # TODO warn users about dot files being excluded with *
        'targets': 'targets',
    }

    def handle_decrypt(self):
        raise NotImplementedError

    def handle_encrypt(self):
        archive = path.join('secrets', self._config.get('archive', self._defaults['archive']))
        gpg_implementor = self._config.get('gpg-implementor', self._defaults['gpg-implementor'])
        gpg_options = self._collect_gpg_options()
        targets = self._collect_targets()
        #TODO find a way to turn off this printing??
        self._log.lowinfo('Files to encrypt:\n%s' % '\n'.join(targets))
        cmd_args = {
            'archive': archive,
            'gpg_implementor': gpg_implementor,
            'gpg_options': gpg_options,
            'targets': targets
        }
        self._log.debug('Encrypt: cmd_args\n' + cmd_args)
        cmd = Template(self._cmd_encrypt).substitute(cmd_args)

        try:
            self._log.debug('Encrypt: cmd: %s' % cmd)
            subprocess.check_call(cmd, shell=True, stdin=subprocess.PIPE)
            self._log.lowinfo('Created encrypted archive %s' % archive)
            self._add_to_git(archive)
            return True
        except subprocess.CalledProcessError as e:
            self._log.error('Failed to create encrypted archive %s' % archive)
            return False
    
    def _add_to_git(self, archive):
        proc = subprocess.Popen(
            'git status --porcelain -uall %s 2> /dev/null' % archive,
            encoding='utf-8',
            shell=True,
            stdout=subprocess.PIPE)
        proc.wait()
        output, _ = proc.communicate()
        self._log.debug('Archive git status: %s' % output)
        if output.startswith('??'):
            resp = None
            while (resp is None):
                resp = input('Add "%s" to git (y/n)? ')
                if resp is None:
                    continue
                resp = resp.strip().lower()
                if not resp:
                    resp = None
                elif resp.startswith('y') or resp.startswith('n'):
                    resp = resp[0]
                else:
                    resp = None
            if resp == 'y':
                subprocess.check_call('git add %s' % archive, shell=True)
                
    def _collect_gpg_options(self):
        ret = []
        if self._config.get('key') is None:
            ret.append('-c')
        else:
            raise NotImplementedError
        return ' '.join(ret)

    def _collect_targets(self):
        targets = self._config.get('targets', self._defaults['targets-file'])
        if isinstance(targets, str):
            with open(path.join('secrets', path.basename(targets)), 'r') as f:
                list_items = f.readlines()
            targets = list_items
        if not isinstance(targets, []):
            raise TypeError('"targets" parameter expected to be list, but here is %s' % type(targets))
        globs = [glob.glob(target) for target in targets]
        ret = ["'{}'".format(path) for paths in globs for path in paths]
        return ret
    



# TODO might have to split encrypt and decrypt into their own worker classes
class Encrypt(dotbot.Plugin):
    DIRECTIVE_DECRYPT = 'decrypt'
    DIRECTIVE_DEFAULTS = 'defaults'
    DIRECTIVE_ENCRYPT = 'encrypt'

    _defaults = {}

    def can_handle(self, directive):
        return directive in [self.DIRECTIVE_DECRYPT, self.DIRECTIVE_DEFAULTS, self.DIRECTIVE_ENCRYPT]
    
    def handle(self, directive, data):
        if directive == self.DIRECTIVE_DECRYPT:
            return self._handle_decrypt(data)
        elif directive == self.DIRECTIVE_DEFAULTS:
            if len(self._defaults) > 0:
                self._log.error('Encrypt: attempt to redifine defaults not allowed. Defaults must be defined only once.')
                return False
            self._defaults = deepcopy(data.get(self.DIRECTIVE_ENCRYPT, self._defaults))
        elif directive == self.DIRECTIVE_ENCRYPT:
            return self._handle_encrypt(data)
        else:
            raise ValueError('Encrypt cannot handle directive %s' % directive)
    
    def _handle_decrypt(self, data):
        self._log.error("Encrypt: decrypt not implemented.")
        return False

    def _handle_encrypt(self, data):
        self._require_provider(data)
        provider = _get_provider_instance(self._defaults, data)
        ret = provider.handle_encrypt()
        return ret
    
    @staticmethod
    def _get_config_provider_strings(defaults, task):
        ret = (defaults.get('provider'), task.get('provider'))
        return ret
    
    def _get_provider_instance(self, defaults, task):
        d, t = _get_config_provider_strings(defaults, task)
        p = t or d
        if p.lower() == 'gpg':
            ret = GpgProvider(self._context, self._log, defaults)
        else:
            raise NotImplementedError('Provider %s has no implementation.' % p)
        return ret

    def _require_provider(self, task):
        d, t = _get_config_provider_strings(self._defaults, task)
        if d is None and t is None:
            raise KeyError('Missing "provider" parameter.')
        if d is not None and t is not None: 
            raise KeyError('Cannot override default provide "%s" with "%s"' % (d, t))

