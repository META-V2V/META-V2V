import glob
import json
import logging
import os
import random
import shutil
from typing import List, Dict, Tuple, Any
from config import APOLLO_ROOT, RECORDS_DIR, STREAM_LOGGING_LEVEL
import requests
import subprocess

BK_FILE_MAP = {
    'RadiusBroker': 'radius',
    'DelayBroker': 'delay',
    'NoiseBroker': 'noise',
    'IntermittentBroker': 'intermittent'
}

BK_HEAD_MAP = {
    'RadiusBroker': 'radius',
    'DelayBroker': 'delay',
    'NoiseBroker': 'noise',
    'IntermittentBroker': 'p'
}

def get_logger(name, filename=None, log_to_file=False) -> logging.Logger:
    """
    Gets logger from logging module
    [Todo] currently, the file recording is not implemented

    :param str name: the name of the logger
    :param str filename: filename of the log records
    :param bool log_to_file: flag to determine logging to file
    :returns: Logger object
    :rtype: Logger
    """
    logger = logging.getLogger(name)
    logger.propagate = False
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(STREAM_LOGGING_LEVEL)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(ch)
    return logger

def get_scenario_logger() -> logging.Logger:
    """
    Gets logger that always logs on the same line

    :returns: Logger object
    :rtype: Logger
    """
    logger = logging.getLogger('Scenario')
    logger.propagate = False
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.terminator = '\r'
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

def random_numeric_id(length:int=5) -> List[int]:
    """
    Generates a list of random integer ids, used for ApolloRunner's nid

    :param int length: expected length of the ID, default to 5
    :returns: list of integer ids
    :rtype: List[int]
    """
    return sorted(random.sample(range(100000, 999999), k=length))

def save_record_files_and_chromosome(timestamp: str, gen_name: str, ind_name: str,
                                    fol_name: str, ch: dict, 
                                    min_distances: Dict[Tuple[int, int], float],
                                    bk_mode: str, bk_param: Any) -> None:
    """
    Save the record file and the genetic representation

    :param str timestamp: timestamp of this runtime batch
    :param str gen_name: name of the generation
    :param str ind_name: name of the individual
    :param str fol_name: name of the follow-up
    :param dict ch: the genetic representation of the scenario script
    :param Dict[Tuple[int, int], float] min_distances: the min_distances of the scenario
    """
    dest = os.path.join(RECORDS_DIR, timestamp, gen_name, ind_name, fol_name)
    if not os.path.exists(dest):
        os.makedirs(dest)
    else:
        shutil.rmtree(dest)
        os.makedirs(dest)

    fileList = glob.glob(f'{APOLLO_ROOT}/records/*')
    for filePath in fileList:
        shutil.copy2(filePath, dest)

    sc_file = os.path.join(dest, "scenario.json")
    with open(sc_file, 'w') as fp:
        json.dump(ch, fp, indent=4)
    min_distances_file = os.path.join(dest, "min_distances.json")
    with open(min_distances_file, 'w') as fp:
        # Convert tuple keys to string format "i,j"
        min_distances_str_keys = {f"{k[0]},{k[1]}": v for k, v in min_distances.items()}
        json.dump(min_distances_str_keys, fp, indent=4)
    # save the mbk parameters
    bk_file = os.path.join(dest, "communication.json")
    if bk_mode == 'MessageBroker':
        bk_param = None              # parano sense for MessageBroker
    with open(bk_file, 'w') as fp:
        json.dump({'mode': bk_mode, 'param': bk_param}, fp, indent=4)

def send_push_pushover(message: str) -> requests.Response:
    """
    Send a push notification to the Pushover app

    :param str message: the message to send
    :returns: the response from the Pushover app
    :rtype: requests.Response
    """
    token = "as286xhbcqksaz7rj54r2ow9gsfxjw"
    user = "ukgks1x2syems2aekji1frbqqifkgx"
    url = "https://api.pushover.net/1/messages.json"
    data = {
        "token": token,
        "user": user,
        "message": message
    }
    return requests.post(url, data=data)

def kill_apollo_container(route_name: str):
    """
    [Warning] DANGEROUS UTILITY FUNCTION, currently not used
    Kill the Apollo container with the specified route name
    
    :param str route_name: the route name, like 'ROUTE_0', the function will add 'apollo_dev_' prefix automatically
    """
    try:
        container_name = f"apollo_dev_{route_name}"
        
        # get all running docker container information (include name)
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.ID}} {{.Names}}'], 
            capture_output=True, 
            text=True
        )
        
        # parse the container information
        containers = result.stdout.strip().split('\n')
        container_to_kill = None
        
        for container in containers:
            if container:  # make sure not empty line
                container_id, name = container.split(' ', 1)
                if name == container_name:
                    container_to_kill = container_id
                    break
        
        if container_to_kill:
            # Kill the matched container
            subprocess.run(['docker', 'kill', container_to_kill])
            print(f"Successfully killed Apollo container: {container_name}")
            print(f"Container ID: {container_to_kill}")
        else:
            print(f"No running Apollo container found with name: {container_name}")

    except subprocess.CalledProcessError as e:
        print(f"An error occurred while killing container: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
