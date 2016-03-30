# -*- coding: utf-8 -*-
from __future__ import unicode_literals
__author__ = 'mgallet'
__all__ = ['sample_function', ]


# write your actual code here.

def sample_function(first, second=4):
    """This is a sample function to demonstrate doctests
    of :mod:`nagiback.code` and docs.
    It only return the sum of its two arguments.

    Args:
      :param first: (:class:`int`): first value to add
      :param second:  (:class:`int`): second value to add, 4 by default

    Returns:
      * :class:`int`: the sum of `first` and `second`.

    >>> sample_function(6, second=3)
    9
    >>> sample_function(6)
    10
    """
    return first + second



if __name__ == '__main__':
    import doctest
    doctest.testmod()
