import requests, json, zipfile, io
import geopandas, pandas
import glob, os

# input variables
feature_layer = 'water-bodies' #'buildings'

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
    #data = json.loads(response.text)

    #for feat in data['features']:
    #    msoa.append(feat['properties']['msoa_code'])


area_scale = 'lad'#'msoa'
area_codes = lads #msoa

if feature_layer == 'buildings':
    for code in area_codes:
        rstring = '%s/mastermap/buildings?export_format=geojson-zip&scale=%s&area_codes=%s&building_year=2011' % (url, area_scale, ''.join(code))
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

    gdf = gdf.replace('NULL', '0')
    gdf['res_count'] = gdf['res_count'].astype('int64')
    gdf['nonres_count'] = gdf['nonres_count'].astype('int64')
    gdf['number_of_floors'] = gdf['number_of_floors'].astype('int64')
    gdf.drop(['toid_number','height_toroofbase','floor_area','building_ratio','number_of_floors'], axis=1)

    print('Saving output')
    gdf.to_file('/data/outputs/buildings.gpkg', driver="GPKG")

elif feature_layer == 'water-bodies':
    pass

elif feature_layer == 'developed-land':
    pass