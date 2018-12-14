import os
import errno
import stat
import socket

import yu.ssh.ssh as ssh
from yu.network.Location import Location


class RemoteNode(object):
    def __init__(self, ip_address):
        self.location = Location(ip_address)
        self.m_connected = False
        self.m_connected_as_root = False
        self.m_sshSession = ssh.Session(self.location.address)
        self.connected_username = None
        self.password = None
        self.ssh_key = None
        self.configured_hostname = None
        self.connectivity_status = None

    def set_ssh_key(self, ssh_key_path):
        if not os.path.isfile(ssh_key_path):
            raise IOError(ssh_key_path + " is not a valid key")
        self.ssh_key = ssh_key_path

    def connect(self, username, password=None):
        if self.ssh_key is None and password is None:
                raise RuntimeError("No authentication provided")

        if self.ssh_key:
            if not os.path.isfile(self.ssh_key):
                raise IOError(self.ssh_key + " is not a valid key")
            self.m_sshSession.connect(username, ssh_key=self.ssh_key)
        else:
            pwd = password
            if password is None:
                pwd = self.password
            self.m_sshSession.connect(username, pwd)

        self.m_connected = True
        self.connected_username = username
        if username == "root":
            self.m_connected_as_root = True

    def reconnect(self, username=None, password=None):
        self.m_sshSession.close()
        if username is None:
            if self.connected_username is not None:
                username = str(self.connected_username)
                self.connected_username = None
            else:
                raise RuntimeError("No username has been provided for the reconnect")
        self.connect(username, password)

    def command(self, command, timeout=None, shell=False):
        """
        Performs a command on this node

        :param command: the command, as a string, to perform on the remote node
        :param timeout: the maximum amount of time to allow the command to run
        :param shell: whether or not to execute the command in a shell
                      If your command needs to use shell operations like "~" for home dir or you want
                      to use pipes (|) and redirects (< or >) then you need to set this to True

        :return: a tuple of result code and result string
        :raises: socket.timeout if the command exceeds the provided timeout
        """
        if not self.m_connected:
            return 1, "Node session to " + self.location.address + "not connected"

        try:
            return self.m_sshSession.exec_command(command, timeout=timeout, shell=shell)

        except paramiko as e:
            self.m_connected = False
            # Have one go at reconnecting
            try:
                self.reconnect()
                return self.m_sshSession.exec_command(command, timeout=timeout, shell=shell)
            except socket.timeout as e:
                raise e
            except:
                return 1, "Node session to " + self.location.address + " not connected (attempted one retry)"

    def copy_file_to(self, path_to_file_to_copy, destination_filename=None, destination_dir=None):
        """
        Copy a file to this node from the local node
        You can optionally choose a new filename for the file and what directory the file will be copied to
        The file will be copied to the home directory of the connection (root by default) and use the filename
        of the original file

        :param path_to_file_to_copy:  The file to copy
        :param destination_filename:  The name to give the file on the remote node (Optional)
                                      Will default to the original filename provided by path_to_file_to_copy
        :param destination_dir:       The destination on the remote node to copy to (Optional)
                                      Will default the home dir of the user if omitted
        :raises RuntimeError if the copy fails
        """
        if not self.m_connected:
            raise RuntimeError("Node session to " + self.location.address + "not connected")

        try:
            self.m_sshSession.copy_file_to(path_to_file_to_copy, destination_filename, destination_dir)
        except RuntimeError as e:
            self.m_connected = False
            # Have one go at reconnecting
            self.reconnect()
            self.m_sshSession.copy_file_to(path_to_file_to_copy, destination_filename, destination_dir)

    def copy_dir_to(self, local_dir_to_copy, destination_dir=None):
        """
        Copy a directory to this RTDB node from the local node
        You can optionally choose the base directory you want to copy the directory to.
        e.g. when copying the directory "lab_results" and providing destination_dir="/home/ignaz" the directory
             will be created as /home/ignaz/lab_results on the remote node
        If no destination directory is provided then the directory will be copied to the home directory
        of the user of the connection (root by default)

        :param local_dir_to_copy: the path to the directory you want to copy
        :param destination_dir: the destination root on the remote node that you want to copy the directory to
        :raises RuntimeError if the copy fails
        """
        if not self.m_connected:
            raise RuntimeError("Node session to " + self.location.address + "not connected")

        try:
            self.m_sshSession.copy_dir_to(local_dir_to_copy, destination_dir)
        except RuntimeError as e:
            self.m_connected = False
            # Have one go at reconnecting
            self.reconnect()
            self.m_sshSession.copy_dir_to(local_dir_to_copy, destination_dir)

    def copy_file_from(self, path_to_file_on_remote, destination_filename=None, destination_dir=None):
        """
        Copy a file from this RTDB node to the local node
        You can optionally choose a new filename for the copied file and what directory the file will be copied to
        The file will be copied to the current working directory and use the filename of the original file by default

        :param path_to_file_on_remote: The file on the remote node to copy
        :param destination_filename:   The name to give the copied file
        :param destination_dir:        The destination to copy the file to locally
        :raises RuntimeError if the copy fails
        """
        if not self.m_connected:
            raise RuntimeError("Node session to " + self.location.address + "not connected")

        try:
            self.m_sshSession.copy_file_from(path_to_file_on_remote, destination_filename, destination_dir)
        except RuntimeError as e:
            self.m_connected = False
            # Have one go at reconnecting
            self.reconnect()
            self.m_sshSession.copy_file_from(path_to_file_on_remote, destination_filename, destination_dir)

    def copy_dir_from(self, path_to_dir_on_remote, destination_dir=None):
        """
        Copy a directory from this RTDB node to the local node
        You can optionally choose a new directory name for the copied dir
        The directory will be copied to the current working directory with the same directory name as on the remote
        by default

        :param path_to_dir_on_remote:  The dir on the remote node to copy
        :param destination_dir:        The destination to copy the directory to
        :raises RuntimeError if the copy fails
        """
        if not self.m_connected:
            raise RuntimeError("Node session to " + self.location.address + "not connected")

        try:
            self.m_sshSession.copy_dir_from(path_to_dir_on_remote, destination_dir)
        except RuntimeError as e:
            self.m_connected = False
            # Have one go at reconnecting
            self.reconnect()
            self.m_sshSession.copy_dir_from(path_to_dir_on_remote, destination_dir)

    def delete_file(self, remote_path, error_if_not_exists=True):
        """
        Delete the provided file from this node

        :param remote_path: The path to the file to delete
        :param error_if_not_exists: when set to True; if the file doesn't exist before this operation then an IOError
                                    will be raised.
                                    When set to False the file not existing will be ignored and will be considered a
                                    success case.
                                    Optional: Default is True
        :raises RuntimeError is the delete operation failed
        :raises IOError if the file did not exist before the delete and error_if_not_exists is True
        """
        if not self.m_connected:
            raise RuntimeError("Node session to " + self.location.address + "not connected")

        try:
            self.m_sshSession.delete_file(remote_path, error_if_not_exists)
        except RuntimeError as e:
            self.m_connected = False
            # Have one go at reconnecting
            self.reconnect()
            self.m_sshSession.delete_file(remote_path)

    def delete_dir(self, remote_directory, contents_only=False):
        """
        Delete the provided directory from this node.
        Note: if the directory does not exist then this function will consider this a success case

        :param remote_directory: The directory to remove
        :param contents_only: if this is set to True then the provided directory will not be deleted itself;
                              it's contents will be deleted but the directory itself will remain after the operation
                              i.e. delete_dir("/opt/sdl/journal", contents_only=True)
                                   would delete everything in /opt/sdl/journal but the directory would still exist
                              (optional) default = False

        :raises RuntimeError is the delete operation failed
        """
        if not self.m_connected:
            raise RuntimeError("Node session to " + self.location.address + "not connected")

        try:
            self.m_sshSession.delete_dir(remote_directory, contents_only=contents_only)
        except RuntimeError as e:
            self.m_connected = False
            # Have one go at reconnecting
            self.reconnect()
            try:
                self.m_sshSession.delete_dir(remote_directory, contents_only=contents_only)
            except IOError as e:
                if e.errno == errno.ENOENT:
                    return
                raise RuntimeError(
                    "The delete of " + remote_directory + " on " + self.location.address + " failed: " + str(e))

    def mkdir(self, new_dir_path):
        """
        Create the provided directory on the remote node.
        Note: The directory must be a leaf directory. i.e. if you provide /not_a_path/new_dir and "not_a_path" doesn't
        already exist then this command will fail with an IOError

        :param new_dir_path: the new directory to create
        :raises: RuntimeError if the creation fails
        :raises: IOError if the directory to be created would not be a leaf directory
        """
        if not self.m_connected:
            raise RuntimeError("Node session to " + self.location.address + "not connected")

        try:
            base_dir, dir_name = os.path.split(new_dir_path)
            if not self.is_dir(base_dir):
                raise IOError("Cannot create " + new_dir_path + " on " + self.location.address + ": It is not a "
                                                                                                  "leaf directory")
            self.m_sshSession.mkdir(new_dir_path)
        except RuntimeError as e:
            self.m_connected = False
            # Have one go at reconnecting
            self.reconnect()
            try:
                self.m_sshSession.mkdir(new_dir_path)
            except Exception as e:
                raise RuntimeError(
                    "The creation of " + new_dir_path + " on " + self.location.address + " failed: " + str(e))

    def exists(self, remote_path, follow_symlinks=True):
        """
        Check if the remote_path exists on this node.

        :param remote_path: the remote path to check for existence
        :param follow_symlinks: behaviour to take if remote path is a symlink
        :return: True if remote_path exists; False otherwise
        """
        if not self.m_connected:
            raise RuntimeError("Node session to " + self.location.address + "not connected")

        try:
            self.m_sshSession.stat(remote_path, follow_symlinks)
            return True
        except IOError:
            return False

    def is_file(self, remote_path, follow_symlinks=True):
        """
        Check if the remote_path exists and is a file on this node.

        :param remote_path: the remote path to check
        :param follow_symlinks: behaviour to take if remote path is a symlink
        :return: True if remote_path exists and is a file; False otherwise
        """
        if not self.m_connected:
            raise RuntimeError("Node session to " + self.location.address + "not connected")

        try:
            stat_info = self.m_sshSession.stat(remote_path, follow_symlinks)
            return stat.S_ISREG(stat_info.st_mode)
        except IOError:
            return False

    def is_dir(self, remote_path, follow_symlinks=True):
        """
        Check if the remote_path exists and is a directory on this node.

        :param remote_path: the remote path to check
        :param follow_symlinks: behaviour to take if remote path is a symlink
        :return: True if remote_path exists and is a directory; False otherwise
        """
        if not self.m_connected:
            raise RuntimeError("Node session to " + self.location.address + "not connected")

        try:
            stat_info = self.m_sshSession.stat(remote_path, follow_symlinks)
            return stat.S_ISDIR(stat_info.st_mode)
        except IOError:
            return False

    def extract_tar(self, path_to_tar):
        """
        Extract a tar.gz file on this node

        :param path_to_tar: the remote path of the file to extract
        :raises: RuntimeError if the extract fails
        """
        directory, filename = os.path.split(path_to_tar)
        self.perform_command_on_host("cd " + directory + "; tar -xvzf " + filename)

    def is_connected_as_root(self):
        return self.m_connected_as_root

    def close(self):
        self.m_sshSession.close()

    def get_connectivity_status(self):
        return self.connectivity_status

    def get_location(self):
        return self.location

    def get_host_to_connect_to(self):
        return self.location.address

    def get_configured_hostname(self):
        if self.configured_hostname:
            return self.configured_hostname

        cat_command = 'cat /proc/sys/kernel/hostname'
        result_code, result_string = self.perform_command_on_host(cat_command)
        if result_code is not 0:
            # TODO raise an exception
            return None

        self.configured_hostname = result_string.strip()
        return self.configured_hostname
