import time
import queue
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

class LatencyBroker(MessageBroker):
    """
    Modified MessageBroker to implement latency of perception messages

    :param List[ApolloRunner] runners: list of runners each controlling an ADS instance
    :param float latency: latency time of perception messages
    """
    runners: List[ApolloRunner]
    latency: float
    spinning: bool
    logger: Logger
    t: Thread
    delay_thread: Thread
    message_queue: queue.Queue

    def __init__(self, runners: List[ApolloRunner], latency: float) -> None:
        """
        Constructor
        """
        super().__init__(runners)
        self.latency = latency
        self.logger = get_logger(self.__class__.__name__)
        self.message_queue = queue.Queue()
        self.delay_thread = None

    def _delay_worker(self) -> None:
        """
        Worker thread to handle delayed message publishing
        """
        while self.spinning:
            try:
                # Get message from queue with timeout
                message_data = self.message_queue.get(timeout=0.1)
                if message_data is None:  # Shutdown signal
                    break
                
                runner_nid, perception_obs, header_sequence_num = message_data
                
                # Wait for the specified latency
                time.sleep(self.latency)
                
                # Publish the delayed message
                header = Header(
                    timestamp_sec=time.time(),
                    module_name='MAGGIE',
                    sequence_num=header_sequence_num
                )
                bag = PerceptionObstacles(
                    header=header,
                    perception_obstacle=perception_obs,
                )
                
                # Find the corresponding runner and publish
                for runner in self.runners:
                    if runner.nid == runner_nid:
                        runner.container.bridge.publish(
                            Topics.Obstacles, bag.SerializeToString()
                        )
                        break
                        
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in delay worker: {e}")

    def _spin(self) -> None:
        """
        Modified _spin() function to implement latency of perception messages
        """
        header_sequence_num = 0
        curr_time = 0.0
        
        # Start delay worker thread
        self.delay_thread = Thread(target=self._delay_worker)
        self.delay_thread.start()
        
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

            # collect perception obj messages and queue them for delayed publishing
            for runner in self.runners:
                perception_obs = []
                for i in obs_poly:
                    if i == runner.nid:    # exclude ego vehicle
                        continue
                    if runner.nid in obs_poly and i in obs_poly:
                        perception_obs.append(obs[i])
                perception_obs += pds      # add pedestrian obstacles
                
                # Queue the message for delayed publishing
                self.message_queue.put((runner.nid, perception_obs, header_sequence_num))

            # Note: move the min_distance update to ScenarioRunner for LatencyBroker

            header_sequence_num += 1
            time.sleep(1/PERCEPTION_FREQUENCY)
            curr_time += 1/PERCEPTION_FREQUENCY

    def stop(self) -> None:
        """
        Stops forwarding localization and delay worker
        """
        self.logger.debug('Stopping')
        if not self.spinning:
            return
        self.spinning = False
        
        # Signal delay worker to stop
        if self.delay_thread and self.delay_thread.is_alive():
            self.message_queue.put(None)  # Shutdown signal
            self.delay_thread.join()
        
        if self.t and self.t.is_alive():
            self.t.join()

    # def broadcast(self, channel: Channel, data: bytes): No need to override
    # def spin(self): No need to override
