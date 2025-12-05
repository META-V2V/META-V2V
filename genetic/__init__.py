from scenario import Scenario
from scenario.scenario_runner import ScenarioRunner
from typing import Dict, Tuple
from config import RECORDS_DIR, HD_MAP
from hdmap.parser import MapParser
from doppeltest.ViolationTracker import ViolationTracker
from doppeltest import RecordAnalyzer
import os

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

def eval_scenario_doppeltest(ind: Scenario, timestamp: str):
    """
    DoppelTest fitness function for comparision
    """
    g_name = f'Generation_{ind.gid:05}'
    s_name = f'Scenario_{ind.sid:05}'
    f_name = f'Follow_{ind.fid:05}'

    srunner = ScenarioRunner.get_instance()
    srunner.set_scenario(ind)
    srunner.init_scenario()
    runners = srunner.run_scenario(g_name, s_name, f_name, True)

    min_distances: Dict[Tuple[int, int], float] = srunner.min_distances
    for pair in min_distances:
        min_distances[pair] = round(min_distances[pair], 2)

    obs_routing_map = dict()
    for a, r in runners:
        obs_routing_map[a.nid] = r.routing_str

    unique_violation = 0
    decisions = set()
    for a, r in runners:
        decisions.update(a.get_decisions())
        c_name = a.container.container_name
        r_name = f"{c_name}.{f_name}.00000"
        record_path = os.path.join(RECORDS_DIR, timestamp, g_name, s_name, f_name, r_name)
        ra = RecordAnalyzer(record_path)
        ra.analyze()
        for v in ra.get_results():
            main_type = v[0]
            sub_type = v[1]
            if main_type == 'collision':
                if sub_type < 100:
                    # pedestrian collisoin
                    related_data = frozenset(
                        [r.routing_str, ind.pd_section.pds[sub_type].cw_id])
                    sub_type = 'A&P'
                else:
                    # adc to adc collision
                    related_data = frozenset(
                        [r.routing_str, obs_routing_map[sub_type]]
                    )
                    sub_type = 'A&A'
            else:
                related_data = r.routing_str
            if ViolationTracker.get_instance().add_violation(
                gname=g_name,
                sname=s_name,
                record_file=record_path,
                mt=main_type,
                st=sub_type,
                data=related_data
            ):
                unique_violation += 1

    ma = MapParser.get_instance(HD_MAP)
    conflict = ind.has_ad_conflict()

    # if unique_violation == 0:
    #     # no unique violation, remove records
    #     remove_record_files(g_name, s_name)
    #     pass

    return min(min_distances.values()), len(decisions), conflict, unique_violation
