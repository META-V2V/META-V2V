from random import randint, random, shuffle
from scenario import Scenario
from scenario.ad_agents import ADAgent, ADSection
from scenario.pd_agents import PDAgent, PDSection
from scenario.traffic_light import TLConfig, TrafficSection
from config import MAX_ADC_COUNT, MAX_PD_COUNT, HD_MAP
from hdmap.parser import MapParser
from typing import List, Tuple

def mut_ad_section(ind: ADSection) -> ADSection:
    """
    mutate the ad section of the individual

    :param ADSection ind: the ad section of the individual
    :returns: the mutated ad section of the individual
    :rtype: ADSection
    """
    mut_pb = random()
    # remove a random adc with 10% probability
    if mut_pb < 0.1 and len(ind.adcs) > 2:
        shuffle(ind.adcs)
        ind.adcs.pop()
        ind.adjust_time()
        return ind

    # add a random adc with 30% probability
    trial = 0
    if mut_pb < 0.4 and len(ind.adcs) < MAX_ADC_COUNT:
        while True:
            new_ad = ADAgent.get_one(trial < 15)
            if ind.has_conflict(new_ad) and ind.add_agent(new_ad):
                break
            elif trial > 15 and ind.add_agent(new_ad):
                break
            trial += 1
        ind.adjust_time()
        return ind

    # mutate a random agent
    index = randint(0, len(ind.adcs) - 1)
    routing = ind.adcs[index].routing
    original_adc = ind.adcs.pop(index)
    mut_counter = 0
    while True:
        if ind.add_agent(ADAgent.get_one_for_routing(routing)):
            break
        mut_counter += 1
        if mut_counter == 5:
            ind.add_agent(original_adc)
            break
    ind.adjust_time()
    return ind

def mut_pd_section(ind: PDSection) -> PDSection:
    """
    mutate the pd section of the individual

    :param PDSection ind: the pd section of the individual
    :returns: the mutated pd section of the individual
    :rtype: PDSection
    """
    if len(ind.pds) == 0:
        # if there is no pd, add a random pd
        ind.add_agent(PDAgent.get_one())
        return ind

    mut_pb = random()
    # remove a random pd with 20% probability
    if mut_pb < 0.2 and len(ind.pds) > 0:
        shuffle(ind.pds)
        ind.pds.pop()
        return ind

    # add a random pd with 20% probability
    if mut_pb < 0.4 and len(ind.pds) <= MAX_PD_COUNT:
        ind.pds.append(PDAgent.get_one())
        return ind

    # mutate a random pd with 60% probability
    index = randint(0, len(ind.pds) - 1)
    ind.pds[index] = PDAgent.get_one_for_cw(ind.pds[index].cw_id)
    return ind

def mut_tl(ind: TrafficSection) -> TrafficSection:
    """
    mutate the traffic section of the individual once

    :param TrafficSection ind: the traffic section of the individual
    :returns: the mutated traffic section of the individual
    :rtype: TrafficSection
    """
    mp = MapParser.get_instance(HD_MAP)
    signals = list(mp.get_signals())
    # randomly select a signal light for mutation
    index = randint(0, len(ind.tls) - 1)
    original_tl = ind.tls.pop(index)
    mut_id = original_tl.tid
    # collect the equivalent and conflicting signal light ids
    eq_list: List[str] = list()
    for sig in original_tl.get_eq():
        if sig in signals:
            eq_list.append(sig)
    ne_list: List[str] = list()
    for sig in original_tl.get_ne():
        if sig in signals:
            ne_list.append(sig)
    # remove the equivalent and conflicting signal lights
    for tl_config in ind.tls:
        if tl_config.tid in eq_list or tl_config.tid in ne_list:
            ind.tls.remove(tl_config)
    # replace original_tl
    new_tl = TLConfig.get_one(mut_id)
    ind.tls.append(new_tl)
    # replace the equivalent and conflicting signal lights
    for sig in eq_list:
        ind.tls.append(new_tl.generate_sync(sig))
    for sig in ne_list:
        ind.tls.append(new_tl.generate_exclusion(sig))
    return ind

def mut_tl_section(ind: TrafficSection) -> TrafficSection:
    """
    mutate the traffic section of the individual several times randomly

    :param TrafficSection ind: the traffic section of the individual
    :returns: the mutated traffic section of the individual
    :rtype: TrafficSection
    """
    mut_pb = random()
    if mut_pb < 0.3:
        # mutate the traffic section of the individual twice with 30% probability
        mut_tl(ind)
        mut_tl(ind)
    if mut_pb < 0.6:
        # mutate the traffic section of the individual once with 30% probability
        mut_tl(ind)
    # do not mutate with 40% probability
    return ind

def mut_scenario(ind: Scenario) -> Tuple[Scenario]:
    """
    mutate the scenario of the individual

    :param Scenario ind: the scenario of the individual
    :returns: the mutated scenario of the individual
    :rtype: Tuple[Scenario]
    """
    mut_pb = random()
    if mut_pb < 0.3:
        # mutate the ad section of the individual with 30% probability
        ind.ad_section = mut_ad_section(ind.ad_section)
    elif mut_pb < 0.6:
        # mutate the pd section of the individual with 30% probability
        ind.pd_section = mut_pd_section(ind.pd_section)
    else:
        # mutate the tl section of the individual with 40% probability
        ind.tl_section = mut_tl_section(ind.tl_section)
    return ind,
