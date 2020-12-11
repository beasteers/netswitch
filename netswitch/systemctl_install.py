


SERVICE_FNAME_TEMPLATE = '/etc/systemd/system/{}.service'
SERVICE_TEMPLATE = '''
[Unit]
Description={name}
StartLimitIntervalSec=0

[Service]
ExecStart=/usr/bin/python3 -n netswitch run {args}
StandardOutput=append:/var/log/{name}_stdout.log
StandardError=append:/var/log/{name}_stderr.log
Restart=always
RestartSec={restartsec}
Type=simple
User=root

[Install]
WantedBy=multi-user.target
'''


def install(*a, name='netswitch', restartsec=10, enable=True, **kw):
    import shlex
    import subprocess
    _esc = lambda x: shlex.quote(repr(x))

    args = ' '.join([_esc(x) for x in a] + [
        '--{} {}'.format(k, _esc(v)) for k, v in kw.items()])

    with open(SERVICE_FNAME_TEMPLATE.format(name), 'w') as f:
        f.write(SERVICE_TEMPLATE.format(
            args=args, name=name, restartsec=restartsec))

    # start service
    subprocess.run(
    (['systemctl', 'enable', name, '&&',] if enable else []) + [
        'systemctl', 'start', name, '&&',
        'sleep', '1', '&&',
        'systemctl', 'status', name
    ], check=True)
