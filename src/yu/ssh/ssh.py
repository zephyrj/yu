import paramiko
import os
import ntpath
import stat
import pathlib
import socket


class NotConnectedException(Exception):
    pass


class RemoteCommandFailedException(Exception):
    pass


class TimedOutException(Exception):
    pass


class Session:
    def __init__(self, hostname):
        self.m_hostname = hostname
        self.m_sshClient = None

    def connect(self, p_username, p_password=None, ssh_key=None):
        host = str(self.m_hostname)
        port = 22

        self.m_sshClient = paramiko.SSHClient()
        self.m_sshClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if ssh_key is not None:
            self.m_sshClient.connect(host, port, username=p_username, key_filename=ssh_key)
        elif p_password is not None:
            self.m_sshClient.connect(host, port, username=p_username, password=p_password)
        else:
            raise RuntimeError("Must provide a key file or a password to connect")

        self.m_sshClient.get_transport().set_keepalive(30)

    def copy_file_to(self, local_file, destination_filename=None, destination_dir=None):
        if destination_dir is None:
            destination_dir = ""

        if destination_filename is None:
            destination_filename = ntpath.basename(local_file)

        sftp = None
        try:
            sftp = self.m_sshClient.open_sftp()
            remote_path = os.path.join(destination_dir, destination_filename)
            sftp.put(local_file, remote_path)
            sftp.chmod(remote_path, os.stat(local_file).st_mode)
        except paramiko.SSHException as e:
            raise RuntimeError("Failed to copy " + local_file + " to " + str(self.m_hostname) + ":\n" + repr(e))
        finally:
            if sftp is not None:
                sftp.close()

    def copy_dir_to(self, local_dir, destination_dir=None, sftp_client=None):
        if not os.path.exists(local_dir):
            raise RuntimeError(local_dir + " does not exist")
        if not os.path.isdir(local_dir):
            raise RuntimeError(local_dir + " is not a directory")

        if destination_dir is None:
            destination_dir = ""

        sftp = sftp_client
        try:
            if sftp is None:
                sftp = self.m_sshClient.open_sftp()

            remote_copy_dir = os.path.join(destination_dir, os.path.basename(local_dir))
            try:
                stat_info = sftp.lstat(remote_copy_dir)
                if not stat.S_ISDIR(stat_info.st_mode):
                    raise RuntimeError("The path " + remote_copy_dir + " already exists on " + str(self.m_hostname) +
                                       " and is not a directory")
            except IOError:
                sftp.mkdir(remote_copy_dir)

            for root, dirs, files in os.walk(local_dir):
                for f in files:
                    local_path = os.path.join(root, f)
                    remote_path = os.path.join(remote_copy_dir, os.path.basename(f))
                    sftp.put(local_path, remote_path)
                    sftp.chmod(remote_path, os.stat(local_path).st_mode)
                for d in dirs:
                    self.copy_dir_to(os.path.join(root, d),
                                     destination_dir=remote_copy_dir,
                                     sftp_client=sftp)
                break
        except paramiko.SSHException as e:
            raise RuntimeError(
                "Failed to copy directory " + local_dir + " to " + str(self.m_hostname) + ":\n" + repr(e))
        finally:
            if sftp is not None and sftp_client is None:
                # If we opened the sftp object then we should close it
                sftp.close()

    def copy_file_from(self, remote_file, destination_filename=None, destination_dir=None):
        if destination_dir is None:
            destination_dir = ""

        if destination_filename is None:
            destination_filename = ntpath.basename(remote_file)

        sftp = None
        try:
            sftp = self.m_sshClient.open_sftp()
            sftp.get(remote_file, os.path.join(destination_dir, destination_filename))
            stat_info = sftp.stat(remote_file)
            os.chmod(os.path.join(destination_dir, destination_filename), stat_info.st_mode)
        except paramiko.SSHException as e:
            raise RuntimeError("Failed to copy " + remote_file + " from " + str(self.m_hostname) + ":\n" + repr(e))
        finally:
            if sftp is not None:
                sftp.close()

    def copy_dir_from(self, remote_dir, destination_dir=None, sftp_client=None):
        if destination_dir is None:
            destination_dir = os.getcwd()

        sftp = sftp_client
        try:
            if sftp_client is None:
                sftp = self.m_sshClient.open_sftp()

            files = sftp.listdir(remote_dir)

            local_copy_dir = os.path.join(destination_dir, os.path.basename(remote_dir))
            if not os.path.exists(local_copy_dir):
                os.mkdir(local_copy_dir)
            else:
                if not os.path.isdir(local_copy_dir):
                    raise RuntimeError("The local path " + local_copy_dir + " already exists but is not a directory")

            for f in files:
                file_path = os.path.join(remote_dir, f)
                stat_info = self.stat(file_path, follow_symlinks=False, sftp_session=sftp)
                if stat.S_ISDIR(stat_info.st_mode):
                    self.copy_dir_from(file_path, local_copy_dir, sftp)

                elif stat.S_ISREG(stat_info.st_mode):
                    sftp.get(file_path, os.path.join(local_copy_dir, f))
                    stat_info = sftp.stat(file_path)
                    os.chmod(os.path.join(local_copy_dir, f), stat_info.st_mode)

                elif stat.S_ISLNK(stat_info.st_mode):
                    link_target = os.path.join(remote_dir, f)
                    link_target_info = self.stat(link_target, follow_symlinks=True, sftp_session=sftp)

                    if stat.S_ISREG(link_target_info.st_mode):
                        sftp.get(file_path, local_copy_dir)

                    if stat.S_ISDIR(link_target_info.st_mode):
                        root = pathlib.Path(remote_dir)
                        link = pathlib.Path(link_target)
                        if root in link.parents:
                            # This might result in a loop - skip it
                            continue
                        sftp.get(file_path, local_copy_dir)
        except IOError as e:
            raise RuntimeError("The directory " + remote_dir + " does not exist on " + str(self.m_hostname))
        except paramiko.SSHException as e:
            raise RuntimeError("Failed to copy directory " + remote_dir + " from " + str(self.m_hostname) + ":\n" + repr(e))
        finally:
            if sftp is not None and sftp_client is None:
                # If we opened the sftp object then we should close it
                sftp.close()

    def delete_file(self, remote_path, error_if_not_exists=True):
        sftp = None
        try:
            sftp = self.m_sshClient.open_sftp()
            sftp.remove(remote_path)
        except IOError as e:
            if error_if_not_exists:
                raise e
            pass
        except paramiko.SSHException as e:
            raise RuntimeError("Failed to delete file " + remote_path + " from " + str(self.m_hostname) + ":\n"
                               + repr(e))
        finally:
            sftp.close()

    def delete_dir(self, remote_directory, contents_only=False):
        # TODO replace the rm -rf with a sftp solution for cross-platformness
        result_code, result_string = self.exec_command("rm -rf " + remote_directory)
        if result_code is not 0:
            raise RuntimeError("Failed to delete " + remote_directory + ": " + result_string)

        if contents_only is True:
            self.mkdir(remote_directory)

    def mkdir(self, remote_directory):
        sftp = None
        try:
            sftp = self.m_sshClient.open_sftp()
            sftp.mkdir(remote_directory)
        except IOError as e:
            raise e
        except paramiko.SSHException as e:
            raise RuntimeError("Failed to create directory " + remote_directory + " on " + str(self.m_hostname) + ":\n"
                               + repr(e))
        finally:
            sftp.close()

    def stat(self, remote_path, follow_symlinks=True, sftp_session=None):
        sftp = sftp_session

        try:
            if sftp is None:
                sftp = self.m_sshClient.open_sftp()
            if follow_symlinks is True:
                return sftp.stat(remote_path)
            else:
                return sftp.lstat(remote_path)
        finally:
            if sftp is not None and sftp_session is None:
                sftp.close()

    def get_session(self):
        return self.m_sshClient

    def close(self):
        self.m_sshClient.close()

    def invoke_shell(self):
        return self.m_sshClient.invoke_shell()

    def exec_command(self, command, timeout=None, shell=False):
        try:
            stdin, stdout, stderr = self.m_sshClient.exec_command(command, -1, timeout, get_pty=shell)

            result_string = stdout.read()
            result_code = stdout.channel.recv_exit_status()
            return result_code, result_string
        except socket.timeout as e:
            raise TimedOutException("Execution of " + command + " on " + str(self.m_hostname) + " timed out (" +
                                    timeout + " seconds)")
        except paramiko.SSHException as e:
            try:
                transport = self.m_sshClient.get_transport()
                transport.send_ignore()
                raise RemoteCommandFailedException("Failed to execute " + command + " on " + str(self.m_hostname)
                                                   + ":" + str(e))
            except EOFError:
                raise NotConnectedException("SSH connection to " + self.m_hostname + " was lost")
