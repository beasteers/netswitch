#!/usr/bin/env python
import os

ETC_INTERFACES_FNAME = '/etc/network/interfaces'

SUPER_BLOCK_KEYS = 'iface', 'mapping'
SUPER_LINE_KEYS = 'auto', 'allow-', 'source'
SUPER_KEYS = SUPER_BLOCK_KEYS + SUPER_LINE_KEYS

IGNORED_IFACES = ('lo',)


class Interfaces:
    """Manage /etc/network/interfaces file

    Source: https://gist.github.com/Apsu/8799432
    """
    body = ''
    def __init__(self, fname=ETC_INTERFACES_FNAME):
        fname, lines = (fname, None) if isinstance(fname, str) else (None, fname)
        self.fname = fname
        if os.path.isfile(fname):
            with open(self.fname, 'r') as f:
                self.body = f.read()
        self.lines = [l for l in (l.strip() for l in self.body.splitlines()) if l]
        self.directives = self.parse(self.lines)  # Parsed directives

    def __str__(self):
        return '\n'.join([
            str(sup) +
            ''.join(['\n    {}'.format(s) for s in subs]) +
            ('\n' if sup.startswith(SUPER_BLOCK_KEYS) else '')
            for sup, subs in self.directives
        ])

    def parse(self, lines):
        "Parse super- and sub-directives, and return nested results"
        it = iter(lines)
        directives = []
        for directive in it:
            while directive.startswith(SUPER_BLOCK_KEYS):  # If we're on a super, start sub loop
                sup, subs = None, []  # Clear super/sub directives
                for sub in it:
                    if sub.startswith(SUPER_KEYS):  # If sub is actually a super
                        sup = sub
                        break
                    subs.append(sub) # Else it's just a sub, so add it
                directives.append([directive, subs])
                if not sup:  # If we didn't find a super, return
                    return directives
                directive = sup  # Store super for next inner loop check
            # Not a super here so just add directive
            directives.append([directive, []])
        return directives

    def save(self, fname):
        with open(fname, 'w') as f:
            f.write(str(self))

    def swap(self, one, two):
        "Swap one directive with another"
        for i, (sup, _) in enumerate(self.directives):
            self.directives[i][0] = sup.replace(one, two)

    def add_subs(self, sup, subs, offset=0):
        "Add sub-directives to super-directive"
        for supi, subsi in self.directives[offset:]:
            if sup in supi:
                subsi.extend(subs)
                return
        self.directives.append((sup, subs))

    @property
    def iface_priority(self):
        return unique([
            p[1] for p in (l.split(' ') for l, subs in self.directives)
            if p[0] in SUPER_BLOCK_KEYS and p[1] not in IGNORED_IFACES])


def unique(it):
    seen = set()
    return [x for x in it if not x in seen and not seen.add(x)]


# class Directive:
#     def __init__(self, sup, subs=()):
#         self.sup, self.subs = sup, list(subs)
#
#     def __str__(self):
#         return (
#             str(self.sup) +
#             ''.join(['\n    {}'.format(s) for s in self.subs]) +
#             ('\n' if self.sup.startswith(SUPER_BLOCK_KEYS) else '')
#         )
#
#     def append(self, *sub):
#         self.subs.append(' '.join(sub))
#
#     def extend(self, *subs):
#         self.subs.extend(subs)
#
#     def replace(self, one, two):
#         self.sup = self.sup.replace(one, two)
#
#
# class Iface(Directive):
#     def __init__(self, iface, subs=(), allow='hotplug', ipv6=False, method='manual'):
#         sup = 'iface {} inet{} {}'.format(iface, '6'*ipv6, method)
#         if allow:
#             sup = 'allow-{} {}\n'.format(allow, iface) + sup
#         super().__init__(sup, list(subs))
#
#
# def ppp(i=0, *a, **kw):
#     return iface('ppp{}'.format(i), *a, **kw)


if __name__ == '__main__':
    ifaces = Interfaces('input.txt')
    ifaces.swap("eth3", "lxb-mgmt")
    ifaces.add_subs("iface lxb-mgmt inet manual", [
        "pre-up ip link add name phy-lxb-mgmt "
        "type veth peer name ovs-lxb-mgmt || true",
        "bridge_ports eth3 phy-lxb-mgmt"
    ])
    print(ifaces.directives)
    print(ifaces)

    assert ifaces.iface_priority == ['eth0', 'eth1', 'eth2', 'lxb-mgmt']

    expected = Interfaces('output.txt')
    assert expected.directives == ifaces.directives
