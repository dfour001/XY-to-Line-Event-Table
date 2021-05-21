import geopandas as gp
import pandas as pd
import csv
import shapefile
from shapely.geometry import Point, LineString
from shapely.ops import nearest_points, transform
import pyproj
import traceback
import math
# from main import lrsPath

lrsPath = 'data/LRS_Salem.shp'
lrs = gp.read_file(lrsPath)
lrs = lrs.to_crs(epsg=26918) # 26918 = UTM 18N

# For projecting points from wgs84 to UTM 18N
wgs84 = pyproj.CRS('EPSG:4326')
utm = pyproj.CRS('EPSG:26918')


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
                if LineString([lineGeom.coords[i], lineGeom.coords[i+1]]).intersects(testPoint.buffer(0.1)):
                    previousVertex = LRSVertex(i, rte_nm, Point(lineGeom.coords[i]))
                    nextVertex = LRSVertex(i + 1, rte_nm, Point(lineGeom.coords[i + 1]))
                    break
        else:
            for line in lineGeom:
                for n in range(len(line.coords) - 1):
                    if LineString([line.coords[n], line.coords[n+1]]).intersects(testPoint.buffer(0.1)):
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


def create_event_table(csvPath, outPath):
    outputRows = []
    with open(csvPath, newline='') as file:
        fileData = csv.DictReader(file)
        for row in fileData:
            try:
                org = row['organization']
                proj_ID = row['id']
                begin_lat = float(row['begin_lat'])
                begin_lng = float(row['begin_lng'])
                # Check for missing end coordinates (point data) and duplicate w/ begin coordinates if needed
                if row['end_lat'] == "":
                    end_lat = float(row['begin_lat'])
                else:                
                    end_lat = float(row['end_lat'])
                
                if row['end_lng'] == "":
                    end_lng = float(row['begin_lng'])
                else:
                    end_lng = float(row['end_lng'])
                beginPoint = Point(begin_lng, begin_lat)
                endPoint = Point(end_lng, end_lat)
                rte_nm = None
                begin_msr = None
                end_msr = None
                comment = ''

                # Project points
                project = pyproj.Transformer.from_crs(wgs84, utm, always_xy=True).transform
                beginPoint = transform(project, beginPoint)
                endPoint = transform(project, endPoint)

                # Search nearby routes until it's clear which rte_nm a project belongs to by
                # reducing the search radius by 1 meter until only 1 rte_nm matches between
                # both begin point and end point.
                x = 25 # Initial search distance
                matchRoutes = None
                while x > 0:
                    # Select routes found within x meters of point
                    beginRoutes = select_nearby_routes(beginPoint, x)
                    endRoutes = select_nearby_routes(endPoint, x)

                    # Find rte_nm that matches between both points
                    matchRoutes = [rte for rte in beginRoutes if rte in endRoutes]

                    if x == 25 and len(matchRoutes) == 0:
                        # No routes within 25m of point
                        break

                    if x < 25 and len(matchRoutes) == 0:
                        # Both routes are close to equal distance.  Go back one meter and return both routes.
                        print('Return both routes')
                        x += 1
                        beginRoutes = select_nearby_routes(beginPoint, x)
                        endRoutes = select_nearby_routes(endPoint, x)
                        matchRoutes = [rte for rte in beginRoutes if rte in endRoutes]
                        break

                    if len(matchRoutes) == 1:
                        # Route found
                        break

                    x -= 1

                if not matchRoutes:
                    comment = "ERROR No matching routes found."
                else:
                    rte_nm = matchRoutes[0]
                    begin_msr = locate_point_on_route(rte_nm, beginPoint)
                    end_msr = locate_point_on_route(rte_nm, endPoint)

                if begin_msr and end_msr and begin_msr == end_msr:
                    begin_msr -= 0.1
                    end_msr += 0.1

                # Check if lat/lng are duplicated
                if begin_lat == end_lat and begin_lng == end_lng:
                    comment += "  ERROR Begin and end point are identical"

                outputRow = {
                    "organization": org,
                    "id": proj_ID,
                    "rte_nm": rte_nm,
                    "begin_msr": begin_msr,
                    "end_msr": end_msr,
                    "begin_lat": begin_lat,
                    "begin_lng": begin_lng,
                    "end_lat": end_lat,
                    "end_lng": end_lng,
                    "comments": comment
                }

                outputRows.append(outputRow)
                
            except Exception as e:
                print(e)
                # print(traceback.format_exc())
                print(f"{row['id']}.")
                comment = "ERROR"
                try:
                    if not row['begin_lat']:
                        comment += " Missing begin_lat."
                    if not row['begin_lng']:
                        comment += " Missing begin_lng."
                    if not row['end_lng']:
                        comment += " Missing end_lng."
                    if not row['end_lat']:
                        comment += " Missing end_lat."
                except:
                    pass

                # Check if lat/lng are duplicates
                if row['begin_lat'] and row['end_lat'] and row['begin_lng'] and row['end_lng']:
                    if row['begin_lat'] == row['end_lat'] and row['begin_lng'] == row['end_lng']:
                        comment += "  ERROR Begin and end point are identical"

                outputRow = {
                    "organization" : row['organization'],
                    "id": row['id'],
                    "rte_nm": None,
                    "begin_msr": None,
                    "end_msr": None,
                    "begin_lat": row['begin_lat'],
                    "begin_lng": row['begin_lng'],
                    "end_lat": row['end_lat'],
                    "end_lng": row['end_lng'],
                    "comments": comment
                }
                outputRows.append(outputRow)

    outputDF = pd.DataFrame(outputRows)
    outputDF.to_csv(outPath, index=False)
    print(f'Event table saved at "{outPath}"')

