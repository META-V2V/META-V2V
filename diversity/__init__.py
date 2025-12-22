"""
Diversity module is used to calculate the similarity of two scenarios,
Demo for future extension for other researchers.
We adopt the population diversity metric used in the MOSAT paper, 
https://dl.acm.org/doi/10.1145/3540250.3549100
namely the average distance difference between vehicle trajectories.
Since each scenario may involve multiple vehicles, we simplify this metric as follows.
Specifically, for each individual in the source test cases of a population,
we select the trajectories of the two vehicles that are most likely to interact.
We then use cyber_record to slice the trajectory logs and align them at a temporal
resolution of 0.1 seconds per frame (following ACAV https://dl.acm.org/doi/10.1145/3597503.3639175).
For each pair of scenarios, we compute the average distance between the two vehicles.
Note that this computation is performed across individuals N, combination N(N-1)/2.
i.e., horizontally across multiple scenarios within the same generation.
A little bit slow, any pull request for algorithm optimization is welcome.
"""

import os
import json
from typing import List, Tuple
import math
from diversity.container import ScenarioContainer

def calculate_individual_dist(scenario1: ScenarioContainer, scenario2: ScenarioContainer):
    """
    Calculate the similarity of two scenarios

    :param ScenarioContainer scenario1: the first scenario
    :param ScenarioContainer scenario2: the second scenario
    :return: the similarity of the two scenarios
    :rtype: float
    """
    # get the interesting trajectory
    start_frame1, end_frame1, min_dist_frame1 = scenario1.get_interesting_trajectory()
    start_frame2, end_frame2, min_dist_frame2 = scenario2.get_interesting_trajectory()

    left1 = min_dist_frame1 - start_frame1
    left2 = min_dist_frame2 - start_frame2
    left_min = min(left1, left2)         # minimum left offset
    right1 = end_frame1 - min_dist_frame1
    right2 = end_frame2 - min_dist_frame2
    right_min = min(right1, right2)      # minimum right offset
    scenario1_car1 = scenario1.car1.loc_align[min_dist_frame1 - left_min:min_dist_frame1 + right_min]
    scenario1_car2 = scenario1.car2.loc_align[min_dist_frame1 - left_min:min_dist_frame1 + right_min]
    scenario2_car1 = scenario2.car1.loc_align[min_dist_frame2 - left_min:min_dist_frame2 + right_min]
    scenario2_car2 = scenario2.car2.loc_align[min_dist_frame2 - left_min:min_dist_frame2 + right_min]

    individual_dist = 0
    for i in range(len(scenario1_car1)):
        # the distance between scenario1 car1 and scenario2 car1
        individual_dist += math.sqrt((scenario1_car1[i]['pose']['position']['x'] - scenario2_car1[i]['pose']['position']['x'])**2 + (scenario1_car1[i]['pose']['position']['y'] - scenario2_car1[i]['pose']['position']['y'])**2)
        # the distance between scenario1 car1 and scenario2 car2
        individual_dist += math.sqrt((scenario1_car1[i]['pose']['position']['x'] - scenario2_car2[i]['pose']['position']['x'])**2 + (scenario1_car1[i]['pose']['position']['y'] - scenario2_car2[i]['pose']['position']['y'])**2)
        # the distance between scenario1 car2 and scenario2 car1
        individual_dist += math.sqrt((scenario1_car2[i]['pose']['position']['x'] - scenario2_car1[i]['pose']['position']['x'])**2 + (scenario1_car2[i]['pose']['position']['y'] - scenario2_car1[i]['pose']['position']['y'])**2)
        # the distance between scenario1 car2 and scenario2 car2
        individual_dist += math.sqrt((scenario1_car2[i]['pose']['position']['x'] - scenario2_car2[i]['pose']['position']['x'])**2 + (scenario1_car2[i]['pose']['position']['y'] - scenario2_car2[i]['pose']['position']['y'])**2)

    individual_dist /= (len(scenario1_car1)*4)   # average distance
    return individual_dist

def calculate_one_generation(generation_path: str) -> float:
    """
    traverse different individuals in the same generation, calculate the similarity between individuals

    :param str generation_path: the path of the generation folder
    :return: the similarity of the generation
    :rtype: float
    """

    scenario_folders = [f for f in os.listdir(generation_path) if f.startswith("Scenario_")]
    # scenario_id, car_pair, min_distance
    scenario_candidates: List[Tuple[str, Tuple[int, int], float]] = []
    for scenario in scenario_folders:
        dist_data = json.load(open(os.path.join(generation_path, scenario, "min_distances.json")))
        # get the minimum value dist and the corresponding car pair
        k, v = min(dist_data.items(), key=lambda x: x[1])
        if v < 1.0:
            car_pair = tuple(map(int, k.split(',')))
            scenario_candidates.append((scenario, car_pair, v))
    generation_similarity = 0
    if len(scenario_candidates) < 2:
        return -1
    for i in range(len(scenario_candidates)):
        
        scenario1_path = os.path.join(generation_path, scenario_candidates[i][0])
        scenario1_car1_record = os.path.join(scenario1_path, f"Car_{scenario_candidates[i][1][0]}.00000")
        scenario1_car2_record = os.path.join(scenario1_path, f"Car_{scenario_candidates[i][1][1]}.00000")
        scenario1 = ScenarioContainer([scenario1_car1_record, scenario1_car2_record])
        for j in range(i+1, len(scenario_candidates)):
            scenario2_path = os.path.join(generation_path, scenario_candidates[j][0])
            scenario2_car1_record = os.path.join(scenario2_path, f"Car_{scenario_candidates[j][1][0]}.00000")
            scenario2_car2_record = os.path.join(scenario2_path, f"Car_{scenario_candidates[j][1][1]}.00000")
            scenario2 = ScenarioContainer([scenario2_car1_record, scenario2_car2_record])
            generation_similarity += calculate_individual_dist(scenario1, scenario2)

    generation_similarity /= (len(scenario_candidates)*(len(scenario_candidates)-1)/2)
    return generation_similarity
