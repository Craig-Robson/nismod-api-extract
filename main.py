import requests, json, zipfile, io
import geopandas, pandas
import glob, os
from os import getenv


def fetch_inputs():
    """"""

    # input variables
    feature_layer = getenv('feature_layer') #developed-land' #'water-bodies' # #  # 'buildings' #
    if feature_layer is None:
        print('Warning! No feature layer defined. Setting as developed-land')
        feature_layer = 'developed-land'

    auth_username = getenv('username')
    if auth_username is None:
        print('Error! No api username passed. Exiting!')
        exit(2)

    auth_password = getenv('password')
    if auth_password is None:
        print('Error! No api password passed. Exiting!')
        exit(2)

    area_codes = getenv('area_codes') #'E12000001,E12000002,E12000003,E12000004,E12000005,E12000006,E12000007,E12000008,E12000009' #
    if area_codes is None:
        print('Warning! No area codes passed. Setting area code for Newcastle Upon Tyne (E08000021)')
        area_codes = 'E08000021'

    scale = getenv('scale')
    if scale is None:
        print('Warning! No scale definition passed. Setting as lads')
        scale = 'lads'

    # name for output
    output_name = getenv('output_name')
    if output_name is None:
        print('Warning! No output name passed. Output name will be the same will use the feature layer type.')
        output_name = feature_layer

    # year to use when fetching data
    data_year = getenv('data_year')
    if data_year is None:
        print('Warning! No data year passed. Using default of 2011.')
        data_year = '2011'

    debug = getenv('debug')
    if debug is None:
        debug = False

    output_dir = 'data/outputs/'
    return feature_layer, auth_password, auth_username, area_codes, scale, data_year, output_dir, output_name, debug


def clear_download_directory():
    """
    Clear the download directory when finished processing
    """
    return


def check_response(response):
    """
    """
    if response.status_code != 200:
        print('Error in response from API!!!!!')
        print(response.status_code)
        print(response.text)
        exit(2)
    return


def download_data(query, area_codes, auth_username, auth_password, url='https://www.nismod.ac.uk/api/data', debug=False):
    """"""

    for code in area_codes:
        if debug: print(code)
        #rstring = '%s/mastermap/buildings?export_format=geojson-zip&scale=%s&area_codes=%s&building_year=2011' % (url, area_scale, ''.join(code))
        rstring = '%s/%s&area_codes=%s' % (url, query, ''.join(code))
        response = requests.get(rstring, auth=(auth_username, auth_password))

        check_response(response)

        # save zip file
        z = zipfile.ZipFile(io.BytesIO(response.content))
        z.extractall('output')

    if debug: print('Downloaded all data')

    # need to loop through all files and add them to a geo-dataframe
    first = True
    if debug: print(glob.glob("output/*.geojson"))
    for file in glob.glob("output/*.geojson"):

        s_buf = io.StringIO()
        if first:
            gdf = geopandas.read_file(file)
            first = False
        else:
            gdf = gdf.append(geopandas.read_file(file))

        # delete file to free up more memory
        os.remove(file)

    print('Information: Downloaded all data and rreated geodataframe.')

    return gdf


def main():

    feature_layer, auth_password, auth_username, area_codes, scale, data_year, output_dir, output_name, debug = fetch_inputs()


    url = 'https://www.nismod.ac.uk/api/data'

    area_codes = area_codes.split(',')
    if debug: print(area_codes)

    if scale == 'gors':
        # get the lads in a GOR
        lads = []
        for gor in area_codes:
            if debug: print(gor)
            rstring = '%s/boundaries/lads_in_gor?gor_codes=%s&export_format=geojson' % (url, gor)
            response = requests.get(rstring, auth=(auth_username, auth_password))

            check_response(response)

            data = json.loads(response.text)

            for feat in data['features']:
                lads.append(feat['properties']['lad_code'])

    elif scale == 'lads':
        lads = area_codes

    #print('Got list of LADs to process (%s)' %len(lads))
    if debug: print(lads)
    msoa = []
    for lad in lads:
        rstring = '%s/boundaries/msoas_in_lad?area_codes=%s&export_format=geojson' % (url, lad)
        response = requests.get(rstring, auth=(auth_username, auth_password))

        check_response(response)

        data = json.loads(response.text)

        for feat in data['features']:
            msoa.append(feat['properties']['msoa_code'])


    print('Information: Got all area codes ready to run processing.')
    area_scale = 'msoa'
    area_codes = msoa

    if feature_layer == 'buildings':
        rstring = 'mastermap/buildings?export_format=geojson-zip&scale=%s&building_year=%s' % (area_scale, data_year)

        # download data and build dataframe
        gdf = download_data(query=rstring, area_codes=area_codes, auth_username=auth_username, auth_password=auth_password, debug=debug)

        gdf = gdf.replace('NULL', '0')
        gdf['res_count'] = gdf['res_count'].astype('int64')
        gdf['nonres_count'] = gdf['nonres_count'].astype('int64')
        gdf['number_of_floors'] = gdf['number_of_floors'].astype('int64')
        gdf.drop(['toid_number','height_toroofbase','floor_area','building_ratio','number_of_floors'], axis=1)

        print('Information: Saving output - %s' %output_name)
        gdf.to_file(os.path.join(output_dir,'%s.gpkg' %output_name), driver="GPKG")

    elif feature_layer == 'water-bodies':

        classification_codes = '10089' #inland water, area
        rstring = 'mastermap/areas?classification_codes=%s&export_format=geojson-zip&scale=%s&year=%s' % (classification_codes, area_scale, data_year)

        # download data and build geodataframe
        gdf = download_data(query=rstring, area_codes=area_codes, auth_username=auth_username, auth_password=auth_password, debug=debug)

        # any processing required before saving the data file
        gdf = gdf.replace('NULL', '0')
        #gdf['res_count'] = gdf['res_count'].astype('int64')
        #gdf.drop([''], axis=1)

        print('Information: Saving output - %s' %output_name)
        gdf.to_file(os.path.join(output_dir,'%s.gpkg' %output_name), driver="GPKG")

    elif feature_layer == 'developed-land':
        # we get all the data, then filter it - this may need to change

        classification_codes = 'all'
        rstring = 'mastermap/areas?classification_codes=%s&export_format=geojson-zip&scale=%s&year=%s&flatten_lists=true' % (
        classification_codes, area_scale, data_year)

        # download data and build geodataframe
        gdf = download_data(query=rstring, area_codes=area_codes, auth_username=auth_username, auth_password=auth_password, debug=debug)

        if debug: print(gdf.columns)
        if debug: print(len(gdf.index))

        # any processing required before saving the data file
        # select only polygons we want
        gdf_land = gdf.loc[gdf['theme'] == 'Land,']
        gdf_result = gdf_land.loc[gdf_land['make'] == 'Multiple']
        gdf_land = gdf_land.loc[gdf_land['make'] == 'Manmade']

        # buildings
        gdf_blds = gdf.loc[gdf['descriptive_group'] == 'Building,']
        gdf_blds = gdf_blds.loc[gdf_blds['make'] == 'Manmade']

        # rail
        gdf_rail = gdf.loc[gdf['descriptive_group'] == 'Rail,']
        gdf_rail = gdf_rail.loc[gdf_rail['make'] == 'Manmade']

        # roads
        gdf_roads_ = gdf.loc[gdf['descriptive_group'] == 'Road Or Track,']
        gdf_roads = gdf_roads_.loc[gdf_roads_['make'] == 'Manmade']
        gdf_roads.append(gdf_roads_.loc[gdf_roads_['make'] == 'Unknown'])

        # roadside
        gdf_roadside = gdf.loc[gdf['descriptive_group'] == 'Roadside,']
        gdf_roadside = gdf_roadside.loc[gdf_roadside['make'] == 'Natural']

        # add all layers together
        gdf_result = gdf_result.append(gdf_land).append(gdf_blds).append(gdf_rail).append(gdf_roads).append(gdf_roadside)

        # any other processing to data
        gdf_result = gdf_result.replace('NULL', '0')
        #gdf['res_count'] = gdf['res_count'].astype('int64')
        #gdf.drop([''], axis=1)

        print('Information: Saving output - %s' %output_name)
        gdf_result.to_file(os.path.join(output_dir,'%s.gpkg' %output_name), driver="GPKG")

    elif feature_layer == 'developed-land-less':
        # we get all the data, then filter it - this may need to change
        # includes all layers as developed-land layer with the exception of roads being ignored

        classification_codes = 'all'
        rstring = 'mastermap/areas?classification_codes=%s&export_format=geojson-zip&scale=%s&year=%s&flatten_lists=true' % (
        classification_codes, area_scale, data_year)

        # download data and build geodataframe
        gdf = download_data(query=rstring, area_codes=area_codes, auth_username=auth_username, auth_password=auth_password, debug=debug)

        if debug: print(gdf.columns)
        #print(gdf.head)
        if debug: print(len(gdf.index))

        # any processing required before saving the data file
        # select only polygons we want
        gdf_land = gdf.loc[gdf['theme'] == 'Land,']
        #print(len(gdf_land.index))
        gdf_result = gdf_land.loc[gdf_land['make'] == 'Multiple']
        gdf_land = gdf_land.loc[gdf_land['make'] == 'Manmade']
        #print(len(gdf_result.index))

        # buildings
        gdf_blds = gdf.loc[gdf['descriptive_group'] == 'Building,']
        gdf_blds = gdf_blds.loc[gdf_blds['make'] == 'Manmade']

        # rail
        gdf_rail = gdf.loc[gdf['descriptive_group'] == 'Rail,']
        gdf_rail = gdf_rail.loc[gdf_rail['make'] == 'Manmade']

        # roads
        #gdf_roads_ = gdf.loc[gdf['descriptive_group'] == 'Road Or Track,']
        #print(len(gdf_roads_.index))
        #gdf_roads = gdf_roads_.loc[gdf_roads_['make'] == 'Manmade']
        #gdf_roads.append(gdf_roads_.loc[gdf_roads_['make'] == 'Unknown'])
        #print(len(gdf_roads.index))

        # roadside
        gdf_roadside = gdf.loc[gdf['descriptive_group'] == 'Roadside,']
        gdf_roadside = gdf_roadside.loc[gdf_roadside['make'] == 'Manmade']
        #print(len(gdf_roadside.index))

        # add all layers together
        gdf_result = gdf_result.append(gdf_land).append(gdf_blds).append(gdf_rail).append(gdf_roadside)

        # any other processing to data
        gdf_result = gdf_result.replace('NULL', '0')
        #gdf['res_count'] = gdf['res_count'].astype('int64')
        #gdf.drop([''], axis=1)

        print('Information: Saving output - %s' %output_name)
        gdf_result.to_file(os.path.join(output_dir,'%s.gpkg' %output_name), driver="GPKG")

main()
