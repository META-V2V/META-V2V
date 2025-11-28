from scenario import Scenario
from scenario.scenario_runner import ScenarioRunner
from typing import Dict, Tuple

def min_distance(timestamp: str, ind: Scenario) -> float:
    """
    run the distinct scenario and return the polygonal distance between each adc pair

    :param str timestamp: timestamp of this runtime batch
    :param Scenario ind: The scenario individual to be evaluated
    :returns: the minimum distance of the scenario
    :rtype: float
    """
    g_name = f'Generation_{ind.gid:05}'
    s_name = f'Scenario_{ind.sid:05}'
    f_name = f'Follow_{ind.fid:05}'
    srunner = ScenarioRunner.get_instance()
    srunner.set_scenario(ind)
    srunner.init_scenario()
    runners = srunner.run_scenario(timestamp, g_name, s_name, f_name, True)
    min_distances: Dict[Tuple[int, int], float] = srunner.min_distances
    for pair in min_distances:
        min_distances[pair] = round(min_distances[pair], 2)
    return min(min_distances.values())
