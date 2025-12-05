import glob
import math
import os
import subprocess
import time
import fcntl
from pathlib import Path
from dataclasses import dataclass
from typing import List, Set, Tuple
from shapely.geometry import LineString, Polygon
from config import (APOLLO_ROOT, APOLLO_VEHICLE_HEIGHT, APOLLO_VEHICLE_LENGTH,
                    APOLLO_VEHICLE_WIDTH, HD_MAP,
                    APOLLO_VEHICLE_back_edge_to_center)
from hdmap.parser import MapParser
from modules.common.proto.geometry_pb2 import Point3D
from modules.localization.proto.localization_pb2 import LocalizationEstimate
from modules.map.proto.map_lane_pb2 import Lane, LaneBoundary
from modules.perception.proto.perception_obstacle_pb2 import PerceptionObstacle
from modules.planning.proto.planning_pb2 import ADCTrajectory

@dataclass
class PositionEstimate:
    """
    Class representing a location on a HD Map

    :param str lane_id: id of the lane on a HD Map
    :param float s: distance from the start of the lane
    """
    lane_id: str
    s: float

    def is_too_close(self, rhs) -> bool:
        """
        Check if 2 PositionEstimate objects are too close to each other. 
        They are too close if their distance is less than 5 meters.

        :param PositionEstimate rhs: right hand side object for comparison
        :returns: True if too close, False otherwise
        :rtype: bool
        """
        # 2 vehicles are too close if their distance is less than 5 meters
        ma = MapParser.get_instance(HD_MAP)
        adc1 = generate_adc_polygon(
            *ma.get_coordinate_and_heading(self.lane_id, self.s))
        adc2 = generate_adc_polygon(
            *ma.get_coordinate_and_heading(rhs.lane_id, rhs.s))
        
        adc1p = Polygon([[x.x, x.y] for x in adc1])
        adc2p = Polygon([[x.x, x.y] for x in adc2])

        return adc1p.distance(adc2p) < 5

def pos_estimate_eq_loc_estimate(pos: PositionEstimate, loc: LocalizationEstimate, 
                                tolerance:float=0.1) -> bool:
    """
    Compare a PositionEstimate object with a LocalizationEstimate object
    Judge if they are the same location

    :param PositionEstimate pos: PositionEstimate object
    :param LocalizationEstimate loc: LocalizationEstimate object
    :param float tolerance: tolerance for PE & LE 'equal' comparison
    :returns: True if they are the same, False otherwise
    :rtype: bool
    """
    ma = MapParser.get_instance(HD_MAP)
    pos_coord, pos_heading = ma.get_coordinate_and_heading(pos.lane_id, pos.s)
    loc_coord = loc.pose.position
    loc_heading = loc.pose.heading
    if abs(pos_coord.x-loc_coord.x) <= tolerance and abs(pos_coord.y-loc_coord.y <= tolerance):
        return True
    return False

def generate_polygon(position: Point3D, theta: float, length: float, width: float) -> List[Point3D]:
    """
    Generate polygon for a perception obstacle

    :param Point3D position: the position of the obstacle
    :param float theta: the heading of the obstacle
    :param float length: the length of the obstacle
    :param float width: the width of the obstacle
    :returns: List with 4 Point3D objects representing the polygon of the obstacle
    :rtype: List[Point3D]
    """
    points = []
    half_l = length / 2.0
    half_w = width / 2.0
    sin_h = math.sin(theta)
    cos_h = math.cos(theta)
    vectors = [(half_l * cos_h - half_w * sin_h,
                half_l * sin_h + half_w * cos_h),
               (-half_l * cos_h - half_w * sin_h,
                - half_l * sin_h + half_w * cos_h),
               (-half_l * cos_h + half_w * sin_h,
                - half_l * sin_h - half_w * cos_h),
               (half_l * cos_h + half_w * sin_h,
                half_l * sin_h - half_w * cos_h)]
    for x, y in vectors:
        p = Point3D()
        p.x = position.x + x
        p.y = position.y + y
        p.z = position.z
        points.append(p)
    return points

def generate_adc_polygon(position: Point3D, theta: float) -> List[Point3D]:
    """
    Generate a polygon for the ADC based on its current position

    :param Point3D position: position of the ADC
    :param float theta: the heading of the ADC (in radians)
    :returns: a list consisting 4 Point3D objects to represent ADC polygon
    :rtype: List[Point3D]
    """
    points = []
    half_w = APOLLO_VEHICLE_WIDTH / 2.0
    front_l = APOLLO_VEHICLE_LENGTH - APOLLO_VEHICLE_back_edge_to_center
    back_l = -1 * APOLLO_VEHICLE_back_edge_to_center
    sin_h = math.sin(theta)
    cos_h = math.cos(theta)
    vectors = [(front_l * cos_h - half_w * sin_h,
                front_l * sin_h + half_w * cos_h),
               (back_l * cos_h - half_w * sin_h,
                back_l * sin_h + half_w * cos_h),
               (back_l * cos_h + half_w * sin_h,
                back_l * sin_h - half_w * cos_h),
               (front_l * cos_h + half_w * sin_h,
                front_l * sin_h - half_w * cos_h)]
    for x, y in vectors:
        p = Point3D()
        p.x = position.x + x
        p.y = position.y + y
        p.z = position.z
        points.append(p)
    return points

def generate_adc_rear_vertices(position: Point3D, theta: float) -> List[Point3D]:
    """
    Generate the rear edge for the ADC

    :param Point3D position: position of the ADC
    :param float theta: heading of the ADC
    :returns: a list consisting 2 Point3D objects to represent the rear edge of the ADC
    :rtype: List[Point3D]
    """
    points = []
    half_w = APOLLO_VEHICLE_WIDTH / 2.0
    back_l = -1 * APOLLO_VEHICLE_back_edge_to_center
    sin_h = math.sin(theta)
    cos_h = math.cos(theta)
    vectors = [(back_l * cos_h - half_w * sin_h,
                back_l * sin_h + half_w * cos_h),
               (back_l * cos_h + half_w * sin_h,
                back_l * sin_h - half_w * cos_h)]

    for x, y in vectors:
        p = Point3D()
        p.x = position.x + x
        p.y = position.y + y
        p.z = position.z
        points.append(p)
    return points

def obstacle_to_polygon(obs: PerceptionObstacle) -> Polygon:
    """
    Constructs a polygon for an obstacle

    :param PerceptionObstacle obs: the perception obstacle protobuf message
    :returns: a Polygon object representing the obstacle
    :rtype: Polygon
    """
    return Polygon([[p.x, p.y] for p in obs.polygon_point])

def pedestrian_location_to_obstacle(_id: int, speed: float, loc: Point3D, heading: float) -> PerceptionObstacle:
    """
    Constructs a perception obstacle message for a pedestrian

    :param int _id: ID of the obstacle
    :param float speed: speed of the obstacle
    :param Point3D loc: location of the obstacle
    :param float heading: heading of the obstacle
    :returns: a PerceptionObstacle protobuf message ready to be published to cyberRT
    :rtype: PerceptionObstacle
    """
    position = Point3D(x=loc.x,
                       y=loc.y, z=loc.z)
    velocity = Point3D(x=math.cos(heading) * speed,
                       y=math.sin(heading) * speed, z=0.0)
    obs = PerceptionObstacle(
        id=_id,
        position=position,
        theta=heading,
        velocity=velocity,
        acceleration=Point3D(x=0, y=0, z=0),
        length=0.3,
        width=0.5,
        height=1.75,
        type=PerceptionObstacle.PEDESTRIAN,
        timestamp=time.time(),
        tracking_time=1.0,
        polygon_point=generate_polygon(
            position, heading, 0.3, 0.5)
    )
    return obs

def dynamic_obstacle_location_to_obstacle(_id: int, speed: float, loc: Point3D, heading: float) -> PerceptionObstacle:
    """
    Constructs a perception obstacle message for a dynamic obstacle, used for generating a simulated Apollo instance only

    :param int _id: ID of the obstacle
    :param float speed: speed of the obstacle
    :param Point3D loc: location of the obstacle
    :param float heading: heading of the obstacle
    :returns: a PerceptionObstacle protobuf message ready to be published to cyberRT
    :rtype: PerceptionObstacle
    """
    position = Point3D(x=loc.x,
                       y=loc.y, z=loc.z)
    velocity = Point3D(x=math.cos(heading) * speed,
                       y=math.sin(heading) * speed, z=0.0)
    obs = PerceptionObstacle(
        id=_id,
        position=position,
        theta=heading,
        velocity=velocity,
        acceleration=Point3D(x=0, y=0, z=0),
        length=APOLLO_VEHICLE_LENGTH,
        width=APOLLO_VEHICLE_WIDTH,
        height=APOLLO_VEHICLE_HEIGHT,
        type=PerceptionObstacle.VEHICLE,
        timestamp=time.time(),
        tracking_time=1.0,
        polygon_point=generate_polygon(
            position, heading, APOLLO_VEHICLE_LENGTH, APOLLO_VEHICLE_WIDTH)
    )
    return obs

def to_Point3D(data: Point3D) -> Point3D:
    """
    Replaces NaN that may occur in Apollo to 0.0

    :param Point3D data: Point3D object to be cleaned
    :returns: cleaned up version of the original Point3D object
    :rtype: Point3D
    """
    return Point3D(
        x=0.0 if math.isnan(data.x) else data.x,
        y=0.0 if math.isnan(data.y) else data.y,
        z=0.0 if math.isnan(data.z) else data.z
    )

def localization_to_obstacle(_id: int, data: LocalizationEstimate) -> PerceptionObstacle:
    """
    Converts LocalizationEstimate to PerceptionObstacle. The localization message of an ADS
    instance is used as part of the perception message for other ADS instances.

    :param int _id: ID of the obstacle
    :param LocalizationEstimate data: localization message of the ADC
    :returns: PerceptionObstacle message converted from localization of an ADC
    :rtype: PerceptionObstacle
    """
    # preprocess data, replace NaN with 0.0
    position = to_Point3D(data.pose.position)
    velocity = to_Point3D(data.pose.linear_velocity)
    acceleration = to_Point3D(data.pose.linear_acceleration)

    obs = PerceptionObstacle(
        id=_id,
        position=position,
        theta=data.pose.heading,
        velocity=velocity,
        acceleration=acceleration,
        length=APOLLO_VEHICLE_LENGTH,
        width=APOLLO_VEHICLE_WIDTH,
        height=APOLLO_VEHICLE_HEIGHT,
        type=PerceptionObstacle.VEHICLE,
        timestamp=data.header.timestamp_sec,
        tracking_time=1.0,
        polygon_point=generate_adc_polygon(
            position, data.pose.heading)
    )
    return obs

def extract_main_decision(data: ADCTrajectory) -> Set[Tuple]:
    """
    Extracts the main decision from a Planning message

    :param ADCTrajectory data: ADC's planning module output
    :returns: a set containing the overall decision and main decision for each obstacle
    :rtype: Set[Tuple]
    """
    # get main decision from data
    main_decision = data.decision.main_decision
    # get object decisions from data
    object_decisions = data.decision.object_decision.decision

    decisions = set()

    # analyze main decision
    if main_decision.HasField('cruise'):
        # FORWARD = 0, LEFT = 1, RIGHT = 2
        md = ('main', 'cruise', main_decision.cruise.change_lane_type)
    elif main_decision.HasField('stop'):
        # modules/planning/proto/decision.proto:19
        md = ('main', 'stop', main_decision.stop.reason_code,
              main_decision.stop.reason)
    elif main_decision.HasField('estop'):
        # modules/planning/proto/decision.proto:150
        md = ('main', 'estop', main_decision.estop.reason_code)
    elif main_decision.HasField('mission_complete'):
        md = ('main', 'mission_complete',)
    else:
        md = ('main', 'not_ready',)

    decisions.add(md)

    # analyze object decision
    for obj_d in object_decisions:
        object_decision = obj_d.object_decision[0]
        if object_decision.HasField('stop'):
            od = ('obj', 'stop', object_decision.stop.reason_code)
        elif object_decision.HasField('follow'):
            od = ('obj', 'follow')
        elif object_decision.HasField('yield'):
            od = ('obj', 'yield')
        elif object_decision.HasField('overtake'):
            od = ('obj', 'overtake')
        elif object_decision.HasField('nudge'):
            od = ('obj', 'nudge', object_decision.nudge.type)
        elif object_decision.HasField('avoid'):
            od = ('obj', 'avoid')
        elif object_decision.HasField('side_pass'):
            od = ('obj', 'side_pass', object_decision.side_pass.type)
        else:  # object_decision.HasField('ignore')
            od = ('obj', 'ignore')

        decisions.add(od)

    return decisions

def clean_apollo_dir() -> None:
    """
    Removes Apollo's log files to save disk space
    Process-safe version with file locking for multi-process support
    """
    
    # using file locking to ensure that only one python process executes the
    # cleanup operation at a time
    lock_file = Path(APOLLO_ROOT) / ".cleanup.lock"
    
    try:
        with open(lock_file, 'a+') as lock:
            # try to get an exclusive lock, if not available, block
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            
            try:
                # clean data directory, use more secure way to delete files
                data_dirs = ['bag', 'core', 'log']
                for data_dir in data_dirs:
                    dir_path = Path(APOLLO_ROOT) / 'data' / data_dir
                    if dir_path.exists():
                        # delete files one by one instead of using rm -rf, more secure
                        for item in dir_path.iterdir():
                            try:
                                if item.is_file():
                                    item.unlink()
                                elif item.is_dir():
                                    import shutil
                                    shutil.rmtree(item, ignore_errors=True)
                            except (PermissionError, OSError) as e:
                                print(f"Warning: Failed to delete {item}: {e}")
                
                # clean log files, add retry mechanism
                fileList = glob.glob(f'{APOLLO_ROOT}/*.log.*')
                for filePath in fileList:
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            if os.path.exists(filePath):
                                os.remove(filePath)
                            break
                        except (PermissionError, OSError) as e:
                            if attempt < max_retries - 1:
                                time.sleep(0.1)  # wait for a short time and retry
                                continue
                            else:
                                print(f"Warning: Failed to delete {filePath} after {max_retries} attempts: {e}")
                
                # create records directory, use exist_ok=True to avoid race condition
                records_dir = Path(APOLLO_ROOT) / 'records'
                records_dir.mkdir(exist_ok=True)
                
            finally:
                # release the lock
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                
    except (PermissionError, OSError) as e:
        print(f"Warning: Could not acquire cleanup lock, proceeding without lock: {e}")
        # if cannot get the lock, revert to the original logic but add better error handling
        _clean_without_lock()
    finally:
        # clean the lock file
        try:
            if lock_file.exists():
                lock_file.unlink()
        except:
            pass  # ignore the lock file cleanup failure

def _clean_without_lock() -> None:
    """
    cleanup function without lock, as a fallback solution when lock cannot be acquired
    """
    # use subprocess but add error handling
    cleanup_commands = [
        f"rm -rf {APOLLO_ROOT}/data/bag/*",
        f"rm -rf {APOLLO_ROOT}/data/core/*", 
        f"rm -rf {APOLLO_ROOT}/data/log/*"
    ]
    
    for cmd in cleanup_commands:
        try:
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Warning: Command '{cmd}' failed: {result.stderr}")
        except Exception as e:
            print(f"Warning: Failed to execute '{cmd}': {e}")
    
    # clean log files
    fileList = glob.glob(f'{APOLLO_ROOT}/*.log.*')
    for filePath in fileList:
        try:
            os.remove(filePath)
        except Exception as e:
            print(f"Warning: Failed to delete {filePath}: {e}")
    
    # create records directory
    os.makedirs(os.path.join(APOLLO_ROOT, 'records'), exist_ok=True)

def calculate_velocity(linear_velocity: Point3D) -> float:
    """
    Calculate velocity based on a given vector

    :param Point3D linear_velocity: velocity in vector form
    :returns: speed calculated from the velocity
    :rtype: float
    """
    x, y, z = linear_velocity.x, linear_velocity.y, linear_velocity.z
    return round(math.sqrt(x ** 2 + y ** 2), 2)

def construct_lane_polygon(lane_msg: Lane) -> Polygon:
    '''
    Construct the lane polygon based on their boundaries

    :param Lane lane_msg: Lane protobuf message extracted from HD Map
    :returns: Polygon representing the lane
    :rtype: Polygon
    '''
    left_points = get_lane_boundary_points(lane_msg.left_boundary)
    right_points = get_lane_boundary_points(lane_msg.right_boundary)
    right_points.reverse()
    all_points = left_points + right_points
    return Polygon(all_points)

def get_lane_boundary_points(boundary: LaneBoundary) -> List[Tuple[float, float]]:
    '''
    Given a lane boundary (left/right), return a list of x, y
    coordinates of all points in the boundary

    :param LaneBoundary boundary: LaneBoundary protobuf message
    :returns: list of boundary points
    :rtype: List[Tuple[float, float]]
    '''
    boundary_points = []
    for segment in boundary.curve.segment:
        for segment_point in segment.line_segment.point:
            boundary_points.append((segment_point.x, segment_point.y))
    return boundary_points

def construct_lane_boundary_linestring(lane_msg: Lane) -> Tuple[LineString, LineString]:
    """
    Construct two linestrings for the lane's left and right boundary

    :param Lane lane_msg: Lane protobuf message extracted from HD Map
    :returns: 2 LineString objects representing left and right boundary of the lane
    :rtype: Tuple[LineString, LineString]
    """
    left_boundary_points = get_lane_boundary_points(lane_msg.left_boundary)
    right_boundary_points = get_lane_boundary_points(lane_msg.right_boundary)
    return LineString(left_boundary_points), LineString(right_boundary_points)
