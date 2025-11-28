import time
from logging import Logger
from threading import Thread
from typing import List
from apollo.apollo_runner import ApolloRunner
from apollo.cyber_bridge import Topics
from broker import MessageBroker
from apollo.utils import localization_to_obstacle, obstacle_to_polygon
from config import PERCEPTION_FREQUENCY
from scenario.pd_manager import PedestrianManager
from modules.common.proto.header_pb2 import Header
from modules.perception.proto.perception_obstacle_pb2 import \
    PerceptionObstacles
from utils import get_logger

class RadiusBroker(MessageBroker):
    """
    Modified MessageBroker to implement distance-capability obstacle filtering,
    using a radius threshold to determine whether to filter out obstacles

    :param List[ApolloRunner] runners: list of runners each controlling an ADS instance
    :param float radius: radius threshold for obstacle filtering
    """
    runenrs: List[ApolloRunner]
    radius: float
    spinning: bool
    logger: Logger
    t: Thread

    def __init__(self, runners: List[ApolloRunner], radius: float) -> None:
        """
        Constructor
        """
        super().__init__(runners)
        self.radius = radius
        self.logger = get_logger(self.__class__.__name__)

    def _spin(self) -> None:
        """
        Helper function to start forwarding localization
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

            # publish obstacle to all running instances
            # filter out obstacles that are too far away judged by param radius
            for runner in self.runners:
                perception_obs = []
                for i in obs_poly:
                    if i == runner.nid:    # exclude ego vehicle
                        continue
                    if runner.nid in obs_poly and i in obs_poly:
                        dist = obs_poly[runner.nid].distance(obs_poly[i])
                        if dist <= self.radius:
                            perception_obs.append(obs[i])
                perception_obs += pds

                header = Header(
                    timestamp_sec=time.time(),
                    module_name='MAGGIE',
                    sequence_num=header_sequence_num
                )
                bag = PerceptionObstacles(
                    header=header,
                    perception_obstacle=perception_obs,
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
