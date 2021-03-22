import pandas as pd
from DMSToDD import dms_to_dd
from test import create_event_table

inputFilePath = r'data\ProjectPipeline.csv'
inputFileConverted = r'data\FranklinCounty_DD.csv'
outputEventTable = r'data\FranklinCounty_Events.csv'


def convert_coordinates(csvPath, outputPath):
    """ Converts input csv file with multiple coordinate formats
        into an output csv file with DD format coordinates """
    outputData = []
    df = pd.read_csv(csvPath, encoding = "ISO-8859-1")
    for i in range(len(df)):
        data = {
            "organization": df.iloc[i]['Organization'],
            "name": df.iloc[i]['Project Name/Description'],
            "begin_lat": dms_to_dd(df.iloc[i]['Project Start Location Latitude']),
            "begin_lng": dms_to_dd(df.iloc[i]['Project Start Location Longitude']),
            "end_lat": dms_to_dd(df.iloc[i]['Project End Location Latitude']),
            "end_lng": dms_to_dd(df.iloc[i]['Project End Location Longitude'])
        }
        outputData.append(data)

    outputDF = pd.DataFrame(outputData)
    outputDF.to_csv(outputPath, index=False)




convert_coordinates(inputFilePath, inputFileConverted)
create_event_table(inputFileConverted, outputEventTable)