"""A small, well-documented module for basic statistics helpers."""


def mean(values):
    """Return the arithmetic mean of a list of numbers."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def variance(values):
    """Return the population variance of a list of numbers."""
    if not values:
        return 0.0
    avg = mean(values)
    return sum((v - avg) ** 2 for v in values) / len(values)


def standard_deviation(values):
    """Return the population standard deviation of a list of numbers."""
    return variance(values) ** 0.5
