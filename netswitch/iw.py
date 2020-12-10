import time
from collections import Counter
from access_points import get_scanner
import logging


logger = logging.getLogger(__name__)


class WLan:
    def __init__(self, iface='wlan0'):
        self.iface = iface
        self.wifi_scanner = get_scanner(iface)

    def scan(self, trusted=None):
        aps = self.wifi_scanner.get_access_points()
        aps = sorted(aps, key=lambda ap: ap.quality, reverse=True)
        #logger.info('all aps: {}'.format([a.ssid for a in aps]))
        return [ap for ap in aps if ap.ssid in trusted] if trusted else aps

    def ap_available(self, ap):
        '''Check if an ap is available.'''
        return any(1 for ap_i in self.scan() if ap in ap_i.ssid)

    def select_best_ssid(self, ssids=None, nmin=3, return_all=False, n_single=4, **kw):
        # handle special cases
        if len(ssids) == 1:
            logger.debug('Checking for network: {}'.format(ssids[0]))
            return any(self.ap_available(ssids[0]) for _ in range(n_single)) and ssids[0]
        # select best
        top_seen, all_seen = self._get_top_ssids(ssids, **kw)
        most_common = Counter(top_seen).most_common(1)
        ap, count = most_common[0] if most_common else (None, -1)
        out_ap = count >= nmin and ap
        if ap and not out_ap:
            logger.debug('AP ({}) was available but not strong enough ({}/{}).'.format(ap, count, nmin))
        return (out_ap, all_seen) if return_all else out_ap

    def _get_top_ssids(self, ssids=None, nscans=5, throttle=1, timeout=30):
        all_seen, top_seen = set(), []
        t0 = time.time()
        #logger.debug('Selecting best network from: {}'.format(ssids or 'all'))
        while len(top_seen) < nscans:
            sids = [ap.ssid for ap in self.scan()]
            trusted = [s for s in sids if s in ssids] if ssids else sids
            logger.info('Scan {} - trusted: {}, all={}'.format(
                len(top_seen), trusted, len(sids)))
            all_seen.update(trusted)
            top_seen.extend(trusted[:1])
            # throttle and timeout
            time.sleep(throttle)
            if timeout and time.time() - t0 >= timeout:
                break
        return top_seen, all_seen
