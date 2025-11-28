from hdmap.parser import MapParser
from apollo.utils import PositionEstimate
from modules.localization.proto.localization_pb2 import LocalizationEstimate
from shapely.geometry import Point
from config import HD_MAP
from shapely.geometry import LineString

def loc_to_pos(loc: LocalizationEstimate) -> PositionEstimate:
    """
    Convert the LocalizationEstimate object to PositionEstimate object

    [New feature] can be used for the future work
    :param LocalizationEstimate loc: The current localization of the ADC
    :returns: The converted PositionEstimate object
    :rtype: PositionEstimate
    """
    if loc is None:
        return PositionEstimate(lane_id=None, s=None)
    point = Point(loc.pose.position.x, loc.pose.position.y)
    mp = MapParser.get_instance(HD_MAP)
    lane_ids = mp.get_lanes()                        # List[lane_ids]
    rt_pos = PositionEstimate(lane_id=None, s=None)  # the value to be returned
    min_dist = float('inf')
    for lane_id in lane_ids:
        # traverse each lane, find the closest lane
        central_line = mp.get_lane_central_curve(lane_id)
        distance = central_line.distance(point)
        if distance < min_dist:
            min_dist = distance
            rt_pos.lane_id = lane_id
    if lane_id is None:
        return rt_pos
    # get the closest lane central line
    lane_central_line = mp.get_lane_central_curve(rt_pos.lane_id)
    segments = list(map(LineString, zip(lane_central_line.coords[:-1], lane_central_line.coords[1:])))
    sorted_segments = sorted(segments, key=lambda x: point.distance(x))
    closest_segment = sorted_segments[0]
    pos = segments.index(closest_segment)
    # find the position in segments
    s = 0
    for i in range(pos):
        # accumulate the length of the previous segments
        s += segments[i].length
    # accumulate the length of the current segment
    cur_seg_start = Point(segments[pos].coords[0])
    # find the start point of the current segment
    s += cur_seg_start.distance(point)
    # accumulate the length of the current segment
    rt_pos.s = round(s, 1)
    return rt_pos
