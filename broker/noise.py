import time
from logging import Logger
from threading import Thread
from typing import List, Dict
import random
from apollo.apollo_runner import ApolloRunner
from apollo.cyber_bridge import Topics
from broker import MessageBroker
from apollo.utils import to_Point3D, generate_adc_polygon
from config import PERCEPTION_FREQUENCY, APOLLO_VEHICLE_LENGTH, APOLLO_VEHICLE_WIDTH, APOLLO_VEHICLE_HEIGHT
from scenario.pd_manager import PedestrianManager
from modules.common.proto.header_pb2 import Header
from modules.perception.proto.perception_obstacle_pb2 import \
    PerceptionObstacles, PerceptionObstacle
from modules.localization.proto.localization_pb2 import LocalizationEstimate
from modules.common.proto.geometry_pb2 import Point3D
from utils import get_logger

class NoiseBroker(MessageBroker):
    """
    Modified MessageBroker to implement noise injection for localization messages,
    using Gaussian distribution, sigma is the standard deviation

    :param List[ApolloRunner] runners: list of runners each controlling an ADS instance
    :param float sigma1: standard deviation of the position noise
    :param float sigma2: standard deviation of the heading noise
    :param float sigma3: standard deviation of the linear velocity noise
    :param float sigma4: standard deviation of the acceleration noise
    """
    runners: List[ApolloRunner]
    sigma1: float
    sigma2: float
    sigma3: float
    sigma4: float
    spinning: bool
    logger: Logger
    t: Thread

    def __init__(self, runners: List[ApolloRunner], sigma1: float, sigma2: float, 
                 sigma3: float, sigma4: float) -> None:
        """
        Constructor
        """
        super().__init__(runners)
        self.sigma1 = sigma1
        self.sigma2 = sigma2
        self.sigma3 = sigma3
        self.sigma4 = sigma4
        self.logger = get_logger(self.__class__.__name__)

    @staticmethod
    def gaussian_noise(value: float, std_dev: float, scale: float=1.0) -> float:
        """
        Generate Gaussian noise with no bias

        :param float value: original value
        :param float std_dev: standard deviation of the Gaussian distribution
        :param float scale: scale of the Gaussian distribution, defaults to 1.0
        :returns: value with Gaussian noise
        :rtype: float
        """
        return value + scale * random.gauss(mu=0.0, sigma=std_dev)

    def noise_Point3D(self, data: Point3D, std_dev: float, scale: float = 1.0) -> Point3D:
        """
        Add noise to Point3D data

        :param Point3D data: original Point3D message
        :param float std_dev: standard deviation of the Gaussian distribution
        :param float scale: scale of the Gaussian distribution, defaults to 1.0
        :returns: Point3D data with noise
        :rtype: Point3D
        """
        return Point3D(
            x=self.gaussian_noise(data.x, std_dev, scale),
            y=self.gaussian_noise(data.y, std_dev, scale),
            z=data.z
        )

    def noise_localization_to_obstacle(self, _id: int, data: LocalizationEstimate) -> PerceptionObstacle:
        """
        Converts LocalizationEstimate to PerceptionObstacle. The localization message of an ADS
        instance is used as part of the perception message for other ADS instances.

        :param int _id: ID of the obstacle
        :param LocalizationEstimate data: localization message of the ADC
        :returns: PerceptionObstacle message converted from localization of an ADC
        :rtype: PerceptionObstacle
        """
        # preprocess data, replace NaN with 0.0
        position = to_Point3D(data.pose.position)
        velocity = to_Point3D(data.pose.linear_velocity)
        acceleration = to_Point3D(data.pose.linear_acceleration)

        # add noise to position(x, y), heading, velocity and acceleration
        position_noise = self.noise_Point3D(position, self.sigma1)
        heading_noise = self.gaussian_noise(data.pose.heading, self.sigma2)
        velocity_noise = self.noise_Point3D(velocity, self.sigma3)
        acceleration_noise = self.noise_Point3D(acceleration, self.sigma4)

        # create a PerceptionObstacle obstacle
        obs = PerceptionObstacle(
            id=_id,
            position=position_noise,
            theta=heading_noise,
            velocity=velocity_noise,
            acceleration=acceleration_noise,
            length=APOLLO_VEHICLE_LENGTH,
            width=APOLLO_VEHICLE_WIDTH,
            height=APOLLO_VEHICLE_HEIGHT,
            type=PerceptionObstacle.VEHICLE,
            timestamp=data.header.timestamp_sec,
            tracking_time=1.0,
            polygon_point=generate_adc_polygon(
                position_noise, heading_noise)
        )
        return obs

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
                loc: LocalizationEstimate = runner.localization
                if loc and loc.header.module_name == 'SimControl':
                    locations[runner.nid] = runner.localization

            # convert localization into obstacles, with noise
            obs: Dict[int, PerceptionObstacle] = dict()
            for k in locations:
                obs[k] = self.noise_localization_to_obstacle(k, locations[k])

            # pedestrian obstacles
            pm = PedestrianManager.get_instance()
            pds = pm.get_pedestrians(curr_time)

            # publish obstacle to all running instances
            for runner in self.runners:
                perception_obs = [obs[x]
                                  for x in obs if x != runner.nid] + pds
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
