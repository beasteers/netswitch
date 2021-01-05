import os
import time
import functools
import fnmatch
import ifcfg
import yaml
from . import iw, wpasup, util
from .util import internet_connected

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def log_kw(msg):
    def outer(func):
        msg_ = msg or func.__name__
        @functools.wraps(func)
        def inner(*a, **kw):
            logger.info('{}: {}'.format(msg_, kw))
            return func(*a, **kw)
        return inner
    return outer(msg) if callable(msg) else outer


class NetSwitch:
    '''

    Example:

    ```
    NetSwitch([
        {'interface': 'wlan*', 'ssids': 's0nycL1f3l1ne'},
        {'interface': 'eth*'},
        {'interface': 'ppp*'},
        {'interface': 'wlan*'},
    ])
    ```

    assume:
     - ifaces: wlan0, wlan1, ppp0
     - trusted ssids: nyu, nyu-legacy

    Procedure:
     - check wlan1 for s0nycL1f3l1ne
     - check wlan0 for s0nycL1f3l1ne
     - check for eth0 and internet connected thru interface
     - check for ppp0 and internet connected thru interface
        - should we control wvdial or whatevs in this ???
     - check wlan1 for [nyu, nyu-legacy]
     - check wlan0 for [nyu, nyu-legacy]
     - check if internet is already connected thru any interface

    '''
    _iface_objs = {}  # cache at a class level - move if iw.Wlan gets more specific
    restart_missing_ip = False
    interfaces = ()
    interval = 0

    # initialization
    @log_kw('Config updated')
    def _on_config_update(self, *,
            interfaces=None, lifeline=os.getenv('LIFELINE_SSID'),
            networks=None, ap_path=None, restart_missing_ip=False, interval=20):
        self.interval = interval
        self.restart_missing_ip = restart_missing_ip
        self.interfaces = (
                ([{'interface': 'wlan*', 'ssids': lifeline, 'require_internet': False}] if lifeline else []) + [
                util.abbr_config(c, 'interface') for c in util.flatten(
                    ['eth*', 'ppp*', 'wlan*'] if interfaces is None else interfaces or [])
            ]
        )

        if lifeline:
            logger.debug('Using lifeline network: %s', lifeline)
        if ap_path:
            wpasup.set_ap_path(ap_path)
        for w in networks or ():
            wpasup.generate_wpa_config(**w)

    @functools.wraps(_on_config_update)
    def __init__(self, __config=None, **kw):
        fname = __config if isinstance(__config, str) else None
        if not fname and __config:
            kw['interfaces'] = __config
        self.config = Config(fname, self._on_config_update, **kw)

    # public interface

    def check(self):
        '''Check internet connections and interfaces. Return True if connected.'''
        self.config.refresh()
        interfaces = ifcfg.interfaces()
        logger.info('Interfaces: {}'.format(', '.join(interfaces) or '--'))
        for cfg in self.interfaces:
            # check if any matching interfaces are available
            ifaces = [i for i in interfaces if fnmatch.fnmatch(i, cfg['interface'])]
            logger.debug('Iface {} - matches {}'.format(cfg['interface'], ', '.join(ifaces) or '--'))

            # try to connect in order of wlan1, wlan0
            restart_missing = cfg.get('restart_missing_ip', self.restart_missing_ip)
            for iface in sorted(ifaces, reverse=True):
                if restart_missing and not interfaces[iface].get('inet'):
                    util.ifup(iface)
                #c1,c2=self.connect(iface, **cfg), (not cfg.get('require_internet', True) or internet_connected(iface))
                #logger.info(str((c1,c2)))
                if self.connect(iface, **cfg) and (not cfg.get('require_internet', True) or internet_connected(iface)):
                    #logger.info('allset!')
                    return True
        # check if internet is connected anyways
        return internet_connected()

    def run(self, interval=None):
        interval = self.interval if interval is None else interval
        self.summary()
        self.check()
        while True:
            time.sleep(interval)
            self.check()
        self.summary()

    # internal interface

    def connect(self, iface, **kw):
        '''Connect to an interface.'''
        if iface not in self._iface_objs:
            self._iface_objs[iface] = self._get_iface_obj(iface)
        connect = getattr(self._iface_objs.get(iface), 'connect', None)
        return connect(**kw) if callable(connect) else True

    def _get_iface_obj(self, iface):
        if fnmatch.fnmatch(iface, 'wlan*'):
            return iw.WLan(iface=iface)
        return

    # supplimentary interface

    def __getitem__(self, index):
        return self.__class__(self.interfaces[index])

    def __str__(self):
        return self._summary()

    def summary(self):
        logger.info(self._summary())

    def _summary(self):
        import json
        return '\n' + '\n'.join((
            '-'*50,
            'Current Network:',
            wpasup.Wpa()._summary(),
            '', 'Trusted APs: {}'.format(', '.join(wpasup.ssids_from_dir(wpasup.Wpa.ap_path))),
            '', 'Priority Config: {}'.format(self.interfaces),
            # '', 'Available Networks:',
            # json.dumps(ifcfg.interfaces(), indent=4, sort_keys=True),
            '', 'Interfaces:',
            '\n'.join('\t{:<16}: {:>16} {:>18}'.format(
                str(d.get('device')), str(d.get('inet')), str(d.get('ether')),
            ) for d in ifcfg.interfaces().values()),
            # json.dumps(ifcfg.interfaces(), indent=4, sort_keys=True),
            '-'*50,
        )) + '\n'


class Config(dict):
    _mtime = None
    def __init__(self, fname, on_update=None, filter_none_=False, **kw):
        super().__init__()
        self.fname = fname
        self.on_update = on_update
        if filter_none_:
            kw = {k: v for k, v in kw.items() if v is not None}
        self._passed_kw = kw
        self.refresh(force=True)

    def __getattr__(self, key):
        if key not in self:
            raise AttributeError(key)
        return self[key]

    def refresh(self, force=False):
        # check time, maybe load file
        new, mtime = {}, None
        if self.fname and os.path.isfile(self.fname):
            mtime = os.path.getmtime(self.fname)
            if not force and self._mtime and mtime == self._mtime:
                return   # there was a file before and it is the same
            with open(self.fname, 'r') as f:
                new = yaml.safe_load(f)
        elif not force and self._mtime is None:
            if self.fname:
                logger.warning('Config file {} was specified, but was not '
                               'found. Assuming a blank configuration.'.format(self.fname))
            return  # there was no file before, and there's still not one

        # keep going for: old file -> new file, file -> no file, no file -> file
        # update the callbacks
        new = dict(new, **self._passed_kw)
        if callable(self.on_update):
            modified = self.on_update(**new)
            if modified is not None:  # on_update can return a modified config
                new = modified

        # update the config object
        self.clear()
        self.update(new)
        self._mtime = mtime


#@util._debug_args
# @functools.wraps(NetSwitch)
def run(config=None, interval=20, **kw):
    witch = NetSwitch(config, **kw)
    try:
        witch.run(interval=interval)
    except KeyboardInterrupt:
        print('Interrupted.')
    return witch


if __name__ == '__main__':
    NetSwitch([
        {'interface': 'wlan*', 'ssids': ['s0nycL1f3l1ne']},
        {'interface': 'eth*'},
        {'interface': 'ppp*'},
        {'interface': 'wlan*', 'ssids': '*'},
    ])
