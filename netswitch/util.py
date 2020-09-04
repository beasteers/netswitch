import sys
import fnmatch
import subprocess
import logging

logger = logging.getLogger(__name__)


def matches(pattern, items):
    patterns = list(flatten(pattern)) or ['*']
    return [
        item for item in items
        if any(
            fnmatch.fnmatch(item, pattern)
            for pattern in patterns
        )
    ]


def flatten(*items):
    '''Yield items from any nested iterable.'''
    for item in items:
        if isinstance(item, (list, tuple)):
            yield from flatten(*item)
        else:
            yield item



def mask_dict_values(dct, *keys, ch='*', drop=None):
    return {
        k: '*'*len(v) if v in keys else v
        for k, v in dct.items()
        if not drop or k not in drop
    }


def indent(txt, n=1, w=2):
    return ''.join(' '*w*n + l for l in txt.splitlines(keepends=True))



def restart_iface(ifname=None, sleep=3):
    '''Restart the specified network interface. Returns True if restarted without error.'''
    logger.info("Restarting Interface: {}".format(ifname))
    try:
        subprocess.run(
            'ifdown {} --force && sleep {}'.format(ifname, sleep),
            check=True, stderr=sys.stderr, shell=True)
    finally:
        subprocess.run(
            'ifup {} && sleep {}'.format(ifname, sleep),
            check=True, stderr=sys.stderr, shell=True)
    return True
