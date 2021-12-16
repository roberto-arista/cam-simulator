#!/usr/bin/env python3

# ---------------- #
# Geometry Helpers #
# ---------------- #

# -- Modules -- #
from math import sqrt, cos, radians, sin
from collections import namedtuple

from fontTools.misc.bezierTools import calcCubicParameters


# -- Constants -- #
Point = namedtuple('Point', 'x, y')


# -- Objects, Functions, Procedures -- #
def calcPointOnBezier(a, b, c, d, tValue):
    ax, ay = a
    bx, by = b
    cx, cy = c
    dx, dy = d
    return Point(ax*tValue**3 + bx*tValue**2 + cx*tValue + dx,
                 ay*tValue**3 + by*tValue**2 + cy*tValue + dy)


def calcDistance(pt1, pt2):
    return sqrt((pt1.x - pt2.x)**2 + (pt1.y - pt2.y)**2)


def collectPointsOnLine(pt1, pt2, distance):
    lineLength = calcDistance(pt1, pt2)

    points = []
    for eachStep in range(0, int(lineLength), distance):
        factor = eachStep/int(lineLength)
        x = interpolate(pt1.x, pt2.x, factor)
        y = interpolate(pt1.y, pt2.y, factor)
        points.append(Point(x, y))
    return points


def interpolate(poleOne, poleTwo, factor):
    desiredValue = poleOne + factor*(poleTwo-poleOne)
    return desiredValue


def collectPointsOnBezierCurve(pt1, pt2, pt3, pt4, steps):
    """Adapted from calcCubicBounds in fontTools
       by Just van Rossum https://github.com/behdad/fonttools"""

    a, b, c, d = calcCubicParameters(pt1, pt2, pt3, pt4)
    steps = [t/float(steps) for t in range(steps-2)]

    pointsWithT = [(pt1, 0)]
    for eachT in steps:
        pt = calcPointOnBezier(a, b, c, d, eachT)
        pointsWithT.append((pt, eachT))
    pointsWithT.append((pt4, 1))

    return pointsWithT


def collectPointsOnBezierCurveWithFixedDistance(pt1, pt2, pt3, pt4, distance):
    tStep = 1000
    rawPoints = collectPointsOnBezierCurve(pt1, pt2, pt3, pt4, tStep)

    index = 0
    cleanPoints = []
    while index < len(rawPoints):
        eachPt, tStep = rawPoints[index]
        cleanPoints.append(eachPt)
        for progress in range(1, len(rawPoints) - index):
            if calcDistance(eachPt, rawPoints[index + progress][0]) >= distance:
                index = index + progress
                break
        else:
            break

    if rawPoints[-1] not in cleanPoints:
        cleanPoints.append(rawPoints[-1][0])

    return cleanPoints


def isTouching(offsetPoint, radius, glyph):
    for angle in range(0, 360, 10):
        x = offsetPoint.x + cos(radians(angle))*radius
        y = offsetPoint.y + sin(radians(angle))*radius
        if glyph.pointInside((x, y)) is True:
            return True
    return False
