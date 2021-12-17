#!/usr/bin/env python3

# ------------- #
# CAM Simulator #
# ------------- #


# -- Modules -- #
from math import radians

from vanilla import FloatingWindow, TextBox, EditText, Button, HorizontalLine, CheckBox
from mojo.roboFont import OpenWindow
from mojo.subscriber import WindowController, Subscriber
from mojo.subscriber import registerGlyphEditorSubscriber
from mojo.subscriber import unregisterGlyphEditorSubscriber
from mojo.events import postEvent
from defcon import registerRepresentationFactory
from defcon.objects.glyph import Glyph
from fontTools.pens.basePen import BasePen

from events import DEBUG_MODE, DEFAULT_KEY
from geometry import collectPointsOnLine, collectPointsOnBezierCurveWithFixedDistance
from geometry import projectPoint, isTouching, calcAngle


# -- Constants -- #
FROM_MM_TO_PT = 2.834627813

TOLERANCE = .1   # upm
DISTANCE = .1    # percentage of bit radius
DISTANCE_THRESHOLD = 4

WHITE = (1, 1, 1, 1)
BLACK = (0, 0, 0, 1)
CIRCLE_COLOR = (0, 1, 0, .4)
ERROR_COLOR = (1, 0, 0, .4)


# -- Objects -- #
class ContourBreakingPen(BasePen):

    def __init__(self, bitUPM):
        super().__init__({})
        if DISTANCE*bitUPM > DISTANCE_THRESHOLD:
            self.relativeDistance = int(DISTANCE*bitUPM)
        else:
            self.relativeDistance = DISTANCE_THRESHOLD

    def moveTo(self, pt):
        self.points = []
        self._firstPt = pt
        self._prevPt = pt

    def lineTo(self, pt):
        self.points.extend(
            collectPointsOnLine(self._prevPt,
                                pt,
                                self.relativeDistance)
        )
        self._prevPt = pt

    def curveTo(self, pt1, pt2, pt3):
        self.points.extend(
            collectPointsOnBezierCurveWithFixedDistance(self._prevPt,
                                                        pt1,
                                                        pt2,
                                                        pt3,
                                                        self.relativeDistance)
        )
        self._prevPt = pt3

    def closePath(self):
        self.points.extend(
            collectPointsOnLine(self._prevPt,
                                self._firstPt,
                                self.relativeDistance)
        )
        self._prevPt = None


FACTORY_NAME = f"{DEFAULT_KEY}.simulateBorder"
def simulateBorder(glyph, bodySize=90, bitSize=1):
    assert bodySize > 0 or bodySize is not None
    assert bitSize > 0 or bitSize is not None
    bitUPM = glyph.font.info.unitsPerEm * bitSize * FROM_MM_TO_PT / bodySize

    simulationCircles = []
    errorCircles = []

    for eachContour in glyph:
        pen = ContourBreakingPen(bitUPM)
        eachContour.draw(pen)

        previousPt = None
        for indexPt, eachPt in enumerate(pen.points):
            if indexPt != 0 and eachPt != previousPt:
                angle = calcAngle(previousPt, eachPt)

                offsetPointTolerance = projectPoint(point=eachPt,
                                                    angle=angle+radians(-90),
                                                    distance=bitUPM/2 + TOLERANCE)

                if not isTouching(offsetPointTolerance, bitUPM/2, glyph):
                    simulationCircles.append((offsetPointTolerance[0]-bitUPM/2, offsetPointTolerance[1]-bitUPM/2))
                else:
                    errorCircles.append((offsetPointTolerance[0]-bitUPM/2, offsetPointTolerance[1]-bitUPM/2))

            previousPt = eachPt

    return bitUPM, simulationCircles, errorCircles


class CAMSimulatorController(WindowController):

    debug = DEBUG_MODE
    previewOn = False
    bodySize = 90
    bitSize = 1
    showSimulation = True
    showErrors = True

    def build(self):
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

        # init window
        self.w = FloatingWindow((pluginWidth, pluginHeight), "CAM Simulator")

        # body caption
        jumpingY = marginTop
        jumpingX = marginLft
        self.w.bodyCaption = TextBox((jumpingX, jumpingY, netWidth*.38, TextBoxHeight),
                                     "bodySize:",
                                     alignment="right")

        # body edit
        jumpingX += netWidth*.42
        self.w.bodyEdit = EditText((jumpingX, jumpingY, netWidth*.2, EditTextHeight),
                                   text=f"{self.bodySize}",
                                   callback=self.bodyEditCallback)

        # mm edit
        jumpingX += netWidth*.2
        self.w.mm01Caption = TextBox((jumpingX+marginCol, jumpingY+4, netWidth*.2, TextBoxHeight), "pt", sizeStyle="small")

        # bit caption
        jumpingY += EditTextHeight + marginRow
        jumpingX = marginLft
        self.w.bitCaption = TextBox((jumpingX, jumpingY, netWidth*.38, TextBoxHeight),
                                    "bitSize:",
                                    alignment="right")

        # bit edit
        jumpingX += netWidth*.42
        self.w.bitEdit = EditText((jumpingX, jumpingY, netWidth*.2, EditTextHeight),
                                  text=f"{self.bitSize}",
                                  callback=self.bitEditCallback)

        # mm edit
        jumpingX += netWidth*.2
        self.w.mm02Caption = TextBox((jumpingX+marginCol, jumpingY+4, netWidth*.2, TextBoxHeight), "mm",
                                     sizeStyle="small")

        # show simulation checkbox
        jumpingY += CheckBoxHeight + marginRow
        self.w.simulationCheck = CheckBox((marginLft, jumpingY, netWidth, CheckBoxHeight),
                                            "Show simulation",
                                            value=self.showSimulation,
                                            callback=self.simulationCheckCallback)

        # show errors checkbox
        jumpingY += CheckBoxHeight
        self.w.errorsCheck = CheckBox((marginLft, jumpingY, netWidth, CheckBoxHeight),
                                        "Show errors",
                                        value=self.showErrors,
                                        callback=self.errorsCheckCallback)

        # separation line
        jumpingY += EditTextHeight + marginRow
        self.w.separationLine = HorizontalLine((marginLft, jumpingY, netWidth, 1))

        # preview button
        jumpingY += marginRow
        jumpingX = marginLft
        self.w.previewButton = Button((jumpingX, jumpingY, netWidth, ButtonHeight),
                                        "Preview On",
                                        callback=self.previewButtonCallback)

        # adjust window height
        jumpingY += ButtonHeight + marginBtm
        self.w.setPosSize((0, 0, pluginWidth, jumpingY))

        # opening window
        self.w.open()

    def started(self):
        CAMSimulatorSubscriber.controller = self
        registerGlyphEditorSubscriber(CAMSimulatorSubscriber)

    def destroy(self):
        CAMSimulatorSubscriber.controller = None
        unregisterGlyphEditorSubscriber(CAMSimulatorSubscriber)

    # callbacks
    def bodyEditCallback(self, sender):
        try:
            self.bodySize = float(sender.get())
        except ValueError:
            self.bodySize = 90
            self.w.bodyEdit.set("90")
        postEvent(f"{DEFAULT_KEY}.bodySizeDidChange")

    def bitEditCallback(self, sender):
        try:
            self.bitSize = float(sender.get())
        except ValueError:
            self.bitSize = 1
            self.w.bitEdit.set("1")
        postEvent(f"{DEFAULT_KEY}.bitSizeDidChange")

    def simulationCheckCallback(self, sender):
        self.showSimulation = bool(sender.get())
        postEvent(f"{DEFAULT_KEY}.simulationVisibilityDidChange")

    def errorsCheckCallback(self, sender):
        self.showErrors = bool(sender.get())
        postEvent(f"{DEFAULT_KEY}.errorsVisibilityDidChange")

    def previewButtonCallback(self, sender):
        if self.previewOn:
            self.previewOn = False
            self.w.previewButton.setTitle("Preview On")
        else:
            self.previewOn = True
            self.w.previewButton.setTitle("Preview Off")
        postEvent(f"{DEFAULT_KEY}.previewDidChange")


class CAMSimulatorSubscriber(Subscriber):

    debug = DEBUG_MODE
    controller = None

    def build(self):
        glyphEditor = self.getGlyphEditor()

        self.backgroundContainer = glyphEditor.extensionContainer(identifier=DEFAULT_KEY, location="background")
        self.backgroundContainer.setVisible(self.controller.previewOn)
        self.simulationLayer = self.backgroundContainer.appendPathSublayer(
            fillColor=CIRCLE_COLOR
        )
        self.simulationLayer.setVisible(self.controller.showSimulation)

        self.errorsLayer = self.backgroundContainer.appendPathSublayer(
            fillColor=ERROR_COLOR
        )
        self.errorsLayer.setVisible(self.controller.showErrors)

    def started(self):
        self.buildVisualization()

    def destroy(self):
        self.backgroundContainer.clearSublayers()

    def glyphEditorWillSetGlyph(self, info):
        self.clearLayers()

    glyphEditorDidSetGlyphDelay = 0.25
    def glyphEditorDidSetGlyph(self, info):
        if self.controller.previewOn:
            self.buildVisualization()

    glyphEditorGlyphDidChangeOutlineDelay = 0.25
    def glyphEditorGlyphDidChangeOutline(self, info):
        if self.controller.previewOn:
            self.buildVisualization()

    def bodySizeDidChange(self, info):
        self.buildVisualization()

    def bitSizeDidChange(self, info):
        self.buildVisualization()

    def simulationVisibilityDidChange(self, info):
        self.simulationLayer.setVisible(self.controller.showSimulation)

    def errorsVisibilityDidChange(self, info):
        self.errorsLayer.setVisible(self.controller.showErrors)

    def previewDidChange(self, info):
        if self.controller.previewOn:
            self.buildVisualization()
        self.backgroundContainer.setVisible(self.controller.previewOn)

    def clearLayers(self):
        self.simulationLayer.clearSublayers()
        self.errorsLayer.clearSublayers()

    def buildVisualization(self):
        self.clearLayers()

        glyph = self.getGlyphEditor().getGlyph()
        data = glyph.getRepresentation(FACTORY_NAME,
                                       bodySize=self.controller.bodySize,
                                       bitSize=self.controller.bitSize)
        bitUPM, simulationCircles, errorCircles = data

        simulationPen = self.simulationLayer.getPen()
        for eachOval in simulationCircles:
            x, y = eachOval
            simulationPen.oval((x, y, bitUPM, bitUPM))

        errorsPen = self.errorsLayer.getPen()
        for eachOval in errorCircles:
            x, y = eachOval
            errorsPen.oval((x, y, bitUPM, bitUPM))


# -- Instructions -- #
if __name__ == "__main__":
    registerRepresentationFactory(Glyph, FACTORY_NAME, simulateBorder)
    OpenWindow(CAMSimulatorController)
