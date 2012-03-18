__import__("pkg_resources").declare_namespace(__name__)

from infi.pyutils.contexts import contextmanager
from logging import getLogger

logger = getLogger()

class PackageNotFound(Exception):
    pass

class SourceDistributionNotFound(Exception):
    pass

class UnsupportedArchive(Exception):
    pass

class InvalidArchive(Exception):
    pass

class PyPI(object):
    def __init__(self):
        import xmlrpclib
        self._client = xmlrpclib.ServerProxy('http://pypi.python.org/pypi')

    def get_available_versions(self, package_name):
        releases = self._client.package_releases(package_name)
        logger.info("Versions found for {!r}: {!r}".format(package_name, releases))
        if len(releases) == 0:
            raise PackageNotFound(package_name)
        return releases

    def get_latest_version(self, package_name):
        from pkg_resources import parse_version
        return self.get_available_versions(package_name)[-1]

    def get_releases_for_version(self, package_name, release_version):
        return self._client.release_urls(package_name, release_version)

    def get_latest_source_distribution_url(self, package_name):
        release_version = self.get_latest_version(package_name)
        for release in filter(lambda release: release['packagetype'] == 'sdist',
                              self.get_releases_for_version(package_name, release_version)):
            return release['url']
        raise SourceDistributionNotFound(package_name, release_version)

def download_package_from_global_pypi(package_name):
    from urllib2 import urlopen
    from tempfile import mkstemp
    from os import write, close
    pypi = PyPI()
    url = pypi.get_latest_source_distribution_url(package_name)
    data = urlopen(url).read()
    fd, path = mkstemp(suffix=url.split('/')[-1])
    write(fd, data)
    close(fd)
    logger.info("Downloaded {} to {}".format(url, path))
    return path

def upload_package_to_local_pypi(distribution_format):
    from infi.execute import execute
    command = ['python', 'setup.py', 'register', '-r', 'local',
                          distribution_format, 'upload', '-r', 'local']
    logger.info("Executing {}".format(' '.join(command)))
    subprocess = execute(command)
    logger.info(subprocess.get_stdout())
    logger.info(subprocess.get_stderr())
    subprocess._assert_success()

def upload_sdist_to_local_pypi():
    upload_package_to_local_pypi('sdist')

def extract_source_package_to_tempdir(package_source_archive):
    from tempfile import mkdtemp
    import os
    tempdir = mkdtemp()
    logger.info("Unpacking {} to {}".format(package_source_archive, tempdir))
    if package_source_archive.endswith('zip'):
        from zipfile import ZipFile
        archive = ZipFile(package_source_archive)
        archive.extractall(tempdir)
    elif package_source_archive.endswith('tar.gz'):
        from tarfile import open
        archive = open(package_source_archive, mode='r:gz')
        archive.extractall(tempdir)
    else:
        raise UnsupportedArchive(package_source_archive)
    if os.path.exists(os.path.join(tempdir, 'setup.py')):
        return tempdir
    for dirname in os.listdir(tempdir):
        if os.path.exists(os.path.join(tempdir, dirname, 'setup.py')):
            return os.path.join(tempdir, dirname)
    raise InvalidArchive(package_source_archive, tempdir)

@contextmanager
def chdir(path):
    import os
    curdir = os.path.abspath(os.path.curdir)
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(curdir)