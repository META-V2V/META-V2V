from broker import MessageBroker
from broker.radius import RadiusBroker
from broker.latency import LatencyBroker
from broker.noise import NoiseBroker
from broker.intermittence import IntermittenceBroker
from typing import Any

class BrokerFactory:
    """
    A Factory Method to produce MessageBroker and its corresponding subclasses, dynamically

    :param str mode: working mode, to create different brokers:{MessageBroker, RadiusBroker, LatencyBroker, NoiseBroker, IntermittenceBroker}
    :param Any param: parameter for the message brokers
    """
    mode: str
    param: Any

    _instance = None

    def __new__(cls):
        """
        This class is a Singleton Design Pattern, override the .__new__()
        """
        if cls._instance is None:
            cls._instance = super(BrokerFactory, cls).__new__(cls)
            cls._instance.__initialized = False
        return cls._instance

    def __init__(self) -> None:
        """
        Constructor
        """
        # The reason why using self.__initialized: bool is self.__new__() for Singleton Design Pattern 
        if not self.__initialized:
            self.mode = None
            self.param = None
            self.__initialized = True

    def set_mode(self, mode: str) -> None:
        """
        Set the property mode in BrokerFactory
        
        param str mode: Command the working mode for Broker
        """
        if mode not in ('MessageBroker', 'RadiusBroker', 'LatencyBroker', 'NoiseBroker', 
                        'IntermittenceBroker'):
            raise ValueError("Unexpected mode in BrokerFactory")
        self.mode = mode

    def set_param(self, param: float) -> None:
        """
        Set the property param in BrokerFactory

        param float param: parameter for the Broker
        """
        self.param = param

    def reset(self) -> None:
        """
        Reset all properties to None
        """
        self.mode = None
        self.param = None

    def createbk(self, runners) -> MessageBroker:
        """
        Create the concrete Broker

        param: List[ApolloRunner] runners: runners passed to Brokers
        returns: a distinct Broker
        rtype: MessageBroker or one of its subclasses
        """
        if self.mode == 'MessageBroker':
            return MessageBroker(runners)
        elif self.mode == 'RadiusBroker':
            return RadiusBroker(runners, self.param)
        elif self.mode == 'LatencyBroker':
            return LatencyBroker(runners, self.param)
        elif self.mode == 'NoiseBroker':
            return NoiseBroker(runners, self.param, 0, 0, 0)
        elif self.mode == 'IntermittenceBroker':
            return IntermittenceBroker(runners, self.param)
        else:
            raise ValueError("Unexpected mode in BrokerFactory")
