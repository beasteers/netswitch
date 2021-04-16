import setuptools

USERNAME = 'beasteers'
NAME = 'netswitch'

setuptools.setup(
    name=NAME,
    version='0.1.4',
    description='wifi switching',
    long_description=open('README.md').read().strip(),
    long_description_content_type='text/markdown',
    author='Bea Steers',
    author_email='bea.steers@gmail.com',
    url='https://github.com/{}/{}'.format(USERNAME, NAME),
    packages=setuptools.find_packages(),
    # package_data={NAME: {'*.service'}},
    entry_points={'console_scripts': ['{name}={name}:cli'.format(name=NAME)]},
    install_requires=['ifcfg', 'access_points', 'pyserial', 'pyyaml', 'fire'],
    license='BSD 3-Clause Clear License',
    keywords='wifi switching network raspberry pi wpa supplicant wlan wlan0 ppp0 eth0')
