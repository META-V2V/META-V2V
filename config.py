import logging
from pathlib import Path

######################## APOLLO CONFIGURATION #########################

PERCEPTION_FREQUENCY = 25
"""Rate at which the Message Broker publishes perception messages"""
APOLLO_VEHICLE_LENGTH = 4.933
"""Length of default Apollo vehicle"""
APOLLO_VEHICLE_WIDTH = 2.11
"""Width of default Apollo vehicle"""
APOLLO_VEHICLE_HEIGHT = 1.48
"""Height of default Apollo vehicle"""
APOLLO_VEHICLE_back_edge_to_center = 1.043
"""Length between the back edge and the center of default Apollo vehicle"""

######################## DIRECTORIES #########################

MT_ROOT = Path(__file__).parent
"""Root directory of Meta-V2V"""
APOLLO_ROOT = f'{MT_ROOT}/BaiduApollo'
"""Root directory of Apollo 7.0"""
RECORDS_DIR = f'{MT_ROOT}/records'
"""Desired directory to save record files"""

######################## SCENARIO CONFIGURATION #########################

STREAM_LOGGING_LEVEL = logging.INFO
"""Global logging level"""
USE_SIM_CONTROL_STANDALONE = True
"""Whether you wish to use extracted SimControl when executing scenario"""
FORCE_INVALID_TRAFFIC_CONTROL = False
"""Whether you wish to force invalid traffic cnotrol (e.g., every signal being green)"""
SCENARIO_UPPER_LIMIT = 30
"""The length of each scenario (in seconds)"""
INSTANCE_MAX_WAIT_TIME = 15
"""The maximum time before the last ADS instance starts moving"""
MAX_ADC_COUNT = 5
"""Number of ADS instances you wish to run simultaneously"""
MAX_PD_COUNT = 5
"""Number of pedestrians you wish to include in simulations"""
RUN_FOR_HOUR = 24
"""Number of hours you wish to run"""
HD_MAP = 'borregas_ave'
"""The HD map you are currently using"""
# :note: you also need to update ``apollo/modules/common/data/global_flagfile.txt``
#   to match the HD map you are using
# [Todo] We are going to use an auto-update script to update the global flagfile.txt

######################## GA CONFIGURATION #########################

POP_SIZE = 30
"""Population size for the genetic algorithm"""
STAGE1 = 5
"""Maximum number of generations in the first stage"""

######################## BROKER CONFIGURATION #########################

BK_PARAM_MAP = {
    'RadiusBroker': [100, 80, 60, 40, 20, 10, 5],
    'DelayBroker': [0.2, 0.4, 0.8, 1.0],
    'NoiseBroker': [0.5, 1.0, 2.0, 4.0, 6.0, 8.0, 10.0],
    'IntermittentBroker': [0.05, 0.1, 0.15, 0.2, 0.25, 0.5]
}
