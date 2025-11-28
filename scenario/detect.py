from typing import List, Dict, Tuple
from apollo.apollo_runner import ApolloRunner
from apollo.utils import localization_to_obstacle, obstacle_to_polygon
from modules.localization.proto.localization_pb2 import LocalizationEstimate
from scenario import Scenario

class CollisionDetector:
    """
    Collision violation online monitor

    note: We've redesigned the min_distance update mechanism, decoupling from the message broker,
    so that the data is the ground truth rather than the distorted in subclasses of message broker.
    Also, in this way, we can implement some other collision times detection, which the collisions
    may happen several times in a single cycle. online-causation monitor (Signal Temporal Logic, STL)
    techniques can be used in the future.

    :param List[ApolloRunner] runners: the runners to be used for collision detection
    :param Scenario scenario: the scenario to be used for collision detection
    :param BrokerFactory bkf: the broker factory to be used for scenario execution
    :param Dict[Tuple[int, int], float] min_distances: the min_distances to be used for current optimization
    :param Dict[Tuple[int, int], List[float]] dist_records: the dist_records for collision times calculation after the scenario executed
    """
    runners: List[ApolloRunner]
    scenario: Scenario
    min_distances: Dict[Tuple[int, int], float]
    dist_records: Dict[Tuple[int, int], List[float]]

    def __init__(self, runners: List[ApolloRunner], scenario: Scenario):
        """
        Constructor
        """
        self.runners = runners
        self.scenario = scenario
        self.min_distances = {}
        for i in range(len(runners)):
            for j in range(i + 1, len(runners)):
                self.min_distances[(i, j)] = float('inf')
        self.dist_records = {}
        for i in range(len(runners)):
            for j in range(i + 1, len(runners)):
                self.dist_records[(i, j)] = []

    def get_polygon_dist(self) -> Dict[Tuple[int, int], float]:
        """
        Get the ADC polygon distance between two ADS localizations

        :returns: the ADC polygon distance pairs
        :rtype: Dict[Tuple[int, int], float]
        """
        # retrieve localization of running instances
        locs: Dict[int, LocalizationEstimate] = dict()
        for runner in self.runners:
            loc: LocalizationEstimate = runner.localization
            if loc and loc.header.module_name == 'SimControl':
                locs[runner.nid] = runner.localization

        # convert localization into obstacle's polygon in Shapely
        obs = dict()
        obs_poly = dict()
        for k in locs:
            obs[k] = localization_to_obstacle(k, locs[k])
            obs_poly[k] = obstacle_to_polygon(obs[k])

        poly_dist: Dict[Tuple[int, int], float] = dict()
        for i in range(len(self.runners)):
            for j in range(i + 1, len(self.runners)):
                if self.runners[i].nid in obs_poly and self.runners[j].nid in obs_poly:
                    poly_dist[(i, j)] = obs_poly[self.runners[i].nid].distance(obs_poly[self.runners[j].nid])
        return poly_dist

    def detect(self) -> None:
        """
        Detect the current distance between each pair of runners, record the dist_records and update the min_distances
        """
        cur_dist = self.get_polygon_dist()

        # save records hasn't been implemented yet, for future optimization extended targets
        # still don't have a good idea about using offline analysis or online-causation monitor (STL)
        # to detect collision times
        self.dist_records = []

        # update min_distances
        for pair in cur_dist:
            if pair not in self.min_distances:
                self.min_distances[pair] = cur_dist[pair]
            else:
                self.min_distances[pair] = min(self.min_distances[pair], cur_dist[pair])

    def get_min_distances(self) -> Dict[Tuple[int, int], float]:
        """
        Get the min_distances

        :returns: the min_distances
        :rtype: Dict[Tuple[int, int], float]
        """
        return self.min_distances
    
    def get_times(self) -> Dict[Tuple[int, int], int]:
        """
        Offline analyze the dist records to judge collision times between each pair of runners

        :returns: the collision times between each pair of runners
        :rtype: Dict[Tuple[int, int], int]
        """
        raise NotImplementedError
