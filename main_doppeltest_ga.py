import os
import csv
import json
import fcntl
from datetime import datetime
from functools import partial
import pandas as pd
from deap import algorithms, base, tools
from broker.factory import BrokerFactory
from apollo.container import ApolloContainer
from scenario import Scenario
from scenario.scenario_runner import ScenarioRunner
from hdmap.parser import MapParser
from genetic.crossover import cx_scenario
from genetic.mutation import mut_scenario
from config import (APOLLO_ROOT, HD_MAP, MAX_ADC_COUNT, RECORDS_DIR,
                    RUN_FOR_HOUR, POP_SIZE, BK_PARAM_MAP)
from utils import BK_FILE_MAP, BK_HEAD_MAP, get_max_container_number
from typing import List, Any, Tuple
from genetic import eval_scenario_doppeltest, min_distance
from copy import deepcopy

# [Warning] Please do not modify this file's name,
# coz we've used inspect.stack() to determine which entrance is calling
# Although it's not a good practice, we just do not want to use so many parameters in the functions

def eval_doppeltest(ind: Scenario, timestamp: str, param_list: List[Any], bk_type: str, mode: str) -> Tuple[float, int, int, int]:
    """
    Using the DoppelTest fitness function to evaluate the scenario

    :param Scenario ind: the scenario individual, ind.gid, ind.sid have been set, fid will be set in this function
    :param str timestamp: timestamp of this runtime batch
    :param List[Any] param_list: the list of parameters for the subclassed MessageBroker with imperfect perception
    :param str bk_type: the type of broker to be used
    :param str mode: the mode of the main script
    :return: dist[0], len(decisions) in source, conflict in source, unique_violations in source
    :rtype: float, int, int, int
    """

    # record the min_dist of source and follow-ups
    dist: List[float] = list()

    # source test case
    ind.fid = 0
    BrokerFactory().set_mode('MessageBroker')
    # return min(min_distances.values()), len(decisions), conflict, unique_violation, doppeltest fitness function values
    source_test_case_return: Tuple[float, int, int, int] = eval_scenario_doppeltest(ind, timestamp)
    dist.append(source_test_case_return[0])

    # set mode to the subclassed MessageBroker with imperfect perception
    BrokerFactory().set_mode(bk_type)
    # set the parameters for the subclassed MessageBroker with imperfect perception
    for index, param in enumerate(param_list):
        # note that has offset 1
        ind.fid = index + 1
        # set the parameters for the subclassed MessageBroker
        BrokerFactory().set_param(param)
        # calculate the min_distance of the follow-up test case
        follow_min_dist: float = min_distance(timestamp, ind)
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

    # return the doppeltest fitness function values
    return source_test_case_return

def main_doppeltest(bk_type: str, cxpb: float, mutpb: float):
    """
    Main function of the doppeltest genetic algorithm.
    
    This script use the DoppelTest fitness function of source test case, no follow-ups diff involved the evolution

    :param str bk_type: the type of broker to be used
    :param float cxpb: the crossover probability
    :param float mutpb: the mutation probability
    """

    mp = MapParser.get_instance(HD_MAP)
    bkf = BrokerFactory()
    # Initialize all apollo containers
    containers = []
    # lock file path
    lock_file_path = "/tmp/meta-v2v-container.lock"

    for _ in range(MAX_ADC_COUNT):
        # get the unique container number and start the instance
        with open(lock_file_path, 'a+') as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                container = ApolloContainer(APOLLO_ROOT, f'ROUTE_{get_max_container_number()+1}')
                containers.append(container)
                container.start_instance()
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
        # finish the subsequent non-critical steps outside the lock, shorten the lock holding time
        container.start_dreamview()
        print(f'Dreamview at http://{container.ip}:{container.port}')

    srunner = ScenarioRunner(containers)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    param_list = BK_PARAM_MAP.get(bk_type)

    toolbox = base.Toolbox()
    toolbox.register('mate', cx_scenario)
    toolbox.register('mutate', mut_scenario)
    toolbox.register('select', tools.selNSGA2)
    hof = tools.ParetoFront()
    # write the header of csv file
    if not os.path.exists(os.path.join(RECORDS_DIR, timestamp)):
        os.makedirs(os.path.join(RECORDS_DIR, timestamp))
    file_path = os.path.join(RECORDS_DIR, timestamp,
                             BK_FILE_MAP.get(bk_type) + '_' + 'doppeltest' + '.csv')
    with open(file_path, 'w') as f:
        writer = csv.writer(f)
        header = ['Generation', 'Individual']
        for i in range(len(param_list) + 1):
            header.extend([f'{BK_HEAD_MAP.get(bk_type)}_{i}', f'dist_{i}', f'diff_{i}'])
        header.append('max_diff')
        header.append('min_diff')
        writer.writerow(header)
    # write the hyperparams to a json file, in case of forget
    hyper_param_json = os.path.join(RECORDS_DIR, timestamp, 'hyper_param.json')
    with open(hyper_param_json, 'w') as f:
        json.dump({'cxpb': cxpb, 'mutpb': mutpb}, f)

    # start the genetic algorithm cycle
    start_time = datetime.now()
    
    # using doppeltest fitness function to evolution
    toolbox.register('evaluate', partial(eval_doppeltest, timestamp=timestamp, param_list=param_list, bk_type=bk_type, mode='doppeltest'))
    # initialize population
    population = [Scenario.get_conflict_one() for _ in range(POP_SIZE)]
    curr_gen = 0
    # initialize gid
    for index, c in enumerate(population):
        c.gid = curr_gen
        c.sid = index
    
    invalid_ind = [ind for ind in population if not ind.fitness.valid]
    fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
    for ind, fit in zip(invalid_ind, fitnesses):
        # the first direction is the min_dist of source test case
        # the second direction is len(decisions) of source test case
        # the third direction is conflict of source test case
        # the fourth direction is unique_violations of source test case
        ind.fitness.values = (fit[0], fit[1], fit[2], fit[3])
    # update the Pareto front
    hof.update(population)

    while True:
        curr_gen += 1
        offspring = algorithms.varOr(population, toolbox, POP_SIZE, cxpb, mutpb)

        # update gid and sid in offspring
        for index, c in enumerate(offspring):
            c.gid = curr_gen
            c.sid = index
        
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = (fit[0], fit[1], fit[2], fit[3])
        # update the Pareto front
        hof.update(offspring)

        # Select the next generation population
        population[:] = toolbox.select(population + offspring, POP_SIZE)

        # timer check
        tdelta = (datetime.now() - start_time).total_seconds()
        if tdelta / 3600 > RUN_FOR_HOUR:
            for ctn in containers:
                ctn.stop_instance()
            break

if __name__ == '__main__':

    bktype = input("Enter the broker type: RadiusBroker, LatencyBroker, NoiseBroker or IntermittenceBroker: ")
    if bktype not in BK_PARAM_MAP:
        raise ValueError(f"Invalid broker type: {bktype}")
    print("Note: The following sum of crossover and mutation probability should not exceed 1")
    cx_pb = float(input("Enter the crossover probability [0,1], baseline is 0.8: "))
    if cx_pb < 0 or cx_pb > 1:
        raise ValueError(f"Invalid crossover probability: {cx_pb}")
    mut_pb = float(input("Enter the mutation probability [0,1], baseline is 0.2: "))
    if mut_pb < 0 or mut_pb > 1:
        raise ValueError(f"Invalid mutation probability: {mut_pb}")
    if cx_pb + mut_pb > 1:
        raise ValueError(f"Invalid crossover and mutation probability: {cx_pb} + {mut_pb} > 1")
    main_doppeltest(bk_type=bktype, cxpb=cx_pb, mutpb=mut_pb)
