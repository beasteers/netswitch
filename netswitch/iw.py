import time
from collections import Counter
from access_points import get_scanner


class WLan:
    def __init__(self, iface='wlan0'):
        self.iface = iface
        self.wifi_scanner = get_scanner(iface)

    def scan(self, trusted=None):
        aps = self.wifi_scanner.get_access_points()
        aps = sorted(aps, key=lambda ap: ap.quality, reverse=True)
        return [ap for ap in aps if ap.ssid in trusted] if trusted else aps

    def ap_available(self, ap):
        '''Check if an ap is available.'''
        return any(1 for ap_i in self.scan() if ap in ap_i.ssid)

    def select_best_ssid(self, ssids=None, nmin=3, **kw):
        if ssids is not None:  # handle special cases
            if not ssids:
                return None
            if len(ssids) == 1:
                return self.ap_available(ssids[0]) and ssids[0]
        # select best
        top_seen, all_seen = self._get_top_ssids(ssids, **kw)
        most_common = Counter(top_seen).most_common(1)
        ap, count = most_common[0] if most_common else (None, -1)
        return count >= nmin and ap, all_seen

    def _get_top_ssids(self, ssids=None, nscans=5, throttle=0.6, timeout=10):
        all_seen, top_seen = set(), []
        t0 = time.time()
        while len(all_seen) < nscans:
            sids = [ap.ssid for ap in self.scan(ssids)]
            all_seen.update(sids)
            top_seen.extend(sids[:1])
            # throttle and timeout
            time.sleep(throttle)
            if timeout and time.time() - t0 >= timeout:
                break
        return top_seen, all_seen
