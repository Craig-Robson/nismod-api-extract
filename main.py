import requests, json, zipfile, io
import geopandas, pandas
import glob, os


def download_data(query, area_codes):
    """"""

    for code in area_codes:
        #rstring = '%s/mastermap/buildings?export_format=geojson-zip&scale=%s&area_codes=%s&building_year=2011' % (url, area_scale, ''.join(code))
        rstring = '%s/%s&area_codes=%s' % (url, query, ''.join(code))
        response = requests.get(rstring, auth=(auth_username, auth_password))

        print(response.status_code)

        # save zip file
        z = zipfile.ZipFile(io.BytesIO(response.content))
        z.extractall('output')

    print('Downloaded all data')

    # need to loop through all files and add them to a geo-dataframe
    first = True
    for file in glob.glob("output/*.geojson"):

        s_buf = io.StringIO()
        if first:
            gdf = geopandas.read_file(file)
            first = False
        else:
            gdf = gdf.append(geopandas.read_file(file))

        # delete file to free up more memory
        os.remove(file)

    print('Created geodataframe')

    return gdf

# input variables
feature_layer = 'water-bodies' #'buildings' #'developed-land'

auth_username = os.getenv('username')
auth_password = os.getenv('password')
area_codes = os.getenv('area_codes')
scale = os.getenv('scale')

area_codes = area_codes.split(',')
print(area_codes)

url = 'https://www.nismod.ac.uk/api/data'

if scale == 'gor':
    # get the lads in a GOR
    lads = []
    for gor in area_codes:
        print(gor)
        rstring = '%s/boundaries/lads_in_gor?gor_codes=%s&export_format=geojson' % (url, gor)
        response = requests.get(rstring, auth=(auth_username, auth_password))
        #print(response.status_code)
        data = json.loads(response.text)

        for feat in data['features']:
            lads.append(feat['properties']['lad_code'])

elif scale == 'lads':
    lads = area_codes

print('Got list of LADs to process (%s)' %len(lads))
print(lads)
msoa = []
for lad in lads:
    rstring = '%s/boundaries/msoas_in_lad?area_codes=%s&export_format=geojson' % (url, lad)
    response = requests.get(rstring, auth=(auth_username, auth_password))
    #print(rstring)
    #print(response.status_code)
    data = json.loads(response.text)

    for feat in data['features']:
        msoa.append(feat['properties']['msoa_code'])


area_scale = 'msoa'
area_codes = msoa

if feature_layer == 'buildings':
    rstring = 'mastermap/buildings?export_format=geojson-zip&scale=%s&building_year=2011' % (url, area_scale)

    # download data and build dataframe
    gdf = download_data(query=rstring, area_codes=area_codes)

    gdf = gdf.replace('NULL', '0')
    gdf['res_count'] = gdf['res_count'].astype('int64')
    gdf['nonres_count'] = gdf['nonres_count'].astype('int64')
    gdf['number_of_floors'] = gdf['number_of_floors'].astype('int64')
    gdf.drop(['toid_number','height_toroofbase','floor_area','building_ratio','number_of_floors'], axis=1)

    print('Saving output')
    gdf.to_file('/data/outputs/%s.gpkg' %feature_layer, driver="GPKG")

elif feature_layer == 'water-bodies':

    classification_codes = '10089,' #inland water, area
    rstring = 'mastermap/areas?classification_codes=%s&export_format=geojson-zip&scale=%s&year=2011' % (classification_codes, area_scale)

    # download data and build geodataframe
    gdf = download_data(query=rstring, area_codes=area_codes)

    # any processing required before saving the data file
    gdf = gdf.replace('NULL', '0')
    #gdf['res_count'] = gdf['res_count'].astype('int64')
    #gdf.drop([''], axis=1)

    print('Saving output')
    gdf.to_file('/data/outputs/%s.gpkg' %feature_layer, driver="GPKG")

elif feature_layer == 'developed-land':
    # we get all the data, then filter it - this may need to change

    classification_codes = 'all'
    rstring = 'mastermap/areas?classification_codes=%s&export_format=geojson-zip&scale=%s&year=2011' % (
    classification_codes, area_scale)

    # download data and build geodataframe
    gdf = download_data(query=rstring, area_codes=area_codes)

    # any processing required before saving the data file
    # select only polygons we want
    gdf_result = gdf.loc[gdf['theme'] == 'Land']
    gdf_result = gdf_result.loc[gdf_result['make'] == 'Multiple']
    # buildings
    gdf_blds = gdf.loc[gdf['descriptive_group'] == 'Buildings']
    gdf_blds = gdf_blds.loc[gdf_blds['make'] == 'Manmade']
    # rail
    gdf_rail = gdf.loc[gdf['descriptive_group'] == 'Rail']
    gdf_rail = gdf_rail.loc[gdf_rail['make'] == 'Manmade']
    # roads
    gdf_roads = gdf.loc[gdf['descriptive_group'] == 'Roads']
    gdf_roads = gdf_roads.loc[gdf_roads['make'] == 'Manmade'] & gdf_roads.loc[gdf_roads['make'] == 'Unknown']
    # roadside
    gdf_roadside = gdf.loc[gdf['descriptive_group'] == 'Roadside']
    gdf_roadside = gdf_roadside.loc[gdf_roadside['make'] == 'Natural']

    gdf_result.append(gdf_blds).append(gdf_rail).append(gdf_roads).append(gdf_roadside)

    # any other processing to data
    gdf = gdf.replace('NULL', '0')
    #gdf['res_count'] = gdf['res_count'].astype('int64')
    #gdf.drop([''], axis=1)

    print('Saving output')
    gdf.to_file('/data/outputs/%s.gpkg' % feature_layer, driver="GPKG")
