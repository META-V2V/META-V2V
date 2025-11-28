import os
import csv
from datetime import datetime
from broker.factory import BrokerFactory
from apollo.container import ApolloContainer
from scenario import Scenario
from scenario.scenario_runner import ScenarioRunner
from hdmap.parser import MapParser
from genetic.evaluate import eval_stage_2
from utils.compress import compress_record_files
from config import (APOLLO_ROOT, HD_MAP, MAX_ADC_COUNT, RECORDS_DIR, RUN_FOR_HOUR, BK_PARAM_MAP)
from utils import BK_FILE_MAP, BK_HEAD_MAP

# [Warning] Please do not modify this file's name,
# coz we've used inspect.stack() to determine which entrance is calling
# Although it's not a good practice, we just do not want to use so many parameters in the functions

def main_random(bk_type: str):
    """
    this script is used for baseline experiment, i.e. random generation
    :param str bk_type: the type of broker to be used
    """

    mp = MapParser.get_instance(HD_MAP)
    bkf = BrokerFactory()
    containers = [
        ApolloContainer(APOLLO_ROOT, f'ROUTE_{x}') for x in range(MAX_ADC_COUNT)]
    for ctn in containers:
        ctn.start_instance()
        ctn.start_dreamview()
        print(f'Dreamview at http://{ctn.ip}:{ctn.port}')
    srunner = ScenarioRunner(containers)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    param_list = BK_PARAM_MAP.get(bk_type)

    # write the header of csv file
    if not os.path.exists(os.path.join(RECORDS_DIR, timestamp)):
        os.makedirs(os.path.join(RECORDS_DIR, timestamp))
    file_path = os.path.join(RECORDS_DIR, timestamp,
                             BK_FILE_MAP.get(bk_type) + '_' + 'random' + '.csv')
    with open(file_path, 'w') as f:
        writer = csv.writer(f)
        header = ['Generation', 'Individual']
        for i in range(len(param_list) + 1):
            header.extend([f'{BK_HEAD_MAP.get(bk_type)}_{i}', f'dist_{i}', f'diff_{i}'])
        header.append('max_diff')
        header.append('min_diff')
        writer.writerow(header)

    # start the random testing cycle
    start_time = datetime.now()
    curr_ind = 0

    while True:
        individual = Scenario.get_conflict_one()
        individual.gid = 0
        individual.sid = curr_ind
        eval_stage_2(individual, timestamp, param_list, bk_type, mode='random')
        curr_ind += 1

        # timer check
        tdelta = (datetime.now() - start_time).total_seconds()
        if tdelta / 3600 > RUN_FOR_HOUR:
            compress_record_files(containers, timestamp, bk_type, 'random')
            break

if __name__ == '__main__':

    main_random(bk_type='MessageBroker')
