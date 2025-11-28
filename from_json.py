import os
import json
from datetime import datetime
from scenario import Scenario
from scenario.scenario_runner import ScenarioRunner
from apollo.container import ApolloContainer
from hdmap.parser import MapParser
from broker.factory import BrokerFactory
from config import HD_MAP, MAX_ADC_COUNT, APOLLO_ROOT, MT_ROOT
from genetic import min_distance

def main():

    # interactive input of the scenario and communication json files from user
    scenario_json = input('Enter the scenario json file path: ')
    scenario_json = scenario_json.strip().strip('"').strip("'")
    while not os.path.isfile(scenario_json):
        print(f'Scenario json file {scenario_json} not found, please enter again')
        scenario_json = input('Enter the scenario json file path: ')
        scenario_json = scenario_json.strip().strip('"').strip("'")
    communication_json = input('Enter the communication json file path: ')
    communication_json = communication_json.strip().strip('"').strip("'")
    while not os.path.isfile(communication_json):
        print(f'Communication json file {communication_json} not found, please enter again')
        communication_json = input('Enter the communication json file path: ')
        communication_json = communication_json.strip().strip('"').strip("'")

    mp = MapParser.get_instance(HD_MAP)
    bkf = BrokerFactory()

    # set the type of Message Broker
    with open(communication_json, 'r') as fp:
        bk_param = json.load(fp)
        bkf.set_mode(bk_param['mode'])
        bkf.set_param(bk_param['param'])

    # initialize the json replay containers
    containers = [ApolloContainer(
        APOLLO_ROOT, f'ROUTE_{x}') for x in range(MAX_ADC_COUNT)]
    for ctn in containers:
        ctn.start_instance()
        ctn.start_dreamview()
        print(f'Dreamview at http://{ctn.ip}:{ctn.port}')
    srunner = ScenarioRunner(containers)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # load the Scenario individual from the json file
    ind = Scenario.from_json(scenario_json)
    ind.gid = 0       # generation id
    ind.sid = 0       # scenario id
    ind.fid = 0       # follow id

    # run the scenario using containers
    min_distance(timestamp, ind)
    print(f'Record file saved in ./records/{timestamp}/Generation_00000/Scenario_00000/Follow_00000 directory')
    print(f'those .00000 files\' infinite cycle replay is available in {MT_ROOT}/replay.py')

if __name__ == '__main__':

    main()
