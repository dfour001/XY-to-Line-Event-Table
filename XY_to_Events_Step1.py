#-------------------------------------------------------------------------------
# Name:        XY_to_Events_Step1.py
# Purpose:     This script will find line events on the lrs given the begin and
#              end point coordinates using GeoPandas.  It will only return a
#              result if the entire event is located on one route.  If not, then
#              the event will need to be located using the Network Analyst (see
#              XY_to_Events_Step2.py).
#
#              Written for Python 3.7
#
# Author:      daniel.fourquet@vdot.virginia.gov
#
# Created:     3/22/2021
#-------------------------------------------------------------------------------
import pandas as pd
from DMSToDD import dms_to_dd
from CreateEventTable import create_event_table

# This should be a csv with all projects in a single sheet
inputFilePath = r'data\AllProjects.csv'

# This will be created by the script after converting coordinates to DD
inputFileConverted = r'data\AllProjects_DD.csv'

outputEventTable = r'data\AllProjects_Events.csv'





def convert_coordinates(csvPath, outputPath):
    """ Converts input csv file with multiple coordinate formats
        into an output csv file with DD format coordinates """
    outputData = []
    df = pd.read_csv(csvPath, encoding = "ISO-8859-1")
    for i in range(len(df)):
        data = {
            "organization": df.iloc[i]['Organization'],
            "id": df.iloc[i]['id'],
            "begin_lat": dms_to_dd(df.iloc[i]['Project Start Location Latitude']),
            "begin_lng": dms_to_dd(df.iloc[i]['Project Start Location Longitude']),
            "end_lat": dms_to_dd(df.iloc[i]['Project End Location Latitude']),
            "end_lng": dms_to_dd(df.iloc[i]['Project End Location Longitude'])
        }
        outputData.append(data)

    outputDF = pd.DataFrame(outputData)
    outputDF.to_csv(outputPath, index=False)



# Convert coordinates from DMS/DD to DD and ensure that they are all in the
# correct hemisphere
convert_coordinates(inputFilePath, inputFileConverted)

# Create an output events table.  Events that span multiple routes will require
# further processing with the network analyst
create_event_table(inputFileConverted, outputEventTable)