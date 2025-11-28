import time
from logging import Logger
from typing import List, Optional, Set, Tuple
from apollo.container import ApolloContainer
from apollo.cyber_bridge import Topics
from apollo.utils import PositionEstimate, extract_main_decision, pos_estimate_eq_loc_estimate
from modules.common.proto.geometry_pb2 import Point3D
from modules.common.proto.header_pb2 import Header
from modules.localization.proto.localization_pb2 import LocalizationEstimate
from modules.localization.proto.pose_pb2 import Pose
from modules.map.proto.map_pb2 import Map
from modules.planning.proto.planning_pb2 import ADCTrajectory
from modules.routing.proto.routing_pb2 import LaneWaypoint, RoutingRequest
from config import HD_MAP, USE_SIM_CONTROL_STANDALONE
from hdmap.parser import MapParser
from utils import get_logger

class ApolloRunner:
    """
    Class to manage and run an Apollo instance

    :param int nid: an unique ID assigned to this container runner
    :param ApolloContainer ctn: the Apollo container controlled by this runner
    :param PositionEstimate start: the initial location of this Apollo instance
    :param float start_time: the amount of time this Apollo instance waits before starts moving
    :param List[PositionEstimate] waypoints: the expected route this Apollo instance should complete
    """
    logger: Logger
    nid: int
    container: ApolloContainer
    start: PositionEstimate
    start_time: float
    waypoints: List[PositionEstimate]
    routing_started: bool
    stop_time_counter: float
    localization: Optional[LocalizationEstimate]
    planning: Optional[ADCTrajectory]
    __decisions: Set[Tuple]
    __coords: List[Tuple]
    __runner_time: int              # Add new variable to count time with ScenarioRunner

    def __init__(self,
                 nid: int,
                 ctn: ApolloContainer,
                 start: PositionEstimate,
                 start_time: float,
                 waypoints: List[PositionEstimate]
                 ) -> None:
        """
        Constructor
        """
        self.logger = get_logger(f'ApolloRunner[{ctn.container_name}]')
        self.nid = nid
        self.container = ctn
        self.start = start
        self.start_time = start_time
        self.waypoints = waypoints

    def register_publishers(self) -> None:
        """
        Register publishers for the cyberRT communication
        """
        for c in [Topics.Localization, Topics.Obstacles, Topics.TrafficLight, Topics.RoutingRequest]:
            self.container.bridge.add_publisher(c)

    def register_subscribers(self) -> None:
        """
        Register subscribers for the cyberRT communication, using callback functions
        """
        def lcb(data):
            """
            Callback function when localization message is received
            """
            self.localization = data
            self.__coords.append((data.pose.position.x, data.pose.position.y))

        def pcb(data):
            """
            Callback function when planning message is received
            """
            self.planning = data
            decisions = extract_main_decision(data)
            self.__decisions.update(decisions)

        self.container.bridge.add_subscriber(Topics.Localization, lcb)
        self.container.bridge.add_subscriber(Topics.Planning, pcb)

    def initialize(self) -> None:
        '''
        Resets and initializes all necessary modules of Apollo
        '''
        self.logger.debug(
            f'Initializing container {self.container.container_name}')

        self.container.reset()
        self.register_publishers()
        self.send_initial_localization()
        if not USE_SIM_CONTROL_STANDALONE:
            self.container.dreamview.start_sim_control()

        # initialize routing started flag
        self.routing_started = False
        self.__decisions = set()
        self.__coords = list()
        self.planning = None
        self.localization = None
        self.register_subscribers()
        self.container.bridge.spin()
        self.logger.debug(
            f'Initialized container {self.container.container_name}')
        self.__runner_time = 0  # set initial time to 0, will be updated by ScenarioRunner

    def should_send_routing(self, t: float) -> bool:
        """
        Check if a routing request should be send to the Apollo instance

        :param float t: the amount of time since the start of the simulation
        :returns: True if should send, False otherwise
        :rtype: bool
        """
        return t >= self.start_time and not self.routing_started

    def send_initial_localization(self) -> None:
        """
        Send the instance's initial location to cyberRT
        """
        self.logger.debug('Sending initial localization')
        ma = MapParser.get_instance(HD_MAP)
        coord, heading = ma.get_coordinate_and_heading(
            self.start.lane_id, self.start.s)

        # create localization message
        loc: LocalizationEstimate = LocalizationEstimate(
            header=Header(
                timestamp_sec=time.time(),
                module_name="MAGGIE",
                sequence_num=0
            ),
            pose=Pose(
                position=coord,
                heading=heading,
                linear_velocity=Point3D(x=0, y=0, z=0)
            )
        )
        # Publish 4 messages to the localization channel so 
        # SimControl can pick these messages up.
        for i in range(4):
            loc.header.sequence_num = i
            self.container.bridge.publish(
                Topics.Localization, loc.SerializeToString())
            time.sleep(0.5)

    def send_routing(self) -> None:
        """
        Send the instance's routing request to cyberRT
        """
        self.logger.debug(
            f'Sending routing request to {self.container.container_name}')
        self.routing_started = True
        ma = MapParser.get_instance(HD_MAP)
        coord, heading = ma.get_coordinate_and_heading(
            self.start.lane_id, self.start.s)

        # create routing request message
        rr = RoutingRequest(
            header=Header(
                timestamp_sec=time.time(),
                module_name="MAGGIE",
                sequence_num=0
            ),
            waypoint=[
                LaneWaypoint(
                    pose=coord,
                    heading=heading
                )
            ] + [
                LaneWaypoint(
                    id=x.lane_id,
                    s=x.s,
                ) for x in self.waypoints
            ]
        )

        self.container.bridge.publish(
            Topics.RoutingRequest, rr.SerializeToString()
        )

    def stop(self, stop_reason: str) -> None:
        """
        Stop the modules in the container

        :param str stop_reason: a debug message indicating why the instance is stopped
        """
        self.logger.debug('Stopping container')
        self.container.stop_all()
        self.logger.debug(f"STOPPED [{stop_reason}]")

    def get_decisions(self) -> Set[Tuple]:
        """
        Get the decisions made by the Apollo instance

        :returns: list of decisions made
        :rtype: Set[Tuple]
        """
        return self.__decisions

    def get_trajectory(self) -> List[Tuple]:
        """
        Get the points traversed by this Apollo instance

        :returns: list of coordinates traversed by this Apollo instance
        :rtype: List[Tuple[float, float]]
        """
        return self.__coords

    def has_arrived_destination(self) -> bool:
        """
        Check if the Apollo instance has arrived at its destination

        :returns: True if arrived, False otherwise
        :rtype: bool
        """

        return pos_estimate_eq_loc_estimate(self.waypoints[-1], self.localization)

    def update_time(self, t: int) -> None:
        '''
        Set the time of the ApolloRunner

        :param int t: the time to set
        '''

        self.__runner_time = t
    
    def get_time(self) -> int:
        """
        Get the time of the ApolloRunner

        :returns: the time of the ApolloRunner
        :rtype: int
        """
        return self.__runner_time
