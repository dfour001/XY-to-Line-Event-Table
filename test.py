import geopandas as gp
import pandas as pd
import csv
import shapefile
from shapely.geometry import Point, LineString
from shapely.ops import nearest_points
import traceback
import math


data = 'data/ProjectPipeline.csv'
lrsPath = 'data/LRS_Salem.shp'
lrs = gp.read_file(lrsPath)
lrs = lrs.to_crs(epsg=4326)

# Geopandas does not support loading m-values from the LRS.  This dictionary of m-values is populated by pyshp
print('load m values')
mValueDict = {}
with shapefile.Reader(lrsPath) as shp:
    for row in shp.iterShapeRecords():
        try:
            record = row.record
            shape = row.shape
            rte_nm = record['RTE_NM']
            mValues = shape.m
            mValueDict[rte_nm] = mValues
        except:
            print('Error finding m-value')
            continue


class LRSVertex:
    def __init__(self, index, rte_nm, geom):
        self.index = index
        self.rte_nm = rte_nm
        self.geom = geom

    def __repr__(self):
        return f'<LRSVertex {self.index} on {self.rte_nm}>'


def find_distance(p1, p2):
    """ Find the distance between two input shapely Points """
    return math.sqrt(abs(p1.x - p2.x)**2 + abs(p1.y - p2.y)**2)

def select_nearby_routes(point, d):
    """ Selects routes within d distance from the input point.
        returns a list of rte_nms """
    output = []
    buffer = point.buffer(d)
    for i in lrs.index:
        if buffer.intersects(lrs['geometry'][i]):
            rte_nm = lrs['RTE_NM'][i]
            output.append(rte_nm)
    
    return output


def locate_point_on_route(rte_nm, point):
    """ Given a rte_nm and point, this function will find the closest
        location along the line to the input point, then return the
        m-value for that location 
        
        rte_nm - string
        point - shapely Point
    """

    try:
        # Get LRS rte geometry
        lineGeom = lrs.loc[lrs['RTE_NM'] == rte_nm]['geometry'].item()

        # Find point on input route
        nearestPoints = nearest_points(lineGeom, point)
        testPoint = nearestPoints[0]

        # Find index of next and previous vertices
        lrsIndex = 0  # Find index to look up MP values.  This needs to be tracked here because the index in multi-part lines resets with each new line

        ## Find distance from each vertex to input point and store in list as tuple (index, distance).  The two shortest distances are the vertices that we need
        vertexDistanceList = []
        previousVertex = None
        nextVertex = None

        if lineGeom.type == 'LineString':
            for i in range(len(lineGeom.coords) - 1):
                if LineString([lineGeom.coords[i], lineGeom.coords[i+1]]).intersects(testPoint.buffer(0.00002)):
                    previousVertex = LRSVertex(i, rte_nm, Point(lineGeom.coords[i]))
                    nextVertex = LRSVertex(i + 1, rte_nm, Point(lineGeom.coords[i + 1]))
                    break
        else:
            for line in lineGeom:
                for n in range(len(line.coords) - 1):
                    if LineString([line.coords[n], line.coords[n+1]]).intersects(testPoint.buffer(0.00002)):
                        previousVertex = LRSVertex(lrsIndex, rte_nm, Point(line.coords[n]))
                        nextVertex = LRSVertex(lrsIndex + 1, rte_nm, Point(line.coords[n + 1]))
                        break
                    lrsIndex += 1
                if previousVertex is not None:
                    break
                lrsIndex += 1 # Because the last vertex of each line isn't accounted for (len(coords) - 1 above)

        if not previousVertex or not nextVertex:
            print(f'Could not find a the line segment that the testPoint lies on')
            return None

        # Find distance between previousVertex and nextVertex
        segmentLength = find_distance(previousVertex.geom, nextVertex.geom)

        # Find distance between previousVertex and testVertex
        distToTestPoint = find_distance(previousVertex.geom, testPoint)

        distRatio = distToTestPoint / segmentLength

        # Find previous and next vertex MP values
        previousVertexMP = mValueDict[rte_nm][previousVertex.index]
        nextVertexMP = mValueDict[rte_nm][nextVertex.index]

        if distRatio == 0:
            testPointMP = previousVertexMP
        else:
            testPointMP = previousVertexMP + ((nextVertexMP - previousVertexMP) * distRatio)

        return round(testPointMP, 3)

    except Exception as e:
        print(f'locate_point_on_route failed for {rte_nm}!')
        print(e)
        print(traceback.format_exc())
        
        return None

outputRows = []
with open(data, newline='') as file:
    fileData = csv.DictReader(file)
    for row in fileData:
        try:
            proj_ID = row['Project Name/Description']
            begin_lat = float(row['Project Start Location Latitude'])
            begin_lng = float(row['Project Start Location Longitude'])
            end_lat = float(row['Project End Location Latitude'])
            end_lng = float(row['Project End Location Longitude'])
            beginPoint = Point(begin_lng, begin_lat)
            endPoint = Point(end_lng, end_lat)
            rte_nm = None
            begin_msr = None
            end_msr = None

            print(f'Locating {proj_ID}:')
            beginRoutes = select_nearby_routes(beginPoint, 0.0002)
            endRoutes = select_nearby_routes(endPoint, 0.0002)
            matchRoutes = [rte for rte in beginRoutes if rte in endRoutes]
            if not matchRoutes:
                print(f"No matching routes for {row['Project Name/Description']}")
            else:
                rte_nm = matchRoutes[0]
                begin_msr = locate_point_on_route(rte_nm, beginPoint)
                end_msr = locate_point_on_route(rte_nm, endPoint)

            outputRow = {
                "name": proj_ID,
                "rte_nm": rte_nm,
                "begin_msr": begin_msr,
                "end_msr": end_msr
            }

            outputRows.append(outputRow)
            
        except Exception as e:
            print(e)
            print(f"Error on {row['Project Name/Description']}.")
            outputRow = {
                "name": proj_ID,
                "rte_nm": rte_nm,
                "begin_msr": begin_msr,
                "end_msr": end_msr
            }
            outputRows.append(outputRow)

outputDF = pd.DataFrame(outputRows)
outputDF.to_csv('testOutput.csv', index=False)

