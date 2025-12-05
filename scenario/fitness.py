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

class DoppeltestFitness(Fitness):
    """
    Class to represent weight of fitness function for DoppelTest GA
    This method fitness function evolution does not consider any diff between the follow-ups and the source

    the first part of weights is for the minimum min_distance
    the second part of weights is for the length of decisions
    the third part of weights isn for the routing request conflict num
    the fourth part of weights is for the statistic of unique violations
    """

    weights = (-1.0, 1.0, 1.0, 1.0)

class MinSingleFitness(Fitness):
    """
    Class to represent weight of fitness function for single-objective optimization,
    minimize direction
    """

    weights = (-1.0,)

class MaxSingleFitness(Fitness):
    """
    Class to represent weight of fitness function for single-objective optimization,
    maximize direction
    """

    weights = (1.0,)
