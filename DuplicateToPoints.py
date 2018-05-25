#Author-Joshua Maruska
#Description-Duplicate a non-parametric copy of a body to a collection of points.

# Referenced heavily from: https://github.com/boboman/Octonomous/blob/master/Octonomous.py
# Referenced heavily from: https://github.com/tapnair/copyPaste/blob/master/copyPaste.py
# Thank you, Patrick Rainsberry and Adam Kumpf!

import adsk.core, traceback
import adsk.fusion

handlers = []


# From a set of selected bodies, join them in a new component for passing around/saving/etc.
def getTempComponentFromBodies(tempBodies):
    app = adsk.core.Application.get()
    product = app.activeProduct
    design = adsk.fusion.Design.cast(product)
    rootComp = design.rootComponent
    tempOccurance = rootComp.occurrences.addNewComponent(adsk.core.Matrix3D.create()) 
    for body in tempBodies:
        body.copyToComponent(tempOccurance)
    return tempOccurance         
                
# The next set of function get the values of the command inputs (UI) when we need them later.
def getInputs_Bodies(inputs):
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

def getInputs_RefPoint(inputs):
    try:
        selection_input = inputs.itemById('refPointSelectInput')
        return selection_input.selection(0).entity
    except:
        app = adsk.core.Application.get()
        ui = app.userInterface
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
            
def getInputs_DestPoints(inputs):
    try:
        selection_input = inputs.itemById('destinationsSelectInput')
        count = selection_input.selectionCount
        destPoints = adsk.core.ObjectCollection.create()
        for i in range(0, count):
            dpt = selection_input.selection(i).entity
            destPoints.add(dpt)
        return destPoints
    except:
        app = adsk.core.Application.get()
        ui = app.userInterface
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Define the event handler for when the add-in command is executed 
# --> EXECUTE THE ADD-IN (i.e. the user has selected things; now actually perform the action to the CAD models using those inputs)
class FusionAddInExecutedEventHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        ui = []
        try:
            global resultFilename
            app     = adsk.core.Application.get()
            ui      = app.userInterface
            product = app.activeProduct
            design  = adsk.fusion.Design.cast(product)
            # Get the inputs.
            inputs          = args.command.commandInputs
            selectedBodies  = getInputs_Bodies(inputs)
            refPoint        = getInputs_RefPoint(inputs)
            destPoints      = getInputs_DestPoints(inputs)
            tempComponent   = getTempComponentFromBodies(selectedBodies)

            # -----------------------
            # design.rootComponent is the ROOT, design.activeComponent is the selected/active component.
            #rootComp = design.rootComponent
            rootComp = design.activeComponent
            # -----------------------
            base_ = rootComp.features.baseFeatures.add()
            if base_.startEdit():
                #will probably need to iterate through the destination points, not the bodies. One paste function per destination
                p3d_ref = refPoint.worldGeometry
                for dstPoint in destPoints:
                    p3d_dst = dstPoint.worldGeometry
                    pastedBodies = adsk.core.ObjectCollection.create()
                    for body in tempComponent.component.bRepBodies:
                        pastedbody = rootComp.bRepBodies.add(body, base_)
                        pastedBodies.add(pastedbody)
                    # Create a transform to do move
                    vector = adsk.core.Vector3D.create(p3d_dst.x-p3d_ref.x, p3d_dst.y-p3d_ref.y, p3d_dst.z-p3d_ref.z)
                    transform = adsk.core.Matrix3D.create()
                    transform.translation = vector
                    # Create a move feature
                    moveFeats = rootComp.features.moveFeatures
                    moveFeatureInput = moveFeats.createInput(pastedBodies, transform)
                    moveFeats.add(moveFeatureInput)  
                base_.finishEdit()
            tempComponent.deleteMe()
            # -----------------------
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

# Define the event handler for when the add-in command is run by the user.
# --> BUILD THE ADD-IN'S UI (allow user to select bodies, points, etc.)
class FusionAddInCreatedEventHandler(adsk.core.CommandCreatedEventHandler):
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
            onExecute = FusionAddInExecutedEventHandler()
            cmd.execute.add(onExecute)
            handlers.append(onExecute)
            # Define the inputs.
            inputs = cmd.commandInputs
            # Create a selection input.
            bodytocopy = inputs.addSelectionInput('bodySelectInput', 'Bodies to Copy', 'Basic select command input')
            bodytocopy.addSelectionFilter('SolidBodies')
            bodytocopy.setSelectionLimits(1,9999)  # min,max points required
            # Create a selection input.
            refpoint = inputs.addSelectionInput('refPointSelectInput', 'Reference Sketch Point', 'Basic select command input')
            refpoint.addSelectionFilter('SketchPoints')
            refpoint.setSelectionLimits(1,1)  # min,max points required
            # Create a selection input.
            destinations = inputs.addSelectionInput('destinationsSelectInput', 'Destination Sketch Points', 'Basic select command input')
            destinations.addSelectionFilter('SketchPoints')
            destinations.setSelectionLimits(1,9999)  # min,max points required
            # --
            cmd.commandCategoryName = 'fusionCopy'
            cmd.setDialogInitialSize(400, 300)
            cmd.setDialogMinimumSize(300, 300)
            cmd.okButtonText = 'Duplicate'
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

# Main Definition
# --> INITIALIZE MAIN APP (add buttons to the main Fusion 360 app so the user can call the add-in)
def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        if ui.commandDefinitions.itemById('DB2PButtonID'):
            ui.commandDefinitions.itemById('DB2PButtonID').deleteMe()
        # Get the CommandDefinitions collection.
        cmdDefs = ui.commandDefinitions
        FusionAddInButtonDef = cmdDefs.addButtonDefinition('DB2PButtonID', 'Duplicate Bodies to Points', 'Select a body, a reference point and all the destination points to pattern the body to.\n', './resources')
        onAddInCreated = FusionAddInCreatedEventHandler()
        FusionAddInButtonDef.commandCreated.add(onAddInCreated)
        handlers.append(onAddInCreated)
        # Find the "ADD-INS" panel for the solid and the surface workspaces.
        solidPanel = ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
        surfacePanel = ui.allToolbarPanels.itemById('SurfaceScriptsAddinsPanel')
        # Add a button for the "Duplicate Bodies" command into both panels.
        buttonControl1 = solidPanel.controls.addCommand(FusionAddInButtonDef, '', False)
        buttonControl2 = surfacePanel.controls.addCommand(FusionAddInButtonDef, '', False)
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

# --> CLEANUP MAIN APP (remove any files/buttons created when the add-in was started/used)
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
