import sys
import re
import fnmatch
import subprocess
import logging

logger = logging.getLogger(__name__)


def _debug_args(func):
    def inner(*a, **kw):
        print('calling', func.__name__, a, kw)
        return func(*a, **kw)
    return inner


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
        k: ch*len(v) if v and k in keys else v
        for k, v in dct.items()
        if not drop or k not in drop
    }


def indent(txt, n=1, w=2):
    return ''.join(' '*w*n + l for l in txt.splitlines(keepends=True))


def abbr_config(value, key):
    return value if isinstance(value, dict) else {key: value}


# internet

_packet_loss = re.compile(r'([\d.]+)% packet loss')
def internet_connected(iface=None, n=3, reliability=0.5):
    '''Check if we're connected to the internet (optionally, check a specific interface `iface`)'''
    cmd = "ping {} -c {} 8.8.8.8".format('-I {}'.format(iface) if iface else '', n)
    #logger.info(cmd)
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    matches = _packet_loss.search(result.stdout.decode('utf-8'))
    #logger.info('stdout: {}'.format(result.stdout.decode('utf-8')))
    if matches:
        loss = float(matches.groups()[0])/100
        if 0 < loss < 1 and loss > reliability:
            logger.warning('packet loss high: {:.1%}'.format(loss))
        return loss < reliability
    return False


# ifup / ifdown

def _ifupdown_(cmd, name, sleep=1, force=True):
    try:
        subprocess.run(
            #'if{} {} {} && sleep {}'.format(cmd, name, force*'--force', sleep),
            'ifconfig {} {} && sleep {}'.format(name, cmd, sleep),
            check=True, capture_output=True, shell=True)
    except subprocess.CalledProcessError as e:
        logger.error(e.stderr and e.stderr.decode())
        return False
    return True

def ifup(name, sleep=1, force=True):
    return _ifupdown_('up', name, sleep=sleep, force=force)

def ifdown(name, sleep=1, force=True):
    return _ifupdown_('down', name, sleep=sleep, force=force)

def restart_iface(name=None, sleep=3):
    '''Restart the specified network interface. Returns True if restarted without error.'''
    logger.info("Restarting Interface: {}".format(name))
    went_down = ifdown(name, sleep)
    back_up = ifup(name, sleep)
    return went_down and back_up
