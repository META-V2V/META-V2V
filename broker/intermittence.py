import time
from logging import Logger
from threading import Thread
from typing import List, Dict
import random
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

class IntermittenceBroker(MessageBroker):
    """
    Modified MessageBroker to implement random message dropping with probability p

    :param List[ApolloRunner] runners: list of runners each controlling an ADS instance
    :param float p: probability of dropping messages, follows Bernoulli distribution
    """
    runners: List[ApolloRunner]
    p: float
    spinning: bool
    logger: Logger
    t: Thread

    def __init__(self, runners: List[ApolloRunner], p: float) -> None:
        """
        Constructor
        """
        super().__init__(runners)
        self.p = p
        self.logger = get_logger(self.__class__.__name__)

    def _spin(self) -> None:
        """
        Modified _spin() function to implement the random message dropping mechanism
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

            # collect the list of senders for each receiver
            # using Bernoulli distribution to determine whether to allow the message transmission
            receive_list: Dict[int, List[int]] = dict()
            for receiver in self.runners:
                receive_list[receiver.nid] = []
                for sender in self.runners:
                    if receiver == sender:
                        continue              # exclude ego vehicle
                    if random.random() < self.p:
                        continue              # drop message with probability p
                    receive_list[receiver.nid].append(sender.nid)

            # publish perception messages for receivers
            for runner in self.runners:
                perception_obs = []
                for x in receive_list[runner.nid]:
                    try:
                        perception_obs.append(obs[x])
                    except KeyError:
                        continue
                perception_obs += pds         # add pedestrian obstacles
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

            # Note: move the min_distance update to ScenarioRunner for LatencyBroker

            header_sequence_num += 1
            time.sleep(1/PERCEPTION_FREQUENCY)
            curr_time += 1/PERCEPTION_FREQUENCY

    # def broadcast(self, channel: Channel, data: bytes): No need to override
    # def spin(self): No need to override
    # def stop(self): No need to override
