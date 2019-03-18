import folium
import folium.plugins as plugins
import json
import pandas as pd
from area import area
from collections import Counter

# from pprint import pprint

# print(folium.__version__)

trees = pd.read_csv('trees.csv')
#trees['planted_date'].unique()
trees = trees[trees['planted_date'] != '1190-06-01']  ##remove problematic samples

treecount=Counter(trees['neighbourhood_name'])  ##count number of entries for each neighbourhood name (equivalent to number of trees)
treecount=pd.DataFrame.from_dict(treecount, orient='index').reset_index()  ##convert treecount to a dataframe
treecount=treecount.rename(columns={'index':'neighbourhood_name', 0:'treecount'})  ##rename columns
treecount['neighbourhood_name']=treecount['neighbourhood_name'].str.upper()  ##convert names to UPPER case to match with bdry
#treecount.to_csv('treecount.csv')  ##output csv for checking


with open('bdry.geojson', "r") as bdry_file: ##open file in read mode ("r")
    bdry=json.load(bdry_file)

with open('area.csv', 'w') as area_file:  ##creates 'area.csv' and opens in write mode ('w')
    for x in bdry['features']:
        print(x['properties']['name'], ',', area(x['geometry']), file=area_file) ##prints to area_file
area_file.close()  ##closes area_file after for loop to finalize file

area_df = pd.read_csv('area.csv', names=['neighbourhood_name','area'])  ##reads area.csv and adds column names

area_df['neighbourhood_name']=area_df['neighbourhood_name'].map(lambda x: x.strip())  ##removes trailing and leading spaces from 'neighbourhood_name'

treedens = pd.merge(treecount, area_df, on = 'neighbourhood_name', how = 'right')
treedens['area'] = treedens['area']/1e6
treedens['treepersqkm'] = treedens['treecount']/treedens['area']

##following method is much faster than populating a list by iterating row-wise through the main dataframe
lat = trees.latitude[trees.latitude.notnull()].values
long = trees.longitude[trees.longitude.notnull()].values

spec = trees.species[trees.longitude.notnull()]
spec = spec.str.split(',', expand=True)
spec = spec[1] + ' ' + spec[0]

hlth = trees.condition_percent.values

size = trees.diameter_breast_height.values

tree_vals = [list(a) for a in zip(lat, long, hlth, size)]
tree_vals = pd.DataFrame(tree_vals, columns=['lat', 'lng', 'hlth', 'size'])
tree_vals = tree_vals.values

callback = """
function (row) {
    var hlthcol;
        if(row[2] > 50 && row[2] < 75){
            hlthcol = "orange";
            } else if(row[2] > 75){
                hlthcol = "green";
                } else {hlthcol = "black";}
    var treesz;
        if(row[3] == 0){
            treesz = 1;
            } else {treesz = (Math.log(row[3])*2);}
    var marker;
    marker = L.circleMarker(new L.LatLng(row[0], row[1]), {color:hlthcol, radius:treesz});
    marker.bindPopup("<b>Health =</b> " + row[2] +"% <br>\
                      <b>Diameter at breast height =</b> " + row[3] + " cm")
    return marker;
};
"""

fmap = folium.Map(location=[53.52,-113.5]
                  , zoom_start=10.5
                  , prefer_canvas=True
                  #, width = 600, height = 600
                 )

fmap_chor = folium.Choropleth(geo_data = bdry
                              , data = treedens
                              , columns = ['neighbourhood_name','treepersqkm'] ##first value is key in the dataframe, second is the data to display
                              , key_on = 'feature.properties.name' ##name of key in json file
                              , fill_color = 'BuPu'
                              , legend_name = '# of trees per sq. km'
                              , highlight=True
                              , name = 'Neighbourhood Tree Density'
                             )

fmap_fmc = plugins.FastMarkerCluster(tree_vals
                                     , callback=callback
                                     , options={'spiderfyOnMaxZoom': False
                                                , 'disableClusteringAtZoom': 17 # #will only show individual points at this zoom level or higher
                                                , 'chunkedLoading': True
                                               }
                                     , name='Tree Locations'
                                    )

fmap_chor.add_to(fmap)
fmap_fmc.add_to(fmap)
folium.LayerControl().add_to(fmap)

fmap.save('index.html')
