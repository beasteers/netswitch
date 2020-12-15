import os
import glob
import math
import time
from collections import Counter
from access_points import get_scanner
import logging
from . import util, wpasup


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WLan:
    def __init__(self, iface='wlan0'):
        self.iface = iface
        self.wifi_scanner = get_scanner(iface)
        self._failed_ssids = {}

    def scan(self, trusted=None):
        aps = self.wifi_scanner.get_access_points()
        aps = sorted(aps, key=lambda ap: ap.quality, reverse=True)
        #logger.info('all aps: {}'.format([a.ssid for a in aps]))
        return [ap for ap in aps if ap.ssid in trusted] if trusted else aps

    def ap_available(self, ap):
        '''Check if an ap is available.'''
        return any(1 for ap_i in self.scan() if ap in ap_i.ssid)

    def select_best_ssid(self, ssids=None, top=0.5, return_all=False, nscans=5, **kw): #, n_single=4
        if ssids and len(ssids) < 3:
            logger.info('[{}] Checking for networks: {}'.format(self.iface, ', '.join(ssids)))
        #    return any(self.ap_available(ssids[0]) for _ in range(n_single)) and ssids[0]
        # select best
        nmin = math.ceil(nscans*top)
        top_seen, all_seen = self._get_top_ssids(ssids, nscans=nscans, **kw)
        most_common = Counter(top_seen).most_common(1)
        ap, count = most_common[0] if most_common else (None, -1)
        out_ap = count >= top and ap
        if ap and not out_ap:
            logger.debug('AP ({}) was seen but not strong enough ({}/{}).'.format(ap, count, nmin))
        return (out_ap, all_seen) if return_all else out_ap

    def _get_top_ssids(self, ssids=None, nscans=5, throttle=1, timeout=30, nfails=3):
        all_seen, top_seen = set(), []
        t0 = time.time()
        #logger.debug('Selecting best network from: {}'.format(ssids or 'all'))
        while len(top_seen) < nscans:
            # get ssid names
            sids = [ap.ssid for ap in self.scan()]
            # filter only the trusted ones
            trusted = [s for s in sids if s in ssids] if ssids is not None else sids
            # remove any failed ssids
            trusted = [s for s in trusted if self._failed_ssids.get(s, 0) < nfails]

            logger.debug('Scan {} - trusted: {}, all={}'.format(
                len(top_seen), trusted, len(sids)))
            all_seen.update(trusted)
            top_seen.extend(trusted[:1])
            # throttle and timeout
            time.sleep(throttle)
            if timeout and time.time() - t0 >= timeout:
                break
        return top_seen, all_seen

    def connect(self, ssids='*', test=False, **kw):
        current = wpasup.Wpa().ssid
        originally_connected = util.internet_connected(self.iface)
        # coerce to list of globs
        ssids = [
            os.path.splitext(os.path.basename(s))[0]
            for pat in util.flatten(ssids)
            for s in glob.glob(wpasup.ssid_path(pat))]
        if not ssids:
            logger.warning('No ssid conf files found matching the provided pattern. Check your aps directory.')
            return

        # check for available ssids and take best one
        ssid = self.select_best_ssid(ssids)
        if not ssid:
            logger.info('[{}] No ssid matches.'.format(self.iface))
            return

        # connect to new network, revert if it failed (e.g. the password was wrong)
        connected = test or wpasup.connect(ssid, verify=True)
        if not connected and current and originally_connected:
            self._failed_ssids[ssid] = self._failed_ssids.get(ssid, 0) + 1
            logger.warning('Could not connect to {}. reverting back to {}'.format(ssid, current))
            ssid = current
            connected = test or wpasup.connect(ssid, verify=True)

        logger.info('[{}] AP ({}) Connected? {}.'.format(self.iface, ssid, connected))
        return connected
