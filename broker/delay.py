import time
from logging import Logger
from threading import Thread
from typing import List
from broker import MessageBroker
from apollo.apollo_runner import ApolloRunner
from apollo.cyber_bridge import Topics
from apollo.utils import localization_to_obstacle, obstacle_to_polygon
from config import PERCEPTION_FREQUENCY
from scenario.pd_manager import PedestrianManager
from modules.common.proto.header_pb2 import Header
from modules.perception.proto.perception_obstacle_pb2 import PerceptionObstacles
from utils import get_logger

class DelayBroker(MessageBroker):
    """
    Modified MessageBroker to implement delay of perception messages

    :param List[ApolloRunner] runners: list of runners each controlling an ADS instance
    :param float delay: delay time of perception messages
    """
    runners: List[ApolloRunner]
    delay: float
    spinning: bool
    logger: Logger
    t: Thread

    def __init__(self, runners: List[ApolloRunner], delay: float) -> None:
        """
        Constructor
        """
        super().__init__(runners)
        self.delay = delay
        self.logger = get_logger(self.__class__.__name__)

    def _spin(self) -> None:
        """
        Modified _spin() function to implement delay of perception messages
        """
        header_sequence_num = 0
        curr_time = 0.0
        while self.spinning:
            # retrieve localization of running instances
            locations = dict()
            for runner in self.runners:
                loc = runner.localization
                if loc and loc.header.module_name == 'SimControl':
                    locations[runner.nid] = runner.localization
            
            # convert localization into obstacles
            obs = dict()
            obs_poly = dict()
            for k in locations:
                obs[k] = localization_to_obstacle(k, locations[k])
                obs_poly[k] = obstacle_to_polygon(obs[k])

            # pedestrian obstacles
            pm = PedestrianManager.get_instance()
            pds = pm.get_pedestrians(curr_time)

            # collect perception obj messages
            perception_dict = dict()
            for runner in self.runners:
                perception_obs = []
                for i in obs_poly:
                    if i == runner.nid:    # exclude ego vehicle
                        continue
                    if runner.nid in obs_poly and i in obs_poly:
                        perception_obs.append(obs[i])
                perception_obs += pds      # add pedestrian obstacles
                perception_dict[runner.nid] = perception_obs

            time.sleep(self.delay)         # delay perception messages by self.delay seconds

            # publish perception messages
            for runner in self.runners:
                header = Header(
                    timestamp_sec=time.time(),
                    module_name='MAGGIE',
                    sequence_num=header_sequence_num
                )
                bag = PerceptionObstacles(
                    header=header,
                    perception_obstacle=perception_dict[runner.nid],
                )
                runner.container.bridge.publish(
                    Topics.Obstacles, bag.SerializeToString()
                )

            # Note: move the min_distance update to ScenarioRunner for DelayBroker

            header_sequence_num += 1
            time.sleep(1/PERCEPTION_FREQUENCY)
            curr_time += 1/PERCEPTION_FREQUENCY

    # def broadcast(self, channel: Channel, data: bytes): No need to override
    # def spin(self): No need to override
    # def stop(self): No need to override
