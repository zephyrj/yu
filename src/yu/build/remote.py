import os

from yu.network.RemoteNode import RemoteNode


class GitException(Exception):
    pass


class CMakeException(Exception):
    pass


class MakeException(Exception):
    pass


class BuildNode(RemoteNode):
    def __init__(self, hostname):
        super(BuildNode, self).__init__(hostname)

    def git_clone(self, repo_address, checkout_location="/tmp"):
        """
        Clone the git repo provided onto this node into the checkout location

        :param repo_address: the git repo to clone
        :param checkout_location: the directory to perform the clone command in
        :return: the remote path that the git repo was checked out into
        :raises: IOError if the checkout_location provided does not exist
        :raises: GitException if the clone command failed
        """
        if not self.is_dir(checkout_location):
            raise IOError("Cannot perform git clone as the checkout directory (" + checkout_location +
                          ") does not exist")

        git_clone_command = "cd " + checkout_location + "; "
        git_clone_command += "git clone --recurse-submodules " + repo_address

        result_code, result_string = self.command(git_clone_command)
        if result_code != 0:
            raise GitException("Failed to clone " + repo_address + ": " + result_string)

        project_name = repo_address.rsplit('/', 1)[-1].rsplit('.', 1)[0]
        return os.path.join(checkout_location, project_name)

    def run_cmake(self, remote_directory, arguments_list):
        """
        Run cmake in a directory on the node

        :param remote_directory: the directory to run the cmake command in
        :param arguments_list: a list containing the arguments which should be passed to the cmake command
        :raises: IOError if the remote_directory provided does not exist
        :raises: CMakeException if the cmake command fails
        """
        if not self.is_dir(remote_directory):
            raise IOError("Cannot perform cmake command as the remote directory (" + remote_directory +
                          ") does not exist")

        cmake_command = "cd " + remote_directory + "; "
        cmake_command += "cmake "
        for arg in arguments_list:
            cmake_command += str(arg) + " "

        result_code, result_string = self.command(cmake_command)
        if result_code != 0:
            raise CMakeException("cmake command failed with code " + result_code + ": " + result_string)

    def run_make(self, remote_directory, arguments_list):
        """
        Run make with in the remote directory with the arguments provided

        :param remote_directory: the remote directory to run the make command in
        :param arguments_list: the arguments to pass to the make command.
                               Each item in the list will be separated by a space.
        :raises: IOError if the remote_directory provided does not exist
        :raises: MakeException if the make command fails
        """
        if not self.is_dir(remote_directory):
            raise IOError("Cannot perform make command as the remote directory (" + remote_directory +
                          ") does not exist")

        make_command = "cd " + remote_directory + "; "
        make_command += "make "
        for arg in arguments_list:
            make_command += str(arg) + " "

        result_code, result_string = self.command(make_command)
        if result_code != 0:
            raise MakeException("make command failed with code " + result_code + ": " + result_string)
