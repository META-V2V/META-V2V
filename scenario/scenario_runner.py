import threading
import time
from logging import Logger
from typing import List, Optional, Tuple, Dict
from apollo.container import ApolloContainer
from apollo.apollo_runner import ApolloRunner
from apollo.cyber_bridge import Topics
from apollo.utils import clean_appolo_dir
from broker.factory import BrokerFactory
from config import SCENARIO_UPPER_LIMIT
from scenario import Scenario
from scenario.ad_agents import ADAgent
from scenario.pd_manager import PedestrianManager
from scenario.detect import CollisionDetector
from utils import (get_logger, get_scenario_logger, random_numeric_id,
                   save_record_files_and_chromosome)

class ScenarioRunner:
    """
    Executes a scenario based on the specification

    :param List[ApolloContainer] containers: containers to be used for scenario
    :param Scenario curr_scenario: the current scenario to be executed
    :param PedestrianManager pm: the pedestrian manager
    :param bool is_initialized: whether the scenario is initialized
    :param Dict[Tuple[int, int], float] min_distances: the min_distances to be used for current optimization
    """
    logger: Logger
    containers: List[ApolloContainer]
    curr_scenario: Optional[Scenario]
    pm: Optional[PedestrianManager]
    is_initialized: bool
    __instance = None
    __runners: List[ApolloRunner]
    min_distances: Dict[Tuple[int, int], float]

    def __init__(self, containers: List[ApolloContainer]) -> None:
        """
        Constructor
        """
        self.logger = get_logger('ScenarioRunner')
        self.containers = containers
        self.curr_scenario = None
        self.is_initialized = False
        ScenarioRunner.__instance = self

    @staticmethod
    def get_instance() -> 'ScenarioRunner':
        """
        Returns the singleton instance

        :returns: an instance of runner
        :rtype: ScenarioRunner
        """
        return ScenarioRunner.__instance

    def set_scenario(self, s: Scenario) -> None:
        """
        Set the scenario for this runner

        :param Scenario s: scenario representation
        """
        self.curr_scenario = s
        self.is_initialized = False

    def init_scenario(self) -> None:
        """
        Initialize the scenario, create ApolloRunner instances and initialize them
        """
        nids = random_numeric_id(len(self.curr_scenario.ad_section.adcs))
        self.__runners = list()
        for i, c, a in zip(nids, self.containers, self.curr_scenario.ad_section.adcs):
            a.apollo_container = c.container_name
            self.__runners.append(
                ApolloRunner(
                    nid=i,
                    ctn=c,
                    start=a.initial_position,
                    waypoints=a.waypoints,
                    start_time=a.start_t
                )
            )

        # initialize Apollo instances
        threads = list()
        for index in range(len(self.__runners)):
            threads.append(threading.Thread(
                target=self.__runners[index].initialize
            ))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # remove Apollo logs
        clean_appolo_dir()

        # initialize pedestrian manager
        self.pm = PedestrianManager(self.curr_scenario.pd_section)
        self.is_initialized = True

    def run_scenario(self, timestamp:str, gen_name: str, ind_name: str, fol_name: str, save_record=False) -> List[Tuple[ApolloRunner, ADAgent]]:
        """
        Execute the scenario based on the specification

        :param str timestamp: timestamp of this runtime batch
        :param str gen_name: name of the generation
        :param str ind_name: name of the individual
        :param str fol_name: name of the follow-up
        :param bool save_record: whether to save records or not, default to False
        :returns: a list of tuples, each containing an ApolloRunner and an ADAgent
        :rtype: List[Tuple[ApolloRunner, ADAgent]]
        """
        num_adc = len(self.curr_scenario.ad_section.adcs)
        self.logger.info(
            f'{num_adc} agents running a scenario G{self.curr_scenario.gid}S{self.curr_scenario.sid}F{self.curr_scenario.fid}.'
        )
        if self.curr_scenario is None or not self.is_initialized:
            print('Error: No chromosome or not initialized')
            return
        # create the distinct broker for each runtime, using Factory Pattern
        mbk = BrokerFactory().createbk(self.__runners)
        self.logger.info(
            f'{BrokerFactory().mode} is used for this runtime.'
        )
        mbk.spin()
        runner_time = 0
        scenario_logger = get_scenario_logger()
        # starting scenario
        if save_record:
            for r in self.__runners:
                r.container.start_recorder(fol_name)
        # create the collision detector
        detector = CollisionDetector(self.__runners, self.curr_scenario)

        # Begin Scenario Cycle
        while True:
            # Publish TrafficLight
            tld = self.curr_scenario.tl_section.detection(runner_time/1000)
            mbk.broadcast(Topics.TrafficLight, tld.SerializeToString())
            # Send Routing
            for ar in self.__runners:
                if ar.should_send_routing(runner_time/1000):
                    ar.send_routing()

            # detect the current distance between each pair of runners
            detector.detect()

            # Print Scenario Time
            if runner_time % 100 == 0:
                scenario_logger.info(
                    f'Scenario time: {round(runner_time / 1000, 1)}.')
            # Check if scenario exceeded upper limit
            if runner_time / 1000 >= SCENARIO_UPPER_LIMIT:
                scenario_logger.info('\n')
                break

            time.sleep(0.1)
            runner_time += 100
            # Sync time for all ApolloRunners, leave for future usage
            for ar in self.__runners:
                ar.update_time(runner_time)

        # get the min_distances from detector
        self.min_distances = detector.get_min_distances()

        if save_record:
            for r in self.__runners:
                r.container.stop_recorder()
            # buffer period for recorders to stop
            time.sleep(2)
            bk_mode = BrokerFactory().mode
            bk_param = BrokerFactory().param
            save_record_files_and_chromosome(
                timestamp, gen_name, ind_name, fol_name, self.curr_scenario.to_dict(), self.min_distances, bk_mode, bk_param)

        mbk.stop()
        for runner in self.__runners:
            runner.stop('MAIN')

        self.logger.debug(
            f'Scenario ended. Length: {round(runner_time/1000, 2)} seconds.')

        self.is_initialized = False

        return list(zip(self.__runners, self.curr_scenario.ad_section.adcs))
