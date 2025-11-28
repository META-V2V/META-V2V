from copy import deepcopy
from random import randint, random, sample, shuffle
from typing import List, Tuple
from scenario import Scenario
from scenario.ad_agents import ADAgent, ADSection
from scenario.pd_agents import PDSection
from scenario.traffic_light import TrafficSection, TLConfig
from config import MAX_ADC_COUNT, MAX_PD_COUNT, HD_MAP
from hdmap.parser import MapParser

def cx_ad_section(ind1: ADSection, ind2: ADSection) -> Tuple[ADSection, ADSection]:
    """
    crossover the ad section of the two individuals

    :param ADSection ind1: the ad section of the first individual
    :param ADSection ind2: the ad section of the second individual
    :returns: the crossover ad section of the two individuals
    :rtype: Tuple[ADSection, ADSection]
    """
    cx_pb = random()
    # swap entire ad section with 5% probability
    if cx_pb < 0.05:
        return ind2, ind1
    cxed = False

    for adc1 in ind1.adcs:
        for adc2 in ind2.adcs:
            if adc1.routing_str == adc2.routing_str:
                # same routing in both parents
                # swap start_s or start_t with 50% probability
                if random() < 0.5:
                    adc1.start_s = adc2.start_s
                else:
                    adc1.start_t = adc2.start_t
                cxed = True
    if cxed:
        ind1.adjust_time()
        return ind1, ind2

    if len(ind1.adcs) < MAX_ADC_COUNT:
        for adc in ind2.adcs:
            if ind1.has_conflict(adc) and ind1.add_agent(deepcopy(adc)):
                # add an agent from parent 2 to parent 1 if there exists a conflict
                ind1.adjust_time()
                return ind1, ind2

    # if none of the above happened, no common adc, no conflict in either
    # combine to make a new populations
    available_adcs = ind1.adcs + ind2.adcs
    shuffle(available_adcs)
    split_index = randint(2, min(len(available_adcs), MAX_ADC_COUNT))
    result1 = ADSection([])
    for x in available_adcs[:split_index]:
        result1.add_agent(deepcopy(x))

    # make sure offspring adc count is valid
    while len(result1.adcs) > MAX_ADC_COUNT:
        result1.adcs.pop()
    trial = 0
    while len(result1.adcs) < 2:
        new_ad = ADAgent.get_one(trial < 15)
        if result1.has_conflict(new_ad) and result1.add_agent(new_ad):
            break
        elif trial > 15 and result1.add_agent(new_ad):
            break
        trial += 1
    result1.adjust_time()
    return result1, ind2

def cx_pd_section(ind1: PDSection, ind2: PDSection) -> Tuple[PDSection, PDSection]:
    """
    crossover the pd section of the two individuals

    :param PDSection ind1: the pd section of the first individual
    :param PDSection ind2: the pd section of the second individual
    :returns: the crossover pd section of the two individuals
    :rtype: Tuple[PDSection, PDSection]
    """
    cx_pb = random()
    if cx_pb < 0.1:
        # swap entire pd section with 10% probability
        return ind2, ind1

    available_pds = ind1.pds + ind2.pds
    result1 = PDSection(
        sample(available_pds, k=randint(0, min(MAX_PD_COUNT, len(available_pds)))))
    result2 = PDSection(
        sample(available_pds, k=randint(0, min(MAX_PD_COUNT, len(available_pds)))))
    return result1, result2

def cx_tl(ind1: TrafficSection, ind2: TrafficSection) -> Tuple[TrafficSection, TrafficSection]:
    """
    crossover the traffic section of the two individuals once

    :param TrafficSection ind1: the traffic section of the first individual
    :param TrafficSection ind2: the traffic section of the second individual
    :returns: the crossover traffic section of the two individuals
    :rtype: Tuple[TrafficSection, TrafficSection]
    """
    mp = MapParser.get_instance(HD_MAP)
    signals = list(mp.get_signals())
    # randomly select a signal light for crossover
    index = randint(0, len(ind1.tls) - 1)
    eq_list = list()
    ne_list = list()
    for sig in ind1.tls[index].get_eq():
        if sig in signals:
            eq_list.append(sig)
    for sig in ind1.tls[index].get_ne():
        if sig in signals:
            ne_list.append(sig)
    # the exchange signal light is composed of the source signal light, the equivalent signal light, and the conflicting signal light
    exchange_list = [ind1.tls[index].tid] + eq_list + ne_list
    exchange_set = set(exchange_list)

    exchange_1: List[TLConfig] = []
    no_change_1: List[TLConfig] = []
    exchange_2: List[TLConfig] = []
    no_change_2: List[TLConfig] = []
    for tl in ind1.tls:
        if tl.tid in exchange_set:
            exchange_1.append(tl)
        else:
            no_change_1.append(tl)
    for tl in ind2.tls:
        if tl.tid in exchange_set:
            exchange_2.append(tl)
        else:
            no_change_2.append(tl)

    assert set([tl.tid for tl in exchange_1]) == set([tl.tid for tl in exchange_2]), "the exchange signal light is not consistent"
    assert set([tl.tid for tl in no_change_1]) == set([tl.tid for tl in no_change_2]), "the unchanged signal light is not consistent"
    tls_1 = exchange_2 + no_change_1
    tls_2 = exchange_1 + no_change_2
    ind1.tls = tls_1
    ind2.tls = tls_2
    assert set([tl.tid for tl in ind1.tls]) == set([tl.tid for tl in ind2.tls]), "the number of signal lights after crossover is not consistent"
    return ind1, ind2

def cx_tl_section(ind1: TrafficSection, ind2: TrafficSection) -> Tuple[TrafficSection, TrafficSection]:
    """
    crossover the traffic section of the two individuals several times randomly

    :param TrafficSection ind1: the traffic section of the first individual
    :param TrafficSection ind2: the traffic section of the second individual
    :returns: the crossover traffic section of the two individuals
    :rtype: Tuple[TrafficSection, TrafficSection]
    """
    cx_pb = random()
    if cx_pb < 0.3:
        # crossover the traffic section of the two individuals twice with 30% probability
        ind1, ind2 = cx_tl(ind1, ind2)
        ind1, ind2 = cx_tl(ind1, ind2)
    elif cx_pb < 0.6:
        # crossover the traffic section of the two individuals once with 30% probability
        ind1, ind2 = cx_tl(ind1, ind2)
    # do not crossover with 40% probability
    return ind1, ind2

def cx_scenario(ind1: Scenario, ind2: Scenario) -> Tuple[Scenario, Scenario]:
    """
    crossover the scenario of the two individuals

    :param Scenario ind1: the scenario of the first individual
    :param Scenario ind2: the scenario of the second individual
    :returns: the crossover scenario of the two individuals
    :rtype: Tuple[Scenario, Scenario]
    """
    cx_pb = random()
    if cx_pb < 0.6:
        # crossover the ad section of the two individuals with 60% probability
        ind1.ad_section, ind2.ad_section = cx_ad_section(
            ind1.ad_section, ind2.ad_section
        )
    elif cx_pb < 0.8:
        # crossover the pd section of the two individuals with 20% probability
        ind1.pd_section, ind2.pd_section = cx_pd_section(
            ind1.pd_section, ind2.pd_section
        )
    else:
        # crossover the tl section of the two individuals with 20% probability
        ind1.tl_section, ind2.tl_section = cx_tl_section(
            ind1.tl_section, ind2.tl_section
        )
    return ind1, ind2
