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
from genetic.evaluate import eval_stage_1, eval_stage_2
from utils.compress import compress_record_files
from config import (APOLLO_ROOT, HD_MAP, MAX_ADC_COUNT, RECORDS_DIR, 
                    RUN_FOR_HOUR, POP_SIZE, STAGE1, BK_PARAM_MAP)
from utils import BK_FILE_MAP, BK_HEAD_MAP

# [Warning] Please do not modify this file's name,
# coz we've used inspect.stack() to determine which entrance is calling
# Although it's not a good practice, we just do not want to use so many parameters in the functions

def main_soundness(bk_type: str, cxpb: float, mutpb: float):
    """
    Main function of the soundness genetic algorithm.
    Currently, we use two-stage evolution to find the differential behaviors
    for the subtype-Broker with imperfect perception.
    
    In the first stage, we only run the source test case, coz we want the source 
    one reach unsafe state as soon as possible.
    We then implement the second stage, promising the follow-up test cases to reach
    'safe' (false positive) state for the soundness violation, by using the maximize the max_diff.
    min_diff is not used in this case.

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
                             BK_FILE_MAP.get(bk_type) + '_' + 'soundness' + '.csv')
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

    # stage 1
    toolbox.register('evaluate', partial(eval_stage_1, timestamp=timestamp, param_list=param_list, bk_type=bk_type, mode='soundness'))
    # initialize population
    population = [Scenario.get_conflict_one() for _ in range(POP_SIZE)]
    curr_gen = 0
    # initialize sid
    for index, c in enumerate(population):
        c.gid = curr_gen
        c.sid = index

    invalid_ind = [ind for ind in population if not ind.fitness.valid]
    fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
    for ind, fit in zip(invalid_ind, fitnesses):
        # the first direction is the min_dist of source scenario
        # the second direction is to 0 in the first stage
        ind.fitness.values = (fit, 0)
    # update the Pareto front
    hof.update(population)

    while curr_gen < STAGE1:
        curr_gen += 1
        offspring = algorithms.varOr(population, toolbox, POP_SIZE, cxpb, mutpb)

        # update gid and sid in offspring
        for index, c in enumerate(offspring):
            c.gid = curr_gen
            c.sid = index

        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = (fit, 0)
        # update the Pareto front
        hof.update(offspring)

        # Select the next generation population
        population[:] = toolbox.select(population + offspring, POP_SIZE)

        # check if the population is convergent
        pop_fit = [ind.fitness.values[0] for ind in population]
        # ascending order
        pop_fit.sort()
        # 80% of the population min_dist should be less than 5 -> convergent
        if pop_fit[int(POP_SIZE * 0.8)] < 5:
            break

    # stage 2
    # register new evaluate function
    toolbox.unregister('evaluate')
    toolbox.register('evaluate', partial(eval_stage_2, timestamp=timestamp, param_list=param_list, bk_type=bk_type, mode='soundness'))

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
            # direction 1: minimize dist[0]
            # direction 2: maximize max_diff
            ind.fitness.values = (fit[0], fit[2])
        # update the Pareto front
        hof.update(offspring)

        # Select the next generation population
        population[:] = toolbox.select(population + offspring, POP_SIZE)

        # timer check
        tdelta = (datetime.now() - start_time).total_seconds()
        if tdelta / 3600 > RUN_FOR_HOUR:
            compress_record_files(containers, timestamp, bk_type, 'soundness')
            break

if __name__ == '__main__':

    main_soundness(bk_type='MessageBroker', cxpb=0.8, mutpb=0.2)
