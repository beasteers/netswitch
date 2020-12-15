

import shlex

SERVICE_FNAME_TEMPLATE = '/etc/systemd/system/{}.service'
SERVICE_TEMPLATE = '''
[Unit]
Description={name}
StartLimitIntervalSec=0

[Service]
ExecStart=/usr/bin/python3 -m netswitch run {args}
StandardOutput=append:/var/log/{name}_stdout.log
StandardError=append:/var/log/{name}_stderr.log
Restart=always
RestartSec={restartsec}
Type=simple
User=root

[Install]
WantedBy=multi-user.target
'''


def format(*a, name='netswitch', restartsec=10, **kw):
    return SERVICE_TEMPLATE.format(args=asargs(*a, **kw), name=name, restartsec=restartsec)


def install(*a, name='netswitch', enable=True, **kw):
    body = format(*a, name=name, **kw)

    cmd = next((l.split('=', 1)[-1] for l in body.splitlines() if l.startswith('ExecStart')), None)
    print('writing service: {}'.format(cmd))

    with open(SERVICE_FNAME_TEMPLATE.format(name), 'w') as f:
        f.write(body)
    start_enable_service(name, enable=True)


def start_enable_service(name, enable=True):
    import subprocess
    # start service
    cmd = ([
            'systemctl', 'enable', name, '&&',] if enable else []) + [
            'systemctl', 'start', name, '&&',
            'sleep', '1', '&&',
            'systemctl', 'status', name
        ]
    #print(cmd)
    #return
    try:
        subprocess.run(cmd, stderr=subprocess.PIPE, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(e.stderr.decode())
        raise


def asargs(*a, **kw):
    return ' '.join([arg_esc(x) for x in a] + [ '--{} {}'.format(k, arg_esc(v)) for k, v in kw.items()])


import json
def arg_esc(v):
    v = json.dumps(v) #repr(v)
    if len(v) >= 2 and v[0] == v[-1] and v[0] in '\'"':
        v = v[1:-1]
    return shlex.quote(v)


if __name__ == '__main__':
    import fire
    fire.Fire()
