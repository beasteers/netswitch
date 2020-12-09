import os
import sys
import glob
import time
# import shlex
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


def monitor(config, interval=10):
    witch = NetSwitch(config)
    witch.run(interval=interval)
    return witch


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
    def __init__(self, config=None, lifeline=os.getenv('LIFELINE_SSID'), wifi=None):
        config = config or ['eth*', 'ppp*', 'wlan*']
        self.config = [
            {'interface': c} if isinstance(c, str) else c
            for c in (config if isinstance(config, (list, tuple)) else [config])
        ]
        if lifeline:
            self.config = [{'interface': 'wlan*', 'ssids': lifeline}] + self.config
        for w in wifi:
            wpasup.generate_wpa_config(**w)

    @classmethod
    def from_yaml(cls, fname):
        return cls(**yaml.load(fname))

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
            for iface in sorted(ifaces, reverse=True):
                if not interfaces[iface].get('inet'):
                    util.ifup(iface)
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

    def summary(self):
        import json
        print()
        print('\n'.join((
            '-'*50,
            'Current Network:',
            wpasup.Wpa()._summary(),
            # '', 'Available Networks:',
            # json.dumps(ifcfg.interfaces(), indent=4, sort_keys=True),
            '', 'Interfaces:',
            '\n'.join('\t{:<12}: {:>16} {:>18}'.format(
                str(d.get('device')), str(d.get('inet')), str(d.get('ether')),
            ) for d in ifcfg.interfaces().values()),
            # json.dumps(ifcfg.interfaces(), indent=4, sort_keys=True),
            '-'*50,
        )))
        print()


if __name__ == '__main__':
    NetSwitch([
        {'interface': 'wlan*', 'ssids': ['s0nycL1f3l1ne']},
        {'interface': 'eth*'},
        {'interface': 'ppp*'},
        {'interface': 'wlan*', 'ssids': '*'},
    ])
