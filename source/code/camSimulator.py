#!/usr/bin/env python3
# coding: utf-8

#################
# CAM Simulator #
#################

### Modules
from math import radians, cos, sin, sqrt, atan2
from collections import namedtuple
from vanilla import FloatingWindow, TextBox, EditText, Button, HorizontalLine, CheckBox
from mojo.events import addObserver, removeObserver
from mojo.UI import UpdateCurrentGlyphView
from mojo.drawingTools import *
from defcon.objects.glyph import addRepresentationFactory
from fontTools.misc.bezierTools import calcCubicParameters


### Constants
FACTORY_NAME = "CAMsimulator.simulateBorder"

# plugin
Point = namedtuple('Point', 'x, y')
FROM_MM_TO_PT = 2.834627813

TOLERANCE = .1   # upm
DISTANCE = .1   # percentage of bit radius
DISTANCE_THRESHOLD = 4

WHITE = (1, 1, 1)
CIRCLE_COLOR = (0, 1, 0, .1)   # rgb
ERROR_COLOR = (1, 0, 0, .1)

# ui
pluginWidth = 200
pluginHeight = 400

marginTop = 10
marginLft = 10
marginRow = 10
marginRgt = marginLft
marginBtm = 12
marginCol = 5

netWidth = pluginWidth - marginLft - marginRgt

TextBoxHeight = 17
EditTextHeight = 22
ButtonHeight = 20
CheckBoxHeight = 22


### Functions
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


def simulateBorder(glyph, font, bodySize=90, bitSize=1):
    assert bodySize > 0 or bodySize is not None
    assert bitSize > 0 or bitSize is not None
    bitUPM = font.info.unitsPerEm * bitSize * FROM_MM_TO_PT / bodySize

    if DISTANCE*bitUPM > DISTANCE_THRESHOLD:
        relativeDistance = int(DISTANCE*bitUPM)
    else:
        relativeDistance = DISTANCE_THRESHOLD

    previewPoints = []
    simulationPoints = []
    errorPoints = []
    rotation = radians(-90)

    # defcon way of dealing with outlines
    for eachContour in glyph:
        previewContour = []

        for indexSegment, eachSegment in enumerate(eachContour.segments):
            for indexPoint, eachPoint in enumerate(eachSegment):

                if indexSegment == 0:
                    pt1 = Point(eachContour.segments[indexSegment-1][-1].x, eachContour.segments[indexSegment-1][-1].y)

                if eachPoint.segmentType == 'line':
                    pt2 = Point(eachPoint.x, eachPoint.y)
                    points = collectPointsOnLine(pt1, pt2, relativeDistance)
                    pt1 = pt2

                elif eachPoint.segmentType == 'curve':
                    pt2 = Point(eachSegment[indexPoint-2].x, eachSegment[indexPoint-2].y)
                    pt3 = Point(eachSegment[indexPoint-1].x, eachSegment[indexPoint-1].y)
                    pt4 = Point(eachPoint.x, eachPoint.y)

                    points = collectPointsOnBezierCurveWithFixedDistance(pt1,
                                                                         pt2,
                                                                         pt3,
                                                                         pt4,
                                                                         relativeDistance)
                    pt1 = pt4

                else:
                    pass

            # collecting circles
            for indexPt, eachPt in enumerate(points):
                if indexPt != 0 and eachPt != previousPt:
                    angle = atan2((eachPt.y - previousPt.y), (eachPt.x - previousPt.x))
                    offsetPointTolerance = Point(eachPt.x + cos(angle + rotation) * (bitUPM/2 + TOLERANCE),
                                                 eachPt.y + sin(angle + rotation) * (bitUPM/2 + TOLERANCE))

                    offsetPointSharp = Point(eachPt.x + cos(angle + rotation) * (bitUPM/2),
                                             eachPt.y + sin(angle + rotation) * (bitUPM/2))

                    if isTouching(offsetPointTolerance, bitUPM/2., glyph) is False:
                        simulationPoints.append((offsetPointTolerance.x-bitUPM/2., offsetPointTolerance.y-bitUPM/2., bitUPM, bitUPM))
                        previewContour.append((offsetPointSharp.x-bitUPM/2., offsetPointSharp.y-bitUPM/2.))
                    else:
                        errorPoints.append((offsetPointTolerance.x-bitUPM/2., offsetPointTolerance.y-bitUPM/2., bitUPM, bitUPM))
                previousPt = eachPt
            previewPoints.append((eachContour.clockwise, previewContour))

    return bitUPM, previewPoints, simulationPoints, errorPoints


### Class
class CAMsimulator(object):

    # attributes
    previewOn = False
    bodySize = 90
    bitSize = 1
    showSimulation = True
    showErrors = True
    simulationPoints = []
    previewPoints = []
    errorPoints = []
    prevGlyphState = None

    def __init__(self):

        # init win
        self.win = FloatingWindow((pluginWidth, pluginHeight), 'CAM Simulator')

        # body caption
        jumpingY = marginTop
        jumpingX = marginLft
        self.win.bodyCaption = TextBox((jumpingX, jumpingY, netWidth*.38, TextBoxHeight),
                                       'bodySize:',
                                       alignment='right')

        # body edit
        jumpingX += netWidth*.42
        self.win.bodyEdit = EditText((jumpingX, jumpingY, netWidth*.2, EditTextHeight),
                                     text=f'{self.bodySize}',
                                     callback=self.bodyEditCallback)

        # mm edit
        jumpingX += netWidth*.2
        self.win.mm01Caption = TextBox((jumpingX+marginCol, jumpingY+4, netWidth*.2, TextBoxHeight), 'pt', sizeStyle='small')

        # bit caption
        jumpingY += EditTextHeight + marginRow
        jumpingX = marginLft
        self.win.bitCaption = TextBox((jumpingX, jumpingY, netWidth*.38, TextBoxHeight),
                                      'bitSize:',
                                      alignment='right')

        # bit edit
        jumpingX += netWidth*.42
        self.win.bitEdit = EditText((jumpingX, jumpingY, netWidth*.2, EditTextHeight),
                                    text=f'{self.bitSize}',
                                    callback=self.bitEditCallback)

        # mm edit
        jumpingX += netWidth*.2
        self.win.mm02Caption = TextBox((jumpingX+marginCol, jumpingY+4, netWidth*.2, TextBoxHeight), 'mm', sizeStyle='small')

        # show simulation checkbox
        jumpingY += CheckBoxHeight + marginRow
        self.win.simulationCheck = CheckBox((marginLft, jumpingY, netWidth, CheckBoxHeight),
                                            "Show simulation",
                                            value=self.showSimulation,
                                            callback=self.simulationCheckCallback)

        # show errors checkbox
        jumpingY += CheckBoxHeight    # + marginRow
        self.win.errorsCheck = CheckBox((marginLft, jumpingY, netWidth, CheckBoxHeight),
                                        "Show errors",
                                        value=self.showErrors,
                                        callback=self.errorsCheckCallback)

        # separation line
        jumpingY += EditTextHeight + marginRow
        self.win.separationLine = HorizontalLine((marginLft, jumpingY, netWidth, 1))

        # preview button
        jumpingY += marginRow
        jumpingX = marginLft
        self.win.previewButton = Button((jumpingX, jumpingY, netWidth, ButtonHeight),
                                        'Preview On',
                                        callback=self.previewButtonCallback)

        # observers
        addObserver(self, "drawBlack", "drawPreview")
        addObserver(self, "drawSimulation", "drawBackground")
        addObserver(self, "drawSimulation", "drawInactive")
        self.win.bind("close", self.closing)

        # adjust win height
        jumpingY += ButtonHeight + marginBtm
        self.win.setPosSize((0, 0, pluginWidth, jumpingY))

        # opening win
        self.win.open()

    def drawBlack(self, infoDict):
        bitUPM, previewPoints, simulationPoints, errorPoints = infoDict['glyph'].getRepresentation(FACTORY_NAME,
                                                                                                   bodySize=self.bodySize,
                                                                                                   bitSize=self.bitSize,
                                                                                                   font=CurrentFont())

        if self.previewOn is True:
            save()
            translate(bitUPM/2., bitUPM/2.)
            stroke(*WHITE)
            lineJoin('round')
            miterLimit(10)
            strokeWidth(simulationPoints[0][2])

            for contourDirection, contourPoints in previewPoints:
                # 1=clockwise, 0=counterclockwise
                if contourDirection is True:
                    fill(*WHITE)
                else:
                    fill(0)

                newPath()
                for indexPt, eachPt in enumerate(contourPoints):
                    x, y, = eachPt
                    if indexPt == 0:
                        moveTo((x, y))
                    else:
                        lineTo((x, y))
                closePath()
                drawPath()
            restore()

            fill(0)
            drawGlyph(CurrentGlyph())

    def drawSimulation(self, infoDict):
        bitUPM, previewPoints, simulationPoints, errorPoints = infoDict['glyph'].getRepresentation(FACTORY_NAME,
                                                                                                   bodySize=self.bodySize,
                                                                                                   bitSize=self.bitSize,
                                                                                                   font=CurrentFont())

        if self.previewOn is True and simulationPoints and self.showSimulation:
            fill(*CIRCLE_COLOR)
            stroke(None)
            for eachOval in simulationPoints:
                oval(*eachOval)

        if self.previewOn is True and errorPoints and self.showErrors:
            fill(*ERROR_COLOR)
            stroke(None)
            for eachOval in errorPoints:
                oval(*eachOval)
        UpdateCurrentGlyphView()

    def closing(self, sender):
        removeObserver(self, "drawBackground")
        removeObserver(self, "drawPreview")
        removeObserver(self, "drawInactive")
        UpdateCurrentGlyphView()

    # callbacks
    def bodyEditCallback(self, sender):
        try:
            self.bodySize = float(sender.get())
        except ValueError:
            self.bodySize = None
            self.win.bodyEdit.set('')

    def bitEditCallback(self, sender):
        try:
            self.bitSize = float(sender.get())
        except ValueError:
            self.bitSize = None
            self.win.bitEdit.set('')

    def simulationCheckCallback(self, sender):
        self.showSimulation = sender.get()
        UpdateCurrentGlyphView()

    def errorsCheckCallback(self, sender):
        self.showErrors = sender.get()
        UpdateCurrentGlyphView()

    def previewButtonCallback(self, sender):
        if self.bitSize is not None and self.bodySize is not None:
            if self.previewOn is True:
                self.previewOn = False
                self.win.previewButton.setTitle('Preview On')
            else:
                self.previewOn = True
                self.win.previewButton.setTitle('Preview Off')
        UpdateCurrentGlyphView()


### Instructions
addRepresentationFactory(FACTORY_NAME, simulateBorder)
cam = CAMsimulator()