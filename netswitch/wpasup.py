'''Utils for managing wpa supplicant files.
'''
import os
import glob
import logging
from shutil import copyfile
from . import util


logger = logging.getLogger(__name__)

def set_ap_path(path):
    Wpa.ap_path = path

def connect(ssid, verify=False):
    return Wpa(ssid).connect() and (not verify or verify_ssid(ssid))

def verify_ssid(ssid):
    return Wpa().ssid == ssid


class Wpa:
    ap_path = '/etc/wpa_supplicant/aps'
    WPA_PATH = "/etc/wpa_supplicant/wpa_supplicant.conf"
    def __init__(self, ssid=None, path=None, iface='wlan0', ap_path=None):
        self.ap_path = ap_path or self.ap_path
        self.iface = iface
        self.path = path or (ssid_path(ssid, self.ap_path) if ssid else self.WPA_PATH)
        self.ssid = ssid or self.info.get('ssid')

    def connect(self, backup=True, restart=True):
        '''Set ap as current wpa_supplicant.'''
        wpa = Wpa()
        if wpa.ssid != self.ssid:
            if backup:
                wpa.backup()
            return (
                self.copy(self.WPA_PATH)
                and not restart or util.restart_iface(self.iface))
        return True

    @property
    def exists(self):
        return self.path and os.path.exists(self.path)

    def copy(self, dest):
        '''Copy wpa_supplicant to destination.'''
        if self.path != dest and self.exists:
            copyfile(self.path, dest)
        return True

    def create(self, **kw):
        '''Generate wpa supplicant.'''
        generate_wpa_config(self.ssid, **kw)

    def backup(self, force=True):
        '''Make sure that the current wifi network is present in aps/.
        '''
        if force or self.ssid not in ssids_from_dir(self.ap_path):
            self.copy(ssid_path(self.ssid, self.ap_path))
            return True
        return False

    @property
    def info(self):
        '''Parse the wpa_supplicant.conf file and return key value pairs.'''
        DROP_KEYS = ('network',)
        if self._info is None:
            if not self.exists:
                return {}
            with open(self.path) as wpa_conf:
                self._info = {
                    x[0].strip(): x[1].strip('"\' ') for x in
                    (l.split("=", 1) for l in wpa_conf.read().splitlines())
                    if len(x) > 1 and x[0] not in DROP_KEYS
                }
                self._info['password'] = self._info.get('psk')
        return self._info
    _info = None

    def __getattr__(self, k):
        try:
            return self.info[k]
        except KeyError as e:
            raise AttributeError(e)

    def _summary(self):
        import json
        cfg = util.mask_dict_values(
                self.info, 'password', drop=('psk', 'ctrl_interface', 'update_config'))
        return json.dumps(cfg, indent=4 if len(cfg) > 3 else None, sort_keys=True)

    def summary(self):
        print(self._summary())



def ssid_path(ssid, ap_path=None):
    return os.path.join(ap_path or Wpa.ap_path, f'{ssid}.conf')


def ssids_from_dir(ap_path=None, pat='*.conf'):
    '''Get file name -> file path mapping for files in a directory.
    e.g.: `{file: ap_path/file.ext for f in glob(ap_path)}`'''
    return {
        os.path.splitext(os.path.basename(f))[0]: f
        for f in glob.glob(os.path.join(ap_path or Wpa.ap_path, pat))}


def sync_aps(repo_path, ap_path=None, force=True, backup=True):
    '''Copy aps from network/aps to the trusted aps path.'''
    ap_path = ap_path or Wpa.ap_path
    os.makedirs(ap_path, exist_ok=True)
    fnames_repo = ssids_from_dir(repo_path)
    fnames_aps = ssids_from_dir(ap_path)
    for fn in (fnames_repo if force else set(fnames_repo) - set(fnames_aps)):
        copyfile(fnames_repo[fn], os.path.join(ap_path, fn + '.conf'))
    if backup:
        Wpa().backup()



'''

Create Wpa Supplicant File

'''

def generate_wpa_config(
        ssid, password=None, kind='basic', group='netdev',
        country='US', askpass=False, ap_path=None, **kw):
    '''Create the wpa_supplicant configuration file
    in the `./aps/{ssid}.conf`

    Arguments:
        ssid (str): Access point to add credentials for.
        password (str, optional): The

    Returns:
        status (bool): True if no exception was raised when creating
    '''
    logger.debug("Creating config for: " + str(ssid))
    password = password or kw.pop('psk', None)
    if askpass and not password:
        import getpass
        password = getpass.getpass()

    if kind == 'basic':
        network = (
            dict(ssid=ssid, psk=password) if password else
            dict(ssid, key_mgmt='NONE'))
    elif kind == 'edu':
        network = dict(
            ssid=ssid, proto='RSN', key_mgmt='WPA-EAP',
            pairwise='CCMP', phase2="auth=MSCHAPV2",
            auth_alg='OPEN', eap='PEAP',
            identity=kw.pop('identity'),
            password=password)
    else:
        raise ValueError('Unknown wpa config format "{}"'.format(kind))

    tmpl = '''
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP={group}
update_config=1
country={country}
network={{
{network}
}}'''.strip()

    with open(ensure_dir(ssid_path(ssid, ap_path=ap_path)), 'w') as f:
        f.write(tmpl.format(
            group=group, country=country,
            network=util.indent(_wpa_keys(**network, **kw), 2)))
    return True


def ensure_dir(path):
    dname = os.path.dirname(path)
    if dname:
        os.makedirs(dname, exist_ok=True)
    return path


def _wpa_keys(*a, sep='\n', **kw):
    return sep.join(list(map(str, a)) + [
        '{}={}'.format(k, '{!r}'.format(v))
        for k, v in kw.items()
    ])
