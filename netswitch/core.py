import sys
import glob
import time
import shlex
import fnmatch
import subprocess
import ifcfg
from . import iw, wpasup
# import cachetools.func

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)  # INFO


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
    def __init__(self, cfg):
        self.config = [
            {'interface': c} if isinstance(c, str) else c
            for c in (cfg if isinstance(cfg, (list, tuple)) else [cfg])
        ]

    def check(self, test=False):
        '''Check internet connections and interfaces. Return True if connected.'''
        interfaces = list(ifcfg.interfaces())
        logger.info('Interfaces: {}'.format(interfaces))
        for cfg in self.config:
            # check if any matching interfaces are available
            ifaces = [
                i for i in interfaces
                if fnmatch.fnmatch(i, cfg['interface'])]

            logger.info('Iface {} - matches {}'.format(cfg['interface'], ifaces))
            # try to connect in order of wlan1, wlan0
            for iface in sorted(ifaces, reverse=True):
                if self.connect(iface, cfg) and internet_connected(iface):
                    return True
        # check if internet is connected anyways
        return internet_connected()

    def run(self, interval=10):
        self.check()
        while True:
            time.sleep(interval)
            self.check()

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
        ssids = cfg.pop('ssids', '*')
        if not isinstance(ssids, (list, tuple)):  # coerce to list of globs
            ssids = [ssids]
        ssids = [
            s for pat in ssids for s in glob.glob(wpasup.ssid_path(pat))]

        # check for available ssids and take best one
        ssid = wlan.select_best_ssid(ssids)
        logger.debug('Selected ssid: {}'.format(ssid))
        available = ssid is not None
        connected = available and (test or wpasup.Wpa(ssid).connect())
        logger.info(
            'Requested AP ({}) Available? {}. Connected? {}. [{}]'.format(
                ssid, available, connected, iface))
        return connected

    def __getitem__(self, index):
        return self.__class__(self.config[index])


def internet_connected(iface=None, n=3):
    '''Check if we're connected to the internet (optionally, check a specific interface `iface`)'''
    result = subprocess.run(
        "ping {} -c {} 8.8.8.8".format(
            '-I {}'.format(iface) if iface else '', n),
        capture_output=True, check=True, shell=True)
    return not result.stderr



if __name__ == '__main__':
    NetSwitch([
        {'interface': 'wlan*', 'ssids': ['s0nycL1f3l1ne']},
        {'interface': 'eth*'},
        {'interface': 'ppp*'},
        {'interface': 'wlan*', 'ssids': '*'},
    ])
