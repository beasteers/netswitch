import os
import re
import sys
import glob
import time
# import shlex
import functools
import fnmatch
import subprocess
import ifcfg
import yaml
from . import iw, wpasup, util
# import cachetools.func
from .util import internet_connected

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)  # INFO



def _debug_args(func):
    def inner(*a, **kw):
        print('calling', func.__name__, a, kw)
        return func(*a, **kw)
    return inner


def _maybe_load_yaml(func):  # this is so that we can pull parameters from a yaml file
    #@_debug_args
    @functools.wraps(func)
    def inner(self, config=None, **kw):
        if isinstance(config, str):
            kw = dict(yaml.load(config), **kw)
            config = kw.pop('config', None)
        return func(self, config, **kw)
    return inner


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
    wlans = {}  # cache at a class level - move if iw.Wlan gets more specific
    @_maybe_load_yaml
    def __init__(self, config=None, lifeline=os.getenv('LIFELINE_SSID'), networks=None, ap_path=None, restart_missing_ip=False):
        config = config or ['eth*', 'ppp*', 'wlan*']
        self.config = [
            {'interface': c} if isinstance(c, str) else c
            for c in (config if isinstance(config, (list, tuple)) else [config])
        ]
        self.restart_missing_ip = restart_missing_ip
        if lifeline:
            logger.info('Using lifeline network: {}'.format(lifeline))
            self.config = [{'interface': 'wlan*', 'ssids': lifeline}] + self.config
        if ap_path:
            wpasup.set_ap_path(ap_path)
        for w in networks or ():
            wpasup.generate_wpa_config(**w)

    def __str__(self):
        return self._summary()

    def check(self, test=False):
        '''Check internet connections and interfaces. Return True if connected.'''
        interfaces = ifcfg.interfaces()
        logger.info('Interfaces: {}'.format(list(interfaces)))
        for cfg in self.config:
            # check if any matching interfaces are available
            ifaces = [
                i for i in interfaces
                if fnmatch.fnmatch(i, cfg['interface'])]

            logger.info('Iface {} - matches {}'.format(cfg['interface'], ifaces))
            # try to connect in order of wlan1, wlan0
            restart_missing = cfg.get('restart_missing_ip', self.restart_missing_ip)
            for iface in sorted(ifaces, reverse=True):
                if restart_missing and not interfaces[iface].get('inet'):
                    util.ifup(iface)
                    #logger.info('ifup {} {}'.format(iface, interfaces[iface].get('inet')))
                if self.connect(iface, cfg) and internet_connected(iface):
                    return True
        # check if internet is connected anyways
        return internet_connected()

    def run(self, interval=10):
        self.summary()
        self.check()
        while True:
            time.sleep(interval)
            check = self.check()
            # logger.debug('Finished check. Connected to internet? {}'.format(check))
        self.summary()

    def connect(self, iface, cfg, **kw):
        '''Connect to an interface.'''
        if fnmatch.fnmatch(iface, 'wlan*'):
            return self.connect_wlan(iface, cfg, **kw)
        return True

    def connect_wlan(self, iface, cfg, test=False):
        # get the wlan connection object
        if iface not in self.wlans:  # cache it for future use
            self.wlans[iface] = iw.WLan(iface=iface)
        wlan = self.wlans[iface]

        # get matching ssids
        ssids = cfg.get('ssids', '*')
        if not isinstance(ssids, (list, tuple)):  # coerce to list of globs
            ssids = [ssids]
        ssids = [
            os.path.splitext(os.path.basename(s))[0] for pat in ssids
            for s in glob.glob(wpasup.ssid_path(pat))]

        # check for available ssids and take best one
        ssid = wlan.select_best_ssid(ssids)
        if not ssid:
            logger.info('No wifi matches.')
            return

        connected = test or wpasup.connect(ssid, verify=True)
        logger.info(
            'AP ({}) Connected? {}. [{}]'.format(
                ssid, connected, iface))
        return connected

    def __getitem__(self, index):
        return self.__class__(self.config[index])

    def _summary(self):
        import json
        return '\n' + '\n'.join((
            '-'*50,
            'Current Network:',
            wpasup.Wpa()._summary(),
            '', 'Trusted APs: {}'.format(', '.join(wpasup.ssids_from_dir(wpasup.Wpa.ap_path))),
            '', 'Config: {}'.format(self.config),
            # '', 'Available Networks:',
            # json.dumps(ifcfg.interfaces(), indent=4, sort_keys=True),
            '', 'Interfaces:',
            '\n'.join('\t{:<16}: {:>16} {:>18}'.format(
                str(d.get('device')), str(d.get('inet')), str(d.get('ether')),
            ) for d in ifcfg.interfaces().values()),
            # json.dumps(ifcfg.interfaces(), indent=4, sort_keys=True),
            '-'*50,
        )) + '\n'

    def summary(self):
        logger.info(self._summary())


#@_debug_args
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
