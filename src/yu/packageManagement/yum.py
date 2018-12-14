import os
import subprocess
import fileinput


YUM_CONFIG_FILE = '/etc/yum.conf'
YUM_REPO_DIR = "/etc/yum.repos.d"

PROXY_CONFIG_MARKER = '# Proxy settings added by yu.packageManagement.yum'


def _set_system_proxy_local(proxy):
    line_found = False
    done = False

    for line in fileinput.input(YUM_CONFIG_FILE, inplace=True):
        if line.startswith("proxy=") or line_found is True:
            if done is False:
                print("proxy=" + proxy)
                line_found = False
                done = True
        elif line.startswith(PROXY_CONFIG_MARKER):
            line_found = True
        else:
            print(line.strip())
    fileinput.close()

    if done is False:
        with open(YUM_CONFIG_FILE, "a") as f:
            f.write(PROXY_CONFIG_MARKER + "\n")
            f.write("proxy=" + proxy + "\n")


def set_system_proxy(proxy):
    """
    Configure yum to use the provided proxy in the /etc/yum.conf file

    :param proxy: The proxy to use as a string in the form host:port e.g. 10.50.12.10:8080
    """
    if not proxy.startswith("http://"):
        proxy = "http://" + proxy
    return _set_system_proxy_local(proxy)


def repo_is_configured(repo_name):
    try:
        repo_list = subprocess.check_output(['yum', '-q', "repolist"]).strip().split("\n")[1:]
        for repo_line in repo_list:
            repo_line = repo_line[:repo_line.find(" ")]
            if repo_line.find(repo_name) != -1:
                return True
        return False
    except subprocess.CalledProcessError as e:
        text = "Couldn't get yum repolist. Encountered an error: " + str(e)
        if e.output is not None:
            text += "\n" + str(e.output)
        raise RuntimeError(text)


def add_repo(repo_id, repo_name, repo_baseurl, gpgcheck="0"):
    with open(os.path.join(YUM_REPO_DIR, repo_id + ".repo"), "w+") as f:
        f.write("name=" + repo_name)
        f.write("baseurl=" + repo_baseurl)
        f.write("enabled=1")
        f.write("gpgcheck=" + gpgcheck)


def add_repo_with_raw_data(repo_id, repo_data):
    with open(os.path.join(YUM_REPO_DIR, repo_id + ".repo"), "w+") as f:
        f.write(repo_data)


def is_package_installed(package_name):
    """
    Equivalent of `yum list installed <package>`

    :param package_name: Package to install
    :return: True if package is installed; otherwise False
    """
    try:
        _ = subprocess.check_output(['yum', '-q', "list", 'installed', package_name],
                                    stderr=subprocess.STDOUT)
        return True
    except subprocess.CalledProcessError as e:
        return False


def is_package_installed_on(node, package_name):
    """
    Check whether package name is installed on the node provided

    :param node: A yu.network.RemoteNode object to check
    :param package_name: Package to check
    :return: True if the package is installed; False otherwise
    """
    if node.get_location().is_local():
        return is_package_installed(package_name)

    result_code, _, = node.perform_command_on_host("yum -q --disablerepo=* list installed " + package_name)
    if result_code == 0:
        return True
    return False


def install_local_package(package_location):
    """
    Equivalent of `yum localinstall <package_location>`

    :param package_location:  the path to the package to install
    :raises Runtime error if the install failed
    """
    try:
        _ = subprocess.check_output(['yum', "localinstall", '-y', '-q', "--disablerepo=*", package_location],
                                    stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        text = "Couldn't install " + package_location + " package. Encountered an error: " + str(e)
        if e.output is not None:
            text += "\n" + str(e.output)
        raise RuntimeError(text)


def install_package(package_name):
    """
    Equivalent of `yum install <package_name>`

    :param package_name:  the package to install
    :raises Runtime error if the install failed
    """
    try:
        _ = subprocess.check_output(['yum', '-y', '-q', "install", package_name],
                                    stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        text = "Couldn't install " + package_name + " package. Encountered an error: " + str(e)
        if e.output is not None:
            text += "\n" + str(e.output)
        raise RuntimeError(text)


def install_packages(package_list):
    """
    Equivalent of yum install <package_1> <package_2> ... <package_N>
    :param package_list:  the list of packages to install
    :raises: RuntimeError if the install fails
    """
    try:
        command_list = ['yum', '-y', '-q', "install"]
        command_list.extend(package_list)

        _ = subprocess.check_output(command_list, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        text = "Couldn't install " + " ".join(package_list) + " packages. Encountered an error: " + str(e)
        if e.output is not None:
            text += "\n" + str(e.output)
        raise RuntimeError(text)


def install_package_on(node, package_name=None, package_location=None):
    """
    Install the provided package on the provided node. One of package_name or package_location must be
    provided.
    If a package name is provided then it will attempt to do a regular yum install and try to lookup
    the package in the configured yum repos.
    If a package_location is provided then it will be copied onto the node (if node is remote) before
    installing the package locally without trying to access the yum repos

    :param node: the node to install on
    :param package_name: the name of the package to install (optional)
    :param package_location: the location to an already downloaded package to install
    :return:
    """
    package_arg = None
    if package_name is None and package_location is None:
        raise RuntimeError("No package name or location to package provided to install")

    if node.get_location().is_local():
        print("yum installing locally")
        if package_location is not None:
            install_local_package(package_location)
        else:
            install_package(package_name)
        print("Success")
        return

    if package_location is not None:
        print("Copying package to " + node.get_location().address)
        node.copy_file_to(package_location)

        print("yum installing")
        result_code, result_string = node.perform_command_on_host("yum localinstall -y --disablerepo=* " +
                                                                  os.path.basename(package_location))
        if result_code != 0:
            print("Failed")
            raise RuntimeError("Couldn't install " + package_location + " on " + node.get_location().address + ": " +
                               result_string)

        print("Tidying up copied package")
        node.delete_file(package_location)
    else:
        # TODO Check if the internet is accessible and have a go
        print("Failed")
        raise RuntimeError("Couldn't install " + package_name + " on " + node.get_location().address + ": " +
                           "Attempting to install remotely without a package")
    print("Success")


def download_package(package_name, download_directory=None):
    """
    Python api equivalent of yum install --downloadonly --downloaddir=<download_directory> <package_name>
    Will return the path of the downloaded file.

    :param package_name:  The package to download
    :param download_directory: The directory to download the package to
    :raises RuntimeError if the download fails
    """
    if download_directory is None:
        download_directory = os.getcwd()
    try:
        _ = subprocess.check_output(['yum', '-q', '--downloadonly', '--downloaddir=' + download_directory,
                                     "reinstall", package_name], stderr=subprocess.STDOUT)
        potential_downloaded_files = []
        for f in os.listdir(download_directory):
            if f.startswith(package_name):
                potential_downloaded_files.append(os.path.join(download_directory, f))
        if len(potential_downloaded_files) < 1:
            raise RuntimeError("Couldn't find the downloaded package for " + package_name)
        # TODO not fool-proof but much quicker to implement than parsing the yum command output and probably
        # TODO good enough
        return max(potential_downloaded_files, key=os.path.getctime)
    except subprocess.CalledProcessError as e:
        text = "Couldn't download " + package_name + " package. Encountered an error: " + str(e)
        if e.output is not None:
            text += "\n" + str(e.output)
        raise RuntimeError(text)


def download_packages(package_list, download_dir):
    """
    Download multiple packages through yum

    :param package_list: The packages to install
    :param download_dir: The directory to download the packages to
    :raises RuntimeError if any downloads fail
    """
    downloaded_packages = []
    for package in package_list:
        downloaded_packages.append(download_package(package, download_dir))
    return downloaded_packages


def remove_package(package_name):
    """
    Python api equivalent of `yum remove <package>`

    :param package_name: the package to remove
    :raises RuntimeError if remove fails
    """
    try:
        _ = subprocess.check_output(['yum', '-y', '-q', '--disablerepo=*', "remove", package_name],
                                    stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        text = "Couldn't delete " + package_name + " package. Encountered an error: " + str(e)
        if e.output is not None:
            text += "\n" + str(e.output)
        raise RuntimeError(text)


def remove_package_from(node, package_name):
    """
    Uninstall a yum package from the provided node

    :param node:  The node to uninstall from
    :param package_name:  The package to remove
    :raises: RuntimeError if remove failed
    """
    if node.get_location().is_local():
        remove_package(package_name)
        return

    result_code, result_string = node.perform_command_on_host("yum -y -q --disablerepo=* remove " + package_name)
    if result_code != 0:
        raise RuntimeError("Couldn't remove " + package_name + " from " + node.get_location().address + ": " +
                           result_string)
