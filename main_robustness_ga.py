import os
import csv
from datetime import datetime
from functools import partial
from deap import algorithms, base, tools
from broker.factory import BrokerFactory
from apollo.container import ApolloContainer
from scenario import Scenario
from scenario.scenario_runner import ScenarioRunner
from hdmap.parser import MapParser
from genetic.crossover import cx_scenario
from genetic.mutation import mut_scenario
from genetic.evaluate import eval_stage_2
from config import (APOLLO_ROOT, HD_MAP, MAX_ADC_COUNT, RECORDS_DIR,
                    RUN_FOR_HOUR, POP_SIZE, BK_PARAM_MAP)
from utils import BK_FILE_MAP, BK_HEAD_MAP

# [Warning] Please do not modify this file's name,
# coz we've used inspect.stack() to determine which entrance is calling
# Although it's not a good practice, we just do not want to use so many parameters in the functions

def main_robustness(bk_type: str, cxpb: float, mutpb: float):
    """
    Main function of the robustness genetic algorithm.
    The MRT-GA should use one-stage evolution coz the optimization need of min(dist[1:]) generated in follow-ups

    This script minimize the minimum min_dist of follow-ups, and minimize the minimum min_diff of follow-ups
    (negative direction max). Robustness requirements state that the follow-ups' decline should be bounded,
    otherwise, indicate the robustness violation, multi-ADS based perception-to-planning is not robust enough.

    :param str bk_type: the type of broker to be used
    :param float cxpb: the crossover probability
    :param float mutpb: the mutation probability
    """
    mp = MapParser.get_instance(HD_MAP)
    bkf = BrokerFactory()
    containers = [
        ApolloContainer(APOLLO_ROOT, f'ROUTE_{x}') for x in range(MAX_ADC_COUNT)]
    # Initialize all apollo containers
    for ctn in containers:
        ctn.start_instance()
        ctn.start_dreamview()
        print(f'Dreamview at http://{ctn.ip}:{ctn.port}')
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
                             BK_FILE_MAP.get(bk_type) + '_' + 'robustness' + '.csv')
    with open(file_path, 'w') as f:
        writer = csv.writer(f)
        header = ['Generation', 'Individual']
        for i in range(len(param_list) + 1):
            header.extend([f'{BK_HEAD_MAP.get(bk_type)}_{i}', f'dist_{i}', f'diff_{i}'])
        header.append('max_diff')
        header.append('min_diff')
        writer.writerow(header)

    # start the genetic algorithm cycle
    start_time = datetime.now()

    # only stage 2
    toolbox.register('evaluate', partial(eval_stage_2, timestamp=timestamp, param_list=param_list, bk_type=bk_type, mode='robustness'))
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
        # direction 1: minimize min(dist[1:])
        # direction 2: minimize min(diff[1:]), negative direction max
        ind.fitness.values = (fit[1], fit[3])
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
            # direction 1: minimize min(dist[1:])
            # direction 2: minimize min(diff[1:]), negative direction max
            ind.fitness.values = (fit[1], fit[3])
        # update the Pareto front
        hof.update(offspring)

        # Select the next generation population
        population[:] = toolbox.select(population + offspring, POP_SIZE)

        # timer check
        tdelta = (datetime.now() - start_time).total_seconds()
        if tdelta / 3600 > RUN_FOR_HOUR:
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
    main_robustness(bk_type=bktype, cxpb=cx_pb, mutpb=mut_pb)
