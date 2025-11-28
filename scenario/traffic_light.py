from dataclasses import dataclass
from typing import List
from time import time
import random
from hdmap.parser import MapParser
from config import HD_MAP, FORCE_INVALID_TRAFFIC_CONTROL
from modules.perception.proto.traffic_light_detection_pb2 import (
    TrafficLight, TrafficLightDetection)

@dataclass
class TLConfig:
    """
    Genetic representation of a single traffic signal,
    we've redesigned this part coz the original DoppelTest TCSection can change the signal color only once
    the rewrite one can change the signal using time cycle, which is more flexible and realistic so that it 
    can support longer scenarios in the future

    :param str tid: the ID of the traffic signal
    :param List[float] duration: the duration seconds of each color of the traffic signal, in order g, y, r
    :param float delta_t: the time offset of the traffic signal from the start of the scenario
    :param float confidence: the confidence of the traffic signal
    """
    tid: str
    duration: List[float]
    delta_t: float
    confidence: float = 1.0

    @staticmethod
    def get_one(tid) -> 'TLConfig':
        """
        Generate a random TLConfig instance
        hyperparameters currently used: green light duration: 5-10s, yellow light duration: 2s,
        red light duration: 3-5s, offset: 0-10s

        :param str tid: traffic signal id
        :returns: random TLConfig instance
        :rtype: TLConfig
        """
        result = TLConfig(
            tid = tid,
            duration=[random.uniform(5,10), 2.0, random.uniform(3,5)],
            delta_t = random.uniform(0, 10)
        )
        return result

    def generate_sync(self, tid) -> 'TLConfig':
        """
        Generate a TLConfig instance with the same duration as self
        this method will be used to generate a 'EQ' signal, which means the signal is the same as self

        :param str tid: traffic signal id
        :returns: TLConfig instance with the same duration as self
        :rtype: TLConfig
        """
        result = TLConfig(
            tid = tid,
            duration=self.duration,
            delta_t = self.delta_t)
        return result

    def generate_exclusion(self, tid) -> 'TLConfig':
        """
        Generate a TLConfig instance with the 'Orthogonal' duration as self
        this method will be used to generate an 'NE' signal

        :param str tid: traffic signal id
        :returns: TLConfig instance with the exclusion duration as self
        :rtype: TLConfig
        """
        result = TLConfig(
            tid = tid,
            duration=[self.duration[2]-self.duration[1], self.duration[1], self.duration[0]+self.duration[1]],
            delta_t = self.delta_t + self.duration[2])
        # This part is challenging - the assignment logic for orthogonal signals requires knowledge of modular arithmetic from number theory
        # Special attention needs to be paid to the handling of delta_t
        # Because the generated mutually exclusive signal has the normal sequence of red-green-yellow, we need to add self.duration['RED'] to fix delta_t
        # This ensures that the generated traffic light timing is correct and truly orthogonal to the original signal
        # This algorithm can be verified by a test script
        return result

    def color(self, t: float) -> str:
        """
        Get the color of the traffic signal at time t

        :param float t: time
        :returns: color of the traffic signal at time t
        :rtype: str
        """
        if sum(self.duration) == 0:
            return 'GREEN'

        cur_t = t + self.delta_t
        mod = cur_t % sum(self.duration)
        if mod < self.duration[0]:
            # Pay attention to boundary values - they cannot be equal, otherwise errors will occur.
            # See boundary value issues related to modular arithmetic in cyclic periods
            return 'GREEN'
        elif mod < self.duration[0] + self.duration[1]:
            # Pay attention to boundary values - they cannot be equal, otherwise errors will occur.
            # See boundary value issues related to modular arithmetic in cyclic periods
            return 'YELLOW'
        else:
            return 'RED'

    def get_eq(self):
        """
        Get all equivalent traffic signal IDs
        Use yield statement as Generator
        """
        ma = MapParser.get_instance(HD_MAP)
        relevant = ma.get_signals_wrt(self.tid)
        for sig, cond in relevant:
            if cond == 'EQ':
                yield sig
    
    def get_ne(self):
        """
        Get all non-equivalent traffic signal IDs
        Use yield statement as Generator
        """
        ma = MapParser.get_instance(HD_MAP)
        relevant = ma.get_signals_wrt(self.tid)
        for sig, cond in relevant:
            if cond == 'NE':
                yield sig

@dataclass
class TrafficSection:
    """
    Genetic representation of the traffic section

    :param List[TLConfig] tls: list of traffic signal representations
    :param int sequence_num: the sequence number of the traffic section
    """

    tls: List[TLConfig]
    sequence_num: int = 0

    @staticmethod
    def generate_config() -> 'TrafficSection':
        """
        Generate a random TrafficSection instance

        :returns: a random TrafficSection instance
        :rtype: TrafficSection
        """
        result = list()
        mp = MapParser.get_instance(HD_MAP)
        signals = list(mp.get_signals())
        random.shuffle(signals)
        # get a random signal sequence, which is a list of TLConfig instances

        while len(signals) > 0:
            curr_sig = signals.pop()
            tl = TLConfig.get_one(curr_sig)
            result.append(tl)
            for sig in tl.get_eq():
                # Set equavalent TL
                if sig in signals:
                    signals.remove(sig)
                    result.append(tl.generate_sync(sig))
            for sig in tl.get_ne():
                # Set mutual exclusion TL
                if sig in signals:
                    signals.remove(sig)
                    result.append(tl.generate_exclusion(sig))
        
        return TrafficSection(tls=result)

    def add_tl(self, tid: str, duration: List[float], delta_t: float, confidence:float=1.0) -> None:
        """
        Add a TLConfig instance to the TrafficSection

        [WARNING] This method cannot be used alone, otherwise it will cause traffic signal order errors.
          It can only be used when used in JSON files
        :param str tid: traffic signal id
        :param List[float] duration: the duration of each color of the traffic signal, in order g, y, r
        :param float delta_t: the time offset of the traffic signal
        :param float confidence: the confidence of the traffic signal, default to 1.0
        """
        self.tls.append(TLConfig(tid=tid, duration=duration, delta_t=delta_t, confidence=confidence))

    def detection(self, curr_t: float) -> TrafficLightDetection:
        """
        Generate a TrafficLightDetection message object based on the current time

        :param float curr_t: current time
        :returns: TrafficLightDetection message object to be sent
        :rtype: TrafficLightDetection
        """

        tld = TrafficLightDetection()
        tld.header.timestamp_sec = time()
        tld.header.module_name = "MAGGIE"
        tld.header.sequence_num = self.sequence_num
        self.sequence_num += 1

        for k in self.tls:
            tl = tld.traffic_light.add()
            tl.id = k.tid
            tl.confidence = k.confidence
            cl = k.color(curr_t)
            if cl == 'GREEN' or FORCE_INVALID_TRAFFIC_CONTROL:
                tl.color = TrafficLight.GREEN
            elif cl == 'YELLOW':
                tl.color = TrafficLight.YELLOW
            elif cl == 'RED':
                tl.color = TrafficLight.RED
            else:
                tl.color = TrafficLight.UNKNOWN

        return tld
