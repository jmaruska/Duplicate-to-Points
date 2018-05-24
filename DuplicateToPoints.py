#Author-Joshua Maruska
#Description-Duplicate a non-parametric copy of a body to a collection of points.

# Referenced heavily from: https://github.com/boboman/Octonomous/blob/master/Octonomous.py
# Referenced heavily from: https://github.com/tapnair/copyPaste/blob/master/copyPaste.py
# Thank you, Patrick Rainsberry

import adsk.core, traceback
import adsk.fusion

from os.path import expanduser
import os

handlers = []

resultFilename = ''


# Creates directory and returns file name for settings file
def getFileName():

    # Get Home directory
    home = expanduser("~")
    home += '/duplicateToPoint/'
    
    # Create if doesn't exist
    if not os.path.exists(home):
        os.makedirs(home)
    
    # Create file name in this path
    copyPasteFileName = home  + 'duplicator.step'
    return copyPasteFileName


# Export an STL file of selection to local temp directory
def exportFile(tempComponent, filename):

    # Get the ExportManager from the active design.
    app = adsk.core.Application.get()
    design = app.activeProduct
    exportMgr = design.exportManager
    
    # Create export options for STL export    
    stepOptions = exportMgr.createSTEPExportOptions(filename, tempComponent)

    
    # Execute Export command
    exportMgr.execute(stepOptions)
    
    return filename

def getTempComponent(tempBodies):
    app = adsk.core.Application.get()
    product = app.activeProduct
    design = adsk.fusion.Design.cast(product)
    rootComp = design.rootComponent
    tempOccurance = rootComp.occurrences.addNewComponent(adsk.core.Matrix3D.create()) 
    
    for body in tempBodies:
        body.copyToComponent(tempOccurance)
            
    return tempOccurance         
                
def pasteBodies(filename, pasteComponent):

    app = adsk.core.Application.get()
    product = app.activeProduct
    design = adsk.fusion.Design.cast(product)
    rootComp = design.rootComponent
    #features = rootComp.features
        
    # Get import manager
    importManager = app.importManager
    stpFileName = filename
    stpOptions = importManager.createSTEPImportOptions(stpFileName)
    
    temp2Occurence = rootComp.occurrences.addNewComponent(adsk.core.Matrix3D.create()) 
    # Import step file to root component
    importManager.importToTarget(stpOptions, temp2Occurence.component)
    
    base_ = pasteComponent.features.baseFeatures.add()
    
    if base_.startEdit():
        #will probably need to iterate through the destination points, not the bodies. One paste function per destination
        for body in temp2Occurence.component.occurrences.item(0).component.bRepBodies:
            pastedbody = pasteComponent.bRepBodies.add(body, base_)
            
            # Create a transform to do move
            #this is all wrong...
            vector = adsk.core.Vector3D.create(0.0, 10.0, 0.0) # this will be the destinationsSelectInput[n] worldspace position
            transform = adsk.core.Matrix3D.create() # this will be the refPointSelectInput worldspace position
            newTransform = adsk.core.Matrix3D.create() # this will be the differenced vector of transform and newTransform
            newTransform.translation = vector 
            transform.transformBy(newTransform)
            
            pastedbody.transform = vector
            
        base_.finishEdit()  
    
    temp2Occurence.deleteMe()
        
# Get the current values of the command inputs.
def getCopyInputs(inputs):
    try:
    
        selection_input = inputs.itemById('bodySelectInput')
        count = selection_input.selectionCount
        tempBodies = adsk.core.ObjectCollection.create()
    
        for i in range(0, count):
            body = selection_input.selection(i).entity
            tempBodies.add(body)
    
        return tempBodies
    except:
        app = adsk.core.Application.get()
        ui = app.userInterface
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def getPasteInputs(inputs):
    
    try: 

        app = adsk.core.Application.get()
        product = app.activeProduct
        design = adsk.fusion.Design.cast(product)       
        pasteComponent = design.rootComponent
 
        return pasteComponent
        
    except:
        app = adsk.core.Application.get()
        ui = app.userInterface
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

# Define the event handler for when the copyPaste command is executed 
class FusionCopyExecutedEventHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):

        ui = []
        try:
            global resultFilename
            app = adsk.core.Application.get()
            ui  = app.userInterface

            # Get the inputs.
            inputs = args.command.commandInputs
            tempBodies = getCopyInputs(inputs)
            filename = getFileName()
            tempOccurance = getTempComponent(tempBodies)
            
            # Export the selected file as a step to temp directory            
            resultFilename = exportFile(tempOccurance.component, filename)
            tempOccurance.deleteMe()
            

            # Connect to the command executed event.
            cmd = args.command
            cmd.isExecutedWhenPreEmpted = False
            
            onExecute = FusionPasteExecutedEventHandler()
            cmd.execute.add(onExecute)
            handlers.append(onExecute)
            

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Define the event handler for when the copyPaste command is run by the user.
class FusionCopyCreatedEventHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        ui = []
        try:
            app = adsk.core.Application.get()
            ui  = app.userInterface

            # Connect to the command executed event.
            cmd = args.command
            cmd.isExecutedWhenPreEmpted = False
            
            onExecute = FusionCopyExecutedEventHandler()
            cmd.execute.add(onExecute)
            handlers.append(onExecute)

            # Define the inputs.
            inputs = cmd.commandInputs
            
            
            # Create a selection input.
            bodytocopy = inputs.addSelectionInput('bodySelectInput', 'Body to Copy', 'Basic select command input')
            bodytocopy.addSelectionFilter('SolidBodies')
            bodytocopy.setSelectionLimits(1,1)
            
            # Create a selection input.
            refpoint = inputs.addSelectionInput('refPointSelectInput', 'Reference Point', 'Basic select command input')
            refpoint.addSelectionFilter('SketchPoints')
            refpoint.setSelectionLimits(0)  
            
            # Create a selection input.
            destinations = inputs.addSelectionInput('destinationsSelectInput', 'Destination Points', 'Basic select command input')
            destinations.addSelectionFilter('SketchPoints')
            destinations.setSelectionLimits(0)
            
            
            cmd.commandCategoryName = 'fusionCopy'
            cmd.setDialogInitialSize(500, 300)
            cmd.setDialogMinimumSize(300, 300)

            cmd.okButtonText = 'Duplicate'
            
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

# Define the event handler for when the copyPaste command is executed 
class FusionPasteExecutedEventHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):

        ui = []
        try:
            global resultFilename
            app = adsk.core.Application.get()
            ui  = app.userInterface
            
            product = app.activeProduct
            design = adsk.fusion.Design.cast(product)

            # Get the inputs.
            inputs = args.command.commandInputs
            pasteComponent = getPasteInputs(inputs)
            filename = getFileName()
            pasteBodies(filename, pasteComponent)
            
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

                
# Main Definition
def run(context):
    ui = None

    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface

        if ui.commandDefinitions.itemById('DB2PButtonID'):
            ui.commandDefinitions.itemById('DB2PButtonID').deleteMe()

        # Get the CommandDefinitions collection.
        cmdDefs = ui.commandDefinitions

        FusionCopyButtonDef = cmdDefs.addButtonDefinition('DB2PButtonID', 'Duplicate Bodies to Points - 006', 'Select a body, a reference point and all the destination points to pattern the body to.\n', './resources')
        onCopyCreated = FusionCopyCreatedEventHandler()
        FusionCopyButtonDef.commandCreated.add(onCopyCreated)
        handlers.append(onCopyCreated)
        
        # Find the "ADD-INS" panel for the solid and the surface workspaces.
        solidPanel = ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
        surfacePanel = ui.allToolbarPanels.itemById('SurfaceScriptsAddinsPanel')
        
        # Add a button for the "Duplicate Bodies" command into both panels.
        buttonControl1 = solidPanel.controls.addCommand(FusionCopyButtonDef, '', False)
        buttonControl2 = surfacePanel.controls.addCommand(FusionCopyButtonDef, '', False)

    
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def stop(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface

        if ui.commandDefinitions.itemById('DB2PButtonID'):
            ui.commandDefinitions.itemById('DB2PButtonID').deleteMe()
        if ui.commandDefinitions.itemById('PasteButtonID'):
            ui.commandDefinitions.itemById('PasteButtonID').deleteMe()   

        # Find the controls in the solid and surface panels and delete them.
        solidPanel = ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
        cntrl = solidPanel.controls.itemById('DB2PButtonID')
        if cntrl:
            cntrl.deleteMe()
        
        surfacePanel = ui.allToolbarPanels.itemById('SurfaceScriptsAddinsPanel')

        cntrl = surfacePanel.controls.itemById('DB2PButtonID')
        if cntrl:
            cntrl.deleteMe()
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
