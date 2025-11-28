import os
from config import APOLLO_ROOT
import subprocess
import shutil
from apollo.container import ApolloContainer

def execute_command_in_docker(container_name: str, command: str):
    """
    Execute a command in the distinct docker container

    :param str container_name: the name of the docker container
    :param str command: the command to execute in the docker container
    """
    try:
        # build the docker exec command, -d option using detached mode
        docker_command = ['docker', 'exec', '-d', container_name, 'bash', '-c', command]
        
        # execute the command and get the output
        result = subprocess.run(docker_command, capture_output=True, text=True, check=True)
        
        # print the execution result
        if result.returncode == 0:
            print(f"Command executed successfully. Using detached mode, no output will be printed.")
        else:
            print(f"Command executed failed: {result.stderr}")
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e.stderr}")

def main():

    # source record file path
    print("Please input the record file path:")
    file_path = input("> ").strip().strip("'").strip('"')

    # note that we need to copy the record file to the Apollo root directory for the docker container to replay
    dest_path = os.path.join(APOLLO_ROOT, f'replay.00000')
    # make sure the source file exists
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Source file not found: {file_path}")
    # copy the record file to the Apollo root directory
    shutil.copy(file_path, dest_path)

    # initialize the container, create a new container with the TEST route name
    container = ApolloContainer(APOLLO_ROOT, 'ROUTE_TEST')
    container.start_instance(restart=True)
    container.start_dreamview()
    print(f'Dreamview at http://{container.ip}:{container.port}')

    # execute the replay command in the docker container by CyberRT
    command = (f"source ./cyber/setup.bash; cyber_recorder play -f ./replay.00000 -a -l")
    execute_command_in_docker(container.container_name, command)
    while True:
        # wait for the user to stop the container
        stop_signal = input("Enter 'q' to stop the container...")
        if stop_signal.strip().lower() == 'q':
            container.stop_instance()
            print("Container stopped.")
            break
        else:
            print("Invalid input, container will not be stopped.")

if __name__ == '__main__':

    main()
