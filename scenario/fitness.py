from deap.base import Fitness

class SoundnessFitness(Fitness):
    """
    Class to represent weight of fitness function for MT-GA

    the first part of weights is for the source test case minimize min_dist[0], 
    the second part of weights is for the maxmize max_diff in follow-ups, max(diff[1:])
    """
    weights = (-1.0, 1.0)

class RobustnessFitness(Fitness):
    """
    Class to represent weight of fitness function for MRT-GA

    the first part of weights is for the minimum min_distance among all the follow-ups, min(min_dist[1:])
    the second part of weights is for the minimize min_diff in follow-ups, min(diff[1:])
    """
    weights = (-1.0, -1.0)
