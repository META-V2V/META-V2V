from typing import List, Dict, Tuple
from os.path import basename
import math
from cyber_record.record import Record
from google.protobuf.json_format import MessageToDict

class RecordContainer:
    """
    RecordContainer class to contain a car's localization data
    """
    id: str                   # the id of the vehicle in this scenario
    loc: List[Dict]           # the original localization data list
    loc_align: List[Dict]     # the aligned localization data list

    def __init__(self, record_file: str):
        """
        Constructor

        :param str record_file: the path of the record file
        """
    
        # get the id from the file name
        self.id = basename(record_file).split(".")[0].split("_")[-1]
        # initialize the localization list
        self.loc:List[Dict] = []
        # initialize the aligned localization list
        self.loc_align: List[Dict] = []
        # read the record file using cyber_record package
        record = Record(record_file)
        for topic, data, t in record.read_messages():
            # only read the localization data from the stream of localization topic
            if topic == "/apollo/localization/pose":
                # for convenience, convert the protobuf message to python dict
                data_dict = MessageToDict(data, preserving_proto_field_name=True)   # note that should preserve the proto field name
                self.loc.append(data_dict)

    def alignment(self, start_frame: int, end_frame: int):
        """
        Align the loc[] to loc_align[], slice from start_frame to end_frame

        :param int start_frame: the start frame of the alignment
        :param int end_frame: the end frame of the alignment
        """
        self.loc_align = []    # reset the loc_align[]
        if not self.loc:       # if the loc[] is empty, return
            return
        # two-pointer linear alignment to reduce complexity to O(N + T)
        n = len(self.loc)
        i = 0
        # vehicles cycle
        for t in range(start_frame, end_frame):
            target_time = t / 10
            # advance pointer while next timestamp is still <= target_time
            while i + 1 < n and self.loc[i + 1]['header']['timestamp_sec'] <= target_time:
                i += 1
            if i == n - 1:
                best_loc = self.loc[i]
            else:
                t_left = self.loc[i]['header']['timestamp_sec']
                t_right = self.loc[i + 1]['header']['timestamp_sec']
                # choose closer one between i and i+1
                if abs(t_left - target_time) <= abs(t_right - target_time):
                    best_loc = self.loc[i]
                else:
                    best_loc = self.loc[i + 1]
            self.loc_align.append(best_loc)
        # clear the original loc[]
        self.loc = []

class ScenarioContainer:
    """
    ScenarioContainer class to contain a scenario's all cars' RecordContainer

    car1: RecordContainer
    car2: RecordContainer
    """

    car1: RecordContainer
    car2: RecordContainer

    def __init__(self, record_list: List[str]):
        """
        Constructor

        :param List[str] record_list: the list of record files
        """
        self.car1 = RecordContainer(record_list[0])
        self.car2 = RecordContainer(record_list[1])
        time_low, time_high = self.get_time_range()
        # align the localization data of the two cars
        self.car1.alignment(time_low, time_high)
        self.car2.alignment(time_low, time_high)
    
    def get_time_range(self) -> Tuple[int, int]:
        """
        Get the time range of the two cars

        :return: the start frame and the end frame
        :rtype: Tuple[int, int]
        """
        # the latest start time and the earliest end time for common period
        start_time = max(self.car1.loc[0]['header']['timestamp_sec'], self.car2.loc[0]['header']['timestamp_sec'])
        end_time = min(self.car1.loc[-1]['header']['timestamp_sec'], self.car2.loc[-1]['header']['timestamp_sec'])
        # round to 0.1s
        start_time = round(start_time, 1)
        end_time = round(end_time, 1)
        start_frame = int(start_time * 10)
        end_frame = int(end_time * 10)
        return start_frame, end_frame
    
    def calculate_pair_distance(self) -> Tuple[float, int, int]:
        """
        Calculate the minimum distance between the two cars and the frame number of the minimum distance

        :return: the minimum distance, the frame number of the minimum distance, the length of the aligned localization data
        :rtype: Tuple[float, int, int]
        """

        # set the min squared distance to infinity
        min_dist_sq = float("inf")
        # set the frame value to invalid
        min_dist_frame = -1
        for t in range(len(self.car1.loc_align)):
            dx = self.car1.loc_align[t]['pose']['position']['x'] - self.car2.loc_align[t]['pose']['position']['x']
            dy = self.car1.loc_align[t]['pose']['position']['y'] - self.car2.loc_align[t]['pose']['position']['y']
            dist_sq = dx*dx + dy*dy
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                min_dist_frame = t
        return math.sqrt(min_dist_sq), min_dist_frame, len(self.car1.loc_align)  # note min_dist_frame is the pointer of the loc_align[]

    def get_interesting_trajectory(self, window=50):
        """
        Get the trajectory of the two cars before/after the minimum distance, default 50 frames, i.e. 5 seconds before + 5 seconds after

        :param int window: the window size, default 50 frames, i.e. 5 seconds before + 5 seconds after
        :return: the left pointer of the interesting trajectory, the right pointer of the interesting trajectory, the frame number of the minimum distance
        :rtype: Tuple[int, int, int]
        """

        # minimum distance, the frame number of the minimum distance, the length of the aligned localization data
        min_dist, min_dist_frame, len_loc_align = self.calculate_pair_distance()

        # the left pointer of the interesting trajectory
        start_frame = max(0, min_dist_frame - window)

        # the right pointer of the interesting trajectory, be careful with the offset +1 out of bound
        end_frame = min(len_loc_align, min_dist_frame + window)
        return start_frame, end_frame, min_dist_frame
