""" few docker support functions"""

import subprocess
import logging
#WIP

logger = logging.getLogger("utils")

def execute_docker_command(command_list):
    """Execute a docker command"""
    result = subprocess.run(command_list, shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    if result.stderr:
        if "[ERROR]" not in result.stderr.decode("utf-8"):
            logger.error("While performing %s , detected error in output: \n%s", " ".join(command_list), result.stdout.decode('utf-8'))
            raise Exception("Docker command failed")

    if result.stdout:
        logger.info("Copying file into docker: %s", result.stdout.decode("utf-8"))
        return result.stdout.decode('utf-8')
    return None


def copy_file_to_container(path, container_id):
    """Write a file to the container"""
    command_line = ["docker", "cp", path, container_id + ":" + path]
    execute_docker_command(command_list=command_line)


def copy_file_from_container(path, container_id):
    """Write a file to the container"""
    command_line = ["docker", "cp", container_id + ":" + path, path]
    execute_docker_command(command_list=command_line)


def get_list_of_files(container_id, folder, mask="*"):
    """Get a list of files in the docker"""
    command_line = ["docker", "exec", "-t", container_id, "ls", "-t1", folder]
    files = execute_docker_command(command_list=command_line)
    list_files = files.replace("\r\n","\n").split("\n")
    # remove empty lines
    return [filename for filename in list_files if filename]


if __name__ == "__main__":
    my_files = get_list_of_files("021bdbbfcabf", "/tmp")
    print(my_files)
    my_files = get_list_of_files("021bdbbfcabf", "/tmp/sqs")
    print(my_files)
