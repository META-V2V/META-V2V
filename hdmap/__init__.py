from modules.map.proto.map_pb2 import Map


def load_hd_map(filename: str) -> Map:
    """
    Load HD Map from file

    :param str filename: path to the HD Map file
    :returns: Map object
    :rtype: Map
    """
    map = Map()
    with open(filename, 'rb') as f:
        map.ParseFromString(f.read())
    return map
