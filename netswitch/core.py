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

    def check(self):
        '''Check internet connections and interfaces. Return True if connected.'''
        interfaces = list(ifcfg.interfaces())
        # print('Interfaces: {}'.format(interfaces))
        for cfg in self.config:
            # check if any matching interfaces are available
            ifaces = [
                i for i in interfaces
                if fnmatch.fnmatch(i, cfg['interface'])]
            # try to connect in order of wlan1, wlan0
            for iface in sorted(ifaces, reverse=True):
                if self.connect(iface, cfg) and internet_connected(iface):
                    return True
        # check if internet is connected anyways
        return internet_connected()

    def run_check(self, interval=10):
        self.check()
        while True:
            time.sleep(interval)
            self.check()

    def connect(self, iface, cfg):
        '''Connect to an interface.'''
        if fnmatch.fnmatch(iface, 'wlan*'):
            return self.connect_wlan(iface, cfg)
        return True

    def connect_wlan(self, iface, cfg):
        # get the wlan connection object
        if iface not in self.wlans:  # cache it for future use
            self.wlans[iface] = iw.WLan(iface=iface)
        wlan = self.wlans[iface]

        # get matching ssids
        ssids = cfg.pop('ssids', '*')
        if not isinstance(ssids, (list, tuple)):  # coerce to list of globs
            ssids = [ssids]
        ssids = [
            s for pat in ssids for s in glob.glob(wpasup.Wpa.ssid_path(pat))]

        if not ssids:  # nothing to connect to
            return False

        if len(ssids) == 1:  # only one, don't need to compare
            return wlan.ap_available(ssids[0]) and wpasup.Wpa(ssids[0]).connect()

        # check for available ssids and take best one
        ssid = wlan.select_best_ssid(ssids)
        available = ssid is not None
        connected = available and wpasup.Wpa(ssid).connect()
        logger.info(
            f'Requested AP ({ssid}) Available? {available}. Connected? {connected}.')
        return connected

    def __getitem__(self, index):
        return self.__class__(self.config[index])


def internet_connected(iface=None, n=3):
    '''Check if we're connected to the internet (optionally, check a specific interface `iface`)'''
    result = subprocess.run(
        shlex.split("ping {} -c {} 8.8.8.8".format(
            '-I {}'.format(iface) if iface else '', n)),
        capture_output=True, check=True)
    return not result.stderr



if __name__ == '__main__':
    NetSwitch([
        {'interface': 'wlan*', 'ssids': ['s0nycL1f3l1ne']},
        {'interface': 'eth*'},
        {'interface': 'ppp*'},
        {'interface': 'wlan*', 'ssids': '*'},
    ])
