import os
import sys
import requests
import subprocess
import posixpath


GET_PIP_SCRIPT_LOCATION = "https://bootstrap.pypa.io/"
GET_PIP_SCRIPT_NAME = 'get-pip.py'

PIP_COMMAND_LIST = [sys.executable, "-m", "pip"]


def download_get_pip_script(destination_dir):
    """
    Download the script that allows you install pip on a machine
    :param destination_dir:
    :return:
    """
    r = requests.get(posixpath.join(GET_PIP_SCRIPT_LOCATION, GET_PIP_SCRIPT_NAME))
    if not r.ok:
        r.raise_for_status()
    file_location = os.path.join(destination_dir, GET_PIP_SCRIPT_NAME)
    open(file_location, 'wb').write(r.content)
    return file_location


def _run_local_pip_command(args_list):
    command_list = list(PIP_COMMAND_LIST)
    command_list.extend(args_list)
    return subprocess.check_output(command_list, stderr=subprocess.STDOUT)


def download_package(package_name, target_dir=None):
    """
    Download the requested package using pip and put it in the target directory provided. If no directory is
    provided then it will be downloaded into the current working directory

    :param package_name: The package to download
    :param target_dir: The directory to download the package to
    :raises: RuntimeError if the package couldn't be downloaded
    """
    if target_dir is None:
        target_dir = os.getcwd()
    try:
        _run_local_pip_command(['download', '-d', target_dir, package_name])
    except subprocess.CalledProcessError as e:
        text = "Couldn't download " + package_name + ". Encountered an error: " + str(e)
        if e.output is not None:
            text += "\n" + str(e.output)
        raise RuntimeError(text)


def download_packages(package_list, target_dir=None):
    """
    Download the each package in the provided list using pip and put it in the target directory provided.
    If no directory is provided then it will be downloaded into the current working directory

    :param package_list:
    :param target_dir:
    :raises: RuntimeError if any of the packages failed to downloaded
    """
    for package in package_list:
        download_package(package, target_dir)


def is_package_installed(package_name):
    """
    Check whether package_name is installed on this node

    :param package_name: The package to check
    :return: True if the package is installed; False otherwise
    """
    try:
        _run_local_pip_command(['show', package_name])
        return True
    except subprocess.CalledProcessError as e:
        return False


def is_package_installed_on(node, package_name):
    """
    Check whether package_name is installed on the node provided

    :param node: A yu.network.RemoteNode object to check
    :param package_name: Package to check
    :return: True if the package is installed; False otherwise
    """
    if node.get_location().is_local():
        return is_package_installed(package_name)

    result_code, _, = node.perform_command_on_host("pip show " + package_name)
    if result_code == 0:
        return True
    return False


def install_package(package_name):
    """
    Installs package_name onto this node. Equivalent of `pip install <package_name>`

    :param package_name: The package to install
    :raises: RuntimeError if any of the packages failed to install
    """
    try:
        _run_local_pip_command(['install', package_name])
    except subprocess.CalledProcessError as e:
        text = "Couldn't install " + package_name + ". Encountered an error: " + str(e)
        if e.output is not None:
            text += "\n" + str(e.output)
        raise RuntimeError(text)


def install_packages(package_list):
    """
    Installs a list of packages onto this node.
    Equivalent of `pip install <package_1> <package_2> ... <package_N>`

    :param package_list:  The list of packages to install
    :raises: RuntimeError if any of the packages failed to install
    """
    try:
        command_list = ['install']
        command_list.extend(package_list)
        _run_local_pip_command(command_list)
    except subprocess.CalledProcessError as e:
        text = "Couldn't install the packages " + " ".join(package_list) + ". Encountered an error: " + str(e)
        if e.output is not None:
            text += "\n" + str(e.output)
        raise RuntimeError(text)


def install_package_on(node, package=None, wheel_file=None):
    """
    Installs a list of package or wheel onto the node provided
    Equivalent of `pip install package/wheel`
    Note: You must provide one of either a package or wheel_file

    :param node: The yu.network.RemoteNode to install on
    :param package:  The package to install (optional)
    :param wheel_file: The wheel to install (optional)
    :raises: RuntimeError if any the packages failed to install or if nether a package nor wheel_file was provided
    """
    package_arg = None
    if package is not None:
        package_arg = package
    else:
        if wheel_file is not None:
            package_arg = wheel_file

    if package_arg is None:
        raise RuntimeError("No package or wheel provided to install")

    if node.get_location().is_local():
        print("pip install'ing locally")
        install_package(package_arg)
        print("Success")
        return

    if wheel_file is not None:
        print("Copying wheel to " + node.get_location().address)
        node.copy_file_to(wheel_file)
        print("pip installing")
        result_code, result_string = node.perform_command_on_host("python -m pip install --no-index " +
                                                                  os.path.basename(wheel_file))
        if result_code != 0:
            print("Failed")
            raise RuntimeError("Couldn't install " + package_arg + " on " + node.get_location().address + ": " +
                               result_string)
    else:
        result_code, result_string = node.perform_command_on_host("python -m pip install --no-index " + package)
        if result_code != 0:
            print("Failed")
            raise RuntimeError("Couldn't install " + package + " on " + node.get_location().address + ": " +
                               result_string)
    print("Success")


def update_package(package_name):
    """
    Updates package_name on this node. Equivalent of `pip install -U <package_name>`

    :param package_name: The package to update
    :raises: RuntimeError if any of the packages failed to update
    """
    try:
        _run_local_pip_command(['install', "-U", package_name])
    except subprocess.CalledProcessError as e:
        text = "Couldn't update " + package_name + ". Encountered an error: " + str(e)
        if e.output is not None:
            text += "\n" + str(e.output)
        raise RuntimeError(text)


def uninstall_package(package_name):
    """
    Uninstall package_name from this node. Equivalent of `pip uninstall <package_name>`

    :param package_name: The package to uninstall
    :raises: RuntimeError if uninstalling failed
    """
    try:
        _run_local_pip_command(['uninstall', '--yes', package_name])
    except subprocess.CalledProcessError as e:
        text = "Couldn't install " + package_name + ". Encountered an error: " + str(e)
        if e.output is not None:
            text += "\n" + str(e.output)
        raise RuntimeError(text)


def uninstall_package_from(node, package_name):
    """
    Uninstall a pip package from the provided node

    :param node: The yu.network.RemoteNode to uninstall from
    :param package_name: The package to uninstall
    :raises: RuntimeError if uninstalling failed
    """
    if node.get_location().is_local():
        uninstall_package(package_name)
        return

    result_code, result_string = node.perform_command_on_host("pip uninstall --yes " + package_name)
    if result_code != 0:
        raise RuntimeError("Couldn't uninstall " + package_name + " from " + node.get_location().address + ": " +
                           result_string)


def show_package(package_name):
    """
    Get a summary of a package that is installed.
    Equivalent to `pip show <package_name>`

    :param package_name:  The package to get a sumary for
    :return: A dictionary withe following keys:
             Name, Version, Summary, Home-page, Author, Author-email, License,
             Location, Requires, Required-by
    """
    try:
        output = _run_local_pip_command(['show', package_name])
        sumary_list = output.strip().split("\n")
        summary_dict = {}
        for item in sumary_list:
            key = item[:item.index(':')].strip()
            value = item[item.index(':')+1:].strip()
            summary_dict[key] = value
        return summary_dict
    except subprocess.CalledProcessError as e:
        text = "Couldn't get summary for " + package_name + ". It may not be installed"
        if e.output is not None:
            text += "\n" + str(e.output)
        raise RuntimeError(text)
