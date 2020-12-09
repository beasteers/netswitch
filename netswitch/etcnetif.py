'''

source-directory /etc/network/interfaces.d

auto lo
iface lo inet loopback

auto eth0
iface eth0 inet manual

allow-hotplug ppp0
iface ppp0 inet wvdial
post-up echo "cellular (ppp0) is online"

allow-hotplug wlan0
iface wlan0 inet manual
wpa-roam /etc/wpa_supplicant/wpa_supplicant.conf

allow-hotplug wlan1
iface wlan1 inet manual
wpa-roam /etc/wpa_supplicant/wpa_supplicant.conf
'''
import re
import functools

def _expand_wildcard(*rng):
    def outer(func):
        @functools.wraps(func)
        def inner(i='*', *a, **kw):
            return (
                '\n'.join(func(i, *a, **kw) for i in range(*rng))
                if i == '*' else func(i, *a, **kw))
        return inner
    return outer


# interfaces

def source_dir(fname='/etc/network/interfaces.d'):
    return 'source-directory {}'.format(fname)

def lo(**kw):
    return _iface('lo', method='loopback', **kw)

@_expand_wildcard(2)
def eth(i=0, **kw):
    return _iface('eth{}'.format(i), **kw)

@_expand_wildcard(2)
def wlan(i=0, wpa='/etc/wpa_supplicant/wpa_supplicant.conf', roam=True, **kw):
    kw['wpa_{}'.format('roam' if roam else 'conf')] = wpa
    return _iface('wlan{}'.format(i), hotplug=True, **kw)

@_expand_wildcard(2)
def ppp(i=0, method='wvdial', **kw):
    name = 'ppp{}'.format(i)
    return _iface(
        name, hotplug=True, method=method,
        post_up='echo "cellular ({}) is online"'.format(name), **kw)


IFACES = {'wlan': wlan, 'eth': eth, 'ppp': ppp}

def iface(name, *a, **kw):
    if callable(name):
        return name(*a, **kw)
    matches = re.search(r'([A-z]+)([\d\*]*)', name)
    name, i = matches.groups()
    return IFACES[name.lower()](i or '*', *a, **kw)

# utils

def _iface(name, method='manual', hotplug=False, static=None, **kw):
    return '''
{allow} {name}
iface {name} inet {method}
{extra}
'''.format(
    name=name, allow='allow-hotplug' if hotplug else 'auto', method=method,
    extra='\n'.join(l for k, v in kw.items() for l in _cfg_lines(k, v)))

def _cfg_lines(name, value):
    name = name.replace('_', '-')
    for v in value if isinstance(value, (list, tuple)) else [value]:
        yield '{} {}'.format(name, v)


# config formats

def build_file(*ifaces):
    return '\n'.join([source_dir(), lo()] + [
        ifc() if callable(ifc) else ifc for ifc in ifaces
    ])

def default():
    return build_file(eth, ppp, wlan)

def from_config(config=None):
    config = [
        {'interface': 'wlan*', 'ssids': 's0nycL1f3l1ne'},
        {'interface': 'eth*'},
        {'interface': 'ppp*'},
        {'interface': 'wlan*'},
    ]
    return build_file(*(
        iface(c['interface'], **c.get('etc', {}))
        for c in config
    ))


if __name__ == '__main__':
    import fire
    fire.Fire()
