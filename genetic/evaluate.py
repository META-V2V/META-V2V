import os
import pandas as pd
from copy import deepcopy
from typing import List, Any, Tuple
from scenario import Scenario
from broker.factory import BrokerFactory
from config import RECORDS_DIR
from genetic import min_distance
from utils import BK_FILE_MAP

def eval_stage_1(ind: Scenario, timestamp: str, param_list: List[Any], bk_type: str, mode: str) -> float:
    """
    In the first stage, we only run the source scenario

    :param Scenario ind: the scenario chromosome, ind.gid and ind.sid have been set, fid will be set in this function
    :param str timestamp: timestamp of this runtime batch
    :param List[Any] param_list: the list of parameters for the subtype-Broker with imperfect perception
    :param str bk_type: the type of broker to be used
    :param str mode: the mode of the main script
    :return: the min_distance of source scenario
    :rtype: float
    """
    # set mode to MessageBroker
    BrokerFactory().set_mode('MessageBroker')
    # set source scenario fid to 0
    ind.fid = 0
    # calculate the min_distance of the source test case
    ori_min_dist: float = min_distance(timestamp, ind)
    # write the result to csv file
    result = list()
    result.append(f'Generation:{ind.gid}')
    result.append(f'Individual:{ind.sid}')
    if bk_type == 'RadiusBroker':
        result.append(float('inf'))
    else:
        result.append(0)         # param[0]
    result.append(ori_min_dist)  # dist[0]
    result.append(0)             # diff[0], not used
    for param in param_list:
        result.append(param)     # param[1:]
        result.append('')        # dist[1:]
        result.append('')        # diff[1:]
    result.append('')            # max_diff
    result.append('')            # min_diff
    df = pd.DataFrame([result])
    file_path = os.path.join(RECORDS_DIR, timestamp,
                             BK_FILE_MAP.get(bk_type) + '_' + mode + '.csv')
    df.to_csv(file_path, mode='a', index=False, header=False)

    return ori_min_dist

def eval_stage_2(ind: Scenario, timestamp: str, param_list: List[Any], bk_type: str, mode: str) -> Tuple[float, float, float, float]:
    """
    In the second stage, we run the source scenario and the corresponding follow-ups

    :param Scenario ind: the scenario individual, ind.gid, ind.sid have been set, fid will be set in this function
    :param str timestamp: timestamp of this runtime batch
    :param List[Any] param_list: the list of parameters for the subclasses of MessageBroker with imperfect perception
    :param str bk_type: the type of broker to be used
    :param str mode: the mode of the main script
    :return: dist[0], min(dist[1:]), max_diff, min_diff
    :rtype: float, float, float, float
    """
    # record the min_dist of source and follow-ups
    dist: List[float] = list()
    # set source scenario fid to 0
    ind.fid = 0
    # set mode to MessageBroker
    BrokerFactory().set_mode('MessageBroker')
    # calculate the min_distance of the source test case
    ori_min_dist: float = min_distance(timestamp, ind)
    dist.append(ori_min_dist)

    # set mode to the subclassed MessageBroker with imperfect perception
    BrokerFactory().set_mode(bk_type)
    # set the parameters for the subclassed MessageBroker
    for index, param in enumerate(param_list):
        # note that has offset 1
        ind.fid = index + 1
        # set the parameters for the subclassed MessageBroker
        BrokerFactory().set_param(param)
        # calculate the min_distance of the follow-up test case
        follow_min_dist: float = min_distance(timestamp, ind)
        # save the min_dist of the follow-up runtime
        dist.append(follow_min_dist)

    # write the result to csv file
    result = list()
    result.append(f'Generation:{ind.gid}')
    result.append(f'Individual:{ind.sid}')
    param_list_copy = deepcopy(param_list)
    # list alignment
    if bk_type == 'RadiusBroker':
        param_list_copy.insert(0, float('inf'))
    else:
        param_list_copy.insert(0, 0)
    diffs = [round((d-dist[0]), 2) for d in dist]
    # get the maximum difference between the follow-ups and the source
    max_diff = round(max(diffs[1:]), 2)       # exclude the diff[0]
    min_diff = round(min(diffs[1:]), 2)       # exclude the diff[0]
    for pr, d in zip(param_list_copy, dist):
        result.append(pr)                     # param[0:]
        result.append(d)                      # dist[0:]
        result.append(round((d-dist[0]),2))   # diff[0:]
    result.append(max_diff)                   # max_diff
    result.append(min_diff)                   # min_diff
    df = pd.DataFrame([result])
    file_path = os.path.join(RECORDS_DIR, timestamp,
                             BK_FILE_MAP.get(bk_type) + '_' + mode + '.csv')
    df.to_csv(file_path, mode='a', index=False, header=False)

    return dist[0], min(dist[1:]), max_diff, min_diff
