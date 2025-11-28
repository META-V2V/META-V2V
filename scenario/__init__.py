import os
import json
from dataclasses import asdict, dataclass
from deap.base import Fitness
from config import HD_MAP
from scenario.ad_agents import ADAgent, ADSection
from scenario.pd_agents import PDAgent, PDSection
from scenario.traffic_light import TrafficSection
from scenario.fitness import SoundnessFitness, RobustnessFitness
from hdmap.parser import MapParser
import inspect

@dataclass
class Scenario:
    """
    Genetic representation of a scenario (individual)

    :param ADSection ad_section: section of chromosome
      describing ADS instances
    :param PDSection pd_section: section of chromosome
      describing pedestrians
    :param TrafficSection tl_section: section of chromosome
      describing traffic control configuration
    :param int gid: generation id, default to invalid -1
    :param int sid: scenario id, default to invalid -1
    :param int fid: follow-up id, default to invalid -1
    :param Fitness fitness: fitness function instance from deap.base.Fitness, default to None
    """
    ad_section: ADSection
    pd_section: PDSection
    tl_section: TrafficSection
    gid: int = -1
    sid: int = -1
    fid: int = -1

    def __post_init__(self):
        """
        because the python dataclass default factory field is not supported for NoneType and lack of dynamic assignment,
        we decide to use __post_init__ to set the individual's fitness value definition manually

        :main_soundness_ga.py: SoundnessFitness;
        :main_robustness_ga.py: RobustnessFitness;
        :other scripts: None;
        """
        self.fitness: Fitness = None       # default to None
        stack = inspect.stack()
        try:
            for frame in stack:
                if frame.filename.endswith(('main_soundness_ga.py', 'main_robustness_ga.py')):
                    script_name = os.path.basename(frame.filename)
                    if script_name == 'main_soundness_ga.py':
                        self.fitness: Fitness = SoundnessFitness()
                    elif script_name == 'main_robustness_ga.py':
                        self.fitness: Fitness = RobustnessFitness()
                    break
        except Exception as e:
            print(f'Error in __post_init__: {e}')
        finally:
            del stack

    def to_dict(self) -> dict:
        """
        Converts the chromosome to dict

        :returns: scenario in JSON format
        :rtype: dict
        """
        return {
            'ad_section': asdict(self.ad_section),
            'pd_section': asdict(self.pd_section),
            'tl_section': asdict(self.tl_section)
        }

    def to_json(self, file_path: str, name: str) -> bool:
        """
        Save the scenario to a file_path/name.json file

        :param str file_path: path to save the scenario
        :param str name: name of the scenario
        :returns: True if saved successfully, False otherwise
        :rtype: bool
        """
        dict_data = self.to_dict()
        dest_file = os.path.join(file_path, f'{name}.json')
        with open(dest_file, 'w') as fp:
            json.dump(dict_data, fp, indent=4)
        return True

    @staticmethod
    def from_json(json_file_path: str) -> 'Scenario':
        """
        Converts a JSON file into Scenario object

        :param str json_file_path: path to the JSON file
        :returns: Scenario instance
        :rtype: Scenario
        """
        with open(json_file_path, 'r') as fp:
            data = json.loads(fp.read())
            ad_section = data['ad_section']
            r_ad = ADSection([])
            for adc in ad_section['adcs']:
                r_ad.add_agent(
                    ADAgent(adc['routing'], adc['start_s'],
                            adc['dest_s'], adc['start_t'])
                )
            pd_section = data['pd_section']
            r_pd = PDSection([])
            for pd in pd_section['pds']:
                r_pd.add_agent(
                    PDAgent(pd['cw_id'], pd['speed'], pd['start_t'])
                )
            tl_section = data['tl_section']
            r_tl = TrafficSection([])
            for tl in tl_section['tls']:
                r_tl.add_tl(tl['tid'], tl['duration'], tl['delta_t'], tl['confidence'])
            return Scenario(r_ad, r_pd, r_tl)

    @staticmethod
    def get_one() -> 'Scenario':
        """
        Randomly generates a scenario using the representation

        :returns: randomlly generated scenario
        :rtype: Scenario
        """
        result = Scenario(
            ad_section=ADSection.get_one(),
            pd_section=PDSection.get_one(),
            tl_section=TrafficSection.generate_config()
        )
        return result

    @staticmethod
    def get_conflict_one() -> 'Scenario':
        """
        Randomly generates a scenario that gurantees at least
        2 ADS instances have conflicting trajectory

        :returns: randomly generated scenario with conflict
        :rtype: Scenario
        """
        while True:
            result = Scenario(
                ad_section=ADSection.get_one(),
                pd_section=PDSection.get_one(),
                tl_section=TrafficSection.generate_config()
            )
            if result.has_ad_conflict() > 0:
                return result

    @staticmethod
    def get_conflict_one_only_adc() -> 'Scenario':
        """
        Randomly generates a scenario that gurantees at least
        2 ADS instances have conflicting trajectory
        This version has only ADCs and traffic lightswithout pedestrains

        :returns: randomly generated scenario with conflict without PDs
        :rtype: Scenario
        """
        while True:
            result = Scenario(
                ad_section=ADSection.get_one(),
                pd_section=PDSection([]),
                tc_section=TrafficSection.generate_config()
            )
            if result.has_ad_conflict() > 0:
                return result

    def has_ad_conflict(self) -> int:
        """
        Check number of ADS instance pairs with conflict

        :returns: number of conflicts
        :rtype: int
        """
        ma = MapParser.get_instance(HD_MAP)
        conflict = set()
        for ad in self.ad_section.adcs:
            for bd in self.ad_section.adcs:
                if ad.routing == bd.routing:
                    continue
                if ma.is_conflict_lanes(ad.routing, bd.routing):
                    conflict.add(frozenset([ad.routing_str, bd.routing_str]))
        return len(conflict)
