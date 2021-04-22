#-------------------------------------------------------------------------------
# Name:        XY_to_Events_Step2.py
# Purpose:     This script takes the output of XY_to_Events_Step1.py as input
#              and attempts to find the missing event geometries by using the
#              network analyst. This is written to run in Python 2.7 with arcpy,
#              since VDOT does not have the license required to run the network
#              analyst in ArcGIS Pro.
#
#              Before this can be run, the following must be created:
#                  -NetworkDataset - an ND of the area of interest made from the
#                   current version of the LRS.  The ND should allow for turns
#                   at vertices.
#
#                   -All_Points - the begin and end points combined into a single
#                    point feature class
#
#              Written for Python 2.7
#
# Author:      daniel.fourquet@vdot.virginia.gov
#
# Created:     3/22/2021
#-------------------------------------------------------------------------------

import arcpy
import csv
import traceback

arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Network")

NetworkDataset = r'C:\Users\daniel.fourquet\Documents\GitHub\XY-to-Line-Event-Table\data\LRS_Salem_ND.nd'

# Event table in csv format with id and comments field
inputData = r'C:\Users\daniel.fourquet\Documents\GitHub\XY-to-Line-Event-Table\data\Data_All_Except_Galax_Events.csv'

# Before running, you must create begin and end point feature classes, thanks to arcpy's inconsistency with
# its ability to read CSV files.  Thanks ESRI!
all_points = r'C:\Users\daniel.fourquet\Documents\GitHub\XY-to-Line-Event-Table\data\SalemData.gdb\All_Points'
outputLinesPath = r'C:\Users\daniel.fourquet\Documents\GitHub\XY-to-Line-Event-Table\data\SalemData.gdb'
outputLinesFileName = 'LastTryForTuesAgain'
outputLines = "{}\\{}".format(outputLinesPath, outputLinesFileName)

print('Make Route Layer')
rteLyr = arcpy.na.MakeRouteLayer(NetworkDataset, "rteLyr", "Length")

print('Make point layers')
all_points = arcpy.MakeFeatureLayer_management(all_points, "end_points")

outputRecords = False # Track if first record was written yet
with open(inputData, 'r') as csvFile:
    csvData = csv.DictReader(csvFile)
    for i, record in enumerate(csvData):
        try:
            id = record['id']
            comments = record['comments']

            # Only process projects that are not found but have coordinates available
            if comments != 'ERROR No matching routes found.':
                continue           

            print('Processing {}'.format(id))

            # Add begin and end points
            print('    Select points')
            arcpy.SelectLayerByAttribute_management(all_points,"NEW_SELECTION","id = {}".format(id))

            print('    Solve')
            arcpy.na.AddLocations(rteLyr, "Stops", all_points)
            arcpy.na.Solve(rteLyr)

            # Check for geometry length > 0
            with arcpy.da.SearchCursor(r"rteLyr\Routes", 'SHAPE@') as cur:
                for row in cur:
                    print('    Shape len = {}'.format(row[0].length))

            print('    Save line geometry')
            # First iteration will create a new feature class.  Subsequent iterations will append to it.
            if not outputRecords:
                print('    --Creating {}'.format(outputLinesFileName))
                arcpy.FeatureClassToFeatureClass_conversion(r"rteLyr\Routes", outputLinesPath, outputLinesFileName)
                arcpy.AddField_management("{}\\{}".format(outputLinesPath, outputLinesFileName), 'nameID', 'TEXT')
                outputRecords = True
            else:
                print('    --Appending to {}'.format(outputLinesFileName))
                arcpy.Append_management(r"rteLyr\Routes","{}\\{}".format(outputLinesPath, outputLinesFileName),"NO_TEST")
            
            with arcpy.da.UpdateCursor(outputLines, "nameID", 'nameID is Null') as cur:
                for row in cur:
                    row[0] = id
                    cur.updateRow(row)

            
            print('Done')
        except Exception as e:
            print('    --- ERROR on {} ---'.format(id))
            print(e)
            print(traceback.format_exc())
            
        finally:
            arcpy.DeleteRows_management(r"rteLyr\Routes")
            arcpy.DeleteRows_management(r"rteLyr\Stops")
            print('\n')







