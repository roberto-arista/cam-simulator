'''build CAM Simulator extension'''

import os
from mojo.extensions import ExtensionBundle

# get current folder
basePath = os.path.dirname(__file__)

# source folder for all extension files
sourcePath = os.path.join(basePath, 'source')

# folder with python files
libPath = os.path.join(sourcePath, 'code')

# folder with resources (icons etc)
resourcesPath = os.path.join(sourcePath, 'resources')

# load license text from file
# see choosealicense.com for more open-source licenses
licensePath = os.path.join(basePath, 'license.txt')

# name of the compiled extension file
extensionFile = 'CAMSimulator.roboFontExt'

# path of the compiled extension
buildPath = os.path.join(basePath, 'build')
extensionPath = os.path.join(buildPath, extensionFile)

# initiate the extension builder
B = ExtensionBundle()

# name of the extension
B.name = "CAM Simulator"

# name of the developer
B.developer = 'Roberto Arista'

# URL of the developer
B.developerURL = 'https://github.com/roberto-arista'

# extension icon (file path or NSImage)
imagePath = os.path.join(resourcesPath, 'icon.png')
B.icon = imagePath

# version of the extension
B.version = '0.2.0'

# should the extension be launched at start-up?
B.launchAtStartUp = True

# script to be executed when RF starts
B.mainScript = 'events.py'

# minimum RoboFont version required for this extension
B.requiresVersionMajor = '4'
B.requiresVersionMinor = '1'

# scripts which should appear in Extensions menu
B.addToMenu = [
    {
        'path':          'camSimulator.py',
        'preferredName': 'CAM Simulator',
        'shortKey':      '',
    },
]

# license for the extension
with open(licensePath) as license:
    B.license = license.read()

# compile and save the extension bundle
print('building extension...', end=' ')
B.save(extensionPath, libPath=libPath, resourcesPath=resourcesPath)
print('done!')

# check for problems in the compiled extension
print()
print(B.validationErrors())
