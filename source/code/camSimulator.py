#!/usr/bin/env python3

# ------------- #
# CAM Simulator #
# ------------- #


# -- Modules -- #
from math import radians, cos, sin, atan2

from vanilla import FloatingWindow, TextBox, EditText, Button, HorizontalLine, CheckBox
from mojo.roboFont import OpenWindow
from mojo.subscriber import WindowController, Subscriber
from mojo.subscriber import registerGlyphEditorSubscriber
from mojo.subscriber import unregisterGlyphEditorSubscriber
from mojo.events import postEvent
from fontTools.pens.basePen import BasePen

from events import DEBUG_MODE, DEFAULT_KEY
from geometry import collectPointsOnLine, collectPointsOnBezierCurveWithFixedDistance, isTouching


# -- Constants -- #
FROM_MM_TO_PT = 2.834627813

TOLERANCE = .1   # upm
DISTANCE = .1    # percentage of bit radius
DISTANCE_THRESHOLD = 4

WHITE = (1, 1, 1, 1)
BLACK = (0, 0, 0, 1)
CIRCLE_COLOR = (0, 1, 0, .1)
ERROR_COLOR = (1, 0, 0, .1)


# -- Objects -- #
class CAMSimulatorPen(BasePen):

    contours = []
    prevPt = None

    def __init__(self, glyph, bodySize, bitSize):
        super().__init__({})
        self.glyph = glyph
        self.bitUPM = self.glyph.font.info.unitsPerEm * bitSize * FROM_MM_TO_PT / bodySize
        if DISTANCE*self.bitUPM > DISTANCE_THRESHOLD:
            self.relativeDistance = int(DISTANCE*self.bitUPM)
        else:
            self.relativeDistance = DISTANCE_THRESHOLD

    def moveTo(self, pt):
        self.points = []
        self.prevPt = pt

    def lineTo(self, pt):
        self.points.extend(
            collectPointsOnLine(self.prevPt,
                                pt,
                                self.relativeDistance)
        )
        self.prevPt = pt

    def curveTo(self, pt1, pt2, pt3):
        self.points.extend(
            collectPointsOnBezierCurveWithFixedDistance(self.prevPt,
                                                        pt1,
                                                        pt2,
                                                        pt3,
                                                        self.relativeDistance)
        )
        self.prevPt = pt3

    def closePath(self):
        print(self.prevPt)
        self.contours.append((self.prevPt.contour.clockwise, self.points))
        self.prevPt = None

    def calcCircles(self):
        self.previewOutlines = []
        self.simulationCircles = []
        self.errorCircles = []

        rotation = radians(-90)
        halfBitUPM = self.bitUPM/2

        for isClockwise, eachContour in self.contours:
            previewContour = []
            previousPt = None
            for indexPt, eachPt in enumerate(self.points):
                if indexPt != 0 and eachPt != previousPt:
                    angle = atan2((eachPt[1] - previousPt[1]), (eachPt[0] - previousPt[0]))
                    offsetPointTolerance = (eachPt[0] + cos(angle + rotation) * (halfBitUPM + TOLERANCE),
                                            eachPt[1] + sin(angle + rotation) * (halfBitUPM + TOLERANCE))

                    offsetPointSharp = (eachPt[0] + cos(angle + rotation) * (halfBitUPM),
                                        eachPt[1] + sin(angle + rotation) * (halfBitUPM))

                    if not isTouching(offsetPointTolerance, halfBitUPM, self.glyph):
                        self.simulationCircles.append((offsetPointTolerance[0]-halfBitUPM, offsetPointTolerance[1]-halfBitUPM, self.bitUPM))
                        previewContour.append((offsetPointSharp[0]-halfBitUPM, offsetPointSharp[1]-halfBitUPM))
                    else:
                        self.errorCircles.append((offsetPointTolerance[0]-halfBitUPM, offsetPointTolerance[1]-halfBitUPM, self.bitUPM))

                previousPt = eachPt
            self.previewOutlines.append((isClockwise, previewContour))


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
        self.w = FloatingWindow((pluginWidth, pluginHeight), 'CAM Simulator')

        # body caption
        jumpingY = marginTop
        jumpingX = marginLft
        self.w.bodyCaption = TextBox((jumpingX, jumpingY, netWidth*.38, TextBoxHeight),
                                     'bodySize:',
                                     alignment='right')

        # body edit
        jumpingX += netWidth*.42
        self.w.bodyEdit = EditText((jumpingX, jumpingY, netWidth*.2, EditTextHeight),
                                   text=f'{self.bodySize}',
                                   callback=self.bodyEditCallback)

        # mm edit
        jumpingX += netWidth*.2
        self.w.mm01Caption = TextBox((jumpingX+marginCol, jumpingY+4, netWidth*.2, TextBoxHeight), 'pt', sizeStyle='small')

        # bit caption
        jumpingY += EditTextHeight + marginRow
        jumpingX = marginLft
        self.w.bitCaption = TextBox((jumpingX, jumpingY, netWidth*.38, TextBoxHeight),
                                    'bitSize:',
                                    alignment='right')

        # bit edit
        jumpingX += netWidth*.42
        self.w.bitEdit = EditText((jumpingX, jumpingY, netWidth*.2, EditTextHeight),
                                  text=f'{self.bitSize}',
                                  callback=self.bitEditCallback)

        # mm edit
        jumpingX += netWidth*.2
        self.w.mm02Caption = TextBox((jumpingX+marginCol, jumpingY+4, netWidth*.2, TextBoxHeight), 'mm',
                                     sizeStyle='small')

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
                                        'Preview On',
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
            self.bodySize = None
            self.w.bodyEdit.set('')
        postEvent(f"{DEFAULT_KEY}.bodySizeDidChange")

    def bitEditCallback(self, sender):
        try:
            self.bitSize = float(sender.get())
        except ValueError:
            self.bitSize = None
            self.w.bitEdit.set('')
        postEvent(f"{DEFAULT_KEY}.bitSizeDidChange")

    def simulationCheckCallback(self, sender):
        self.showSimulation = sender.get()
        postEvent(f"{DEFAULT_KEY}.simulationVisibilityDidChange")

    def errorsCheckCallback(self, sender):
        self.showErrors = sender.get()
        postEvent(f"{DEFAULT_KEY}.errorsVisibilityDidChange")

    def previewButtonCallback(self, sender):
        if self.bitSize is not None and self.bodySize is not None:
            if self.previewOn:
                self.previewOn = False
                self.w.previewButton.setTitle('Preview On')
            else:
                self.previewOn = True
                self.w.previewButton.setTitle('Preview Off')
        postEvent(f"{DEFAULT_KEY}.previewDidChange")


class CAMSimulatorSubscriber(Subscriber):

    debug = DEBUG_MODE
    controller = None

    def build(self):
        glyphEditor = self.getGlyphEditor()

        self.backgroundContainer = glyphEditor.extensionContainer(identifier=DEFAULT_KEY, location='background')
        self.simulationLayer = self.backgroundContainer.appendBaseSublayer()
        self.errorsLayer = self.backgroundContainer.appendBaseSublayer()

        self.previewContainer = glyphEditor.extensionContainer(identifier=DEFAULT_KEY, location='preview')
        self.previewLayer = self.previewContainer.appendPathSublayer()

    def started(self):
        self.buildVisualization()

    def destroy(self):
        self.backgroundContainer.clearSublayers()
        self.previewContainer.clearSublayers()

    def glyphEditorGlyphDidChangeOutline(self, info):
        self.buildVisualization()

    def bodySizeDidChange(self, info):
        self.buildVisualization()

    def bitSizeDidChange(self, info):
        self.buildVisualization()

    def simulationVisibilityDidChange(self, info):
        self.simulationLayer.setVisibility(self.controller.showSimulation)

    def errorsVisibilityDidChange(self, info):
        self.errorsLayer.setVisibility(self.controller.showErrors)

    def previewDidChange(self, info):
        self.simulationLayer.setVisibility(self.controller.previewOn)
        self.errorsLayer.setVisibility(self.controller.previewOn)
        self.previewLayer.setVisibility(self.controller.previewOn)

    def buildVisualization(self):
        glyph = self.getGlyphEditor().getGlyph()
        pen = CAMSimulatorPen(glyph=self.getGlyphEditor().getGlyph(),
                              bodySize=self.controller.bodySize,
                              bitSize=self.controller.bitSize)
        glyph.draw(pen)
        pen.calcCircles()

        # simulation and errors in the glyph editor
        for eachOval in pen.simulationCircles:
            x, y, diameter = eachOval
            self.simulationLayer.appendOvalSublayer(
                fillColor=CIRCLE_COLOR,
                position=(x, y),
                size=(diameter, diameter)
            )
        for eachOval in pen.errorCircles:
            x, y, diameter = eachOval
            self.simulationLayer.appendOvalSublayer(
                fillColor=ERROR_COLOR,
                position=(x, y),
                size=(diameter, diameter)
            )

        # preview
        for contourDirection, contourPoints in pen.previewPoints:

            contourLayer = self.previewLayer.appendPathSublayer(
                strokeJoin='round',
                position=(self.bitUPM/2, self.bitUPM/2),
                strokeColor=WHITE,
                strokeWidth=diameter,
                fillColor=WHITE if contourDirection else BLACK
            )
            contourLayerPen = contourLayer.getPen()
            for indexPt, eachPt in enumerate(contourPoints):
                x, y, = eachPt
                if indexPt == 0:
                    contourLayerPen.moveTo((x, y))
                else:
                    contourLayerPen.lineTo((x, y))
            contourLayerPen.closePath()

        self.previewLayer.appendPathSublayer(
            fillColor=BLACK
        )
        glyph = self.getGlyphEditor().getGlyph()
        self.previewLayer.setPath(glyph.getRepresentation("merz.CGPath"))


# -- Instructions -- #
if __name__ == '__main__':
    OpenWindow(CAMSimulatorController)
