import folium
import folium.plugins as plugins
import json
import pandas as pd
from area import area
from collections import Counter

# from pprint import pprint

# print(folium.__version__)

trees = pd.read_csv('data-trees.csv')
trees = trees[trees['planted_date'] != '1190-06-01']  # remove problematic samples

# count number of entries for each neighbourhood name (equivalent to number of
# trees), convert to dataframe, rename columns and convert to uppercase.
treecount = Counter(trees['neighbourhood_name'])
treecount = pd.DataFrame.from_dict(treecount, orient='index').reset_index()
treecount = treecount.rename(columns={'index': 'neighbourhood_name', 0: 'treecount'})
treecount['neighbourhood_name'] = treecount['neighbourhood_name'].str.upper()


# open boundary file in read mode ("r")
with open('data-bdry.geojson', "r") as bdry_file:
    bdry = json.load(bdry_file)

# creates 'area.csv' and opens in write mode ('w')
# prints neighbourhood name and calculated area to file
# closes area_file after for loop to finalize file
with open('area.csv', 'w') as area_file:
    for x in bdry['features']:
        print(x['properties']['name'], ',', area(x['geometry']), file=area_file)
area_file.close()

# reads area.csv and adds column names
# removes trailing and leading spaces from entries in 'neighbourhood_name'
area_df = pd.read_csv('area.csv', names=['neighbourhood_name','area'])
area_df['neighbourhood_name'] = area_df['neighbourhood_name'].map(lambda x: x.strip())

treedens = pd.merge(treecount, area_df, on='neighbourhood_name', how='right')
treedens['area'] = treedens['area']/1e6
treedens['treepersqkm'] = treedens['treecount']/treedens['area']

# following method is much faster than populating a list by
# iterating row-wise through the main dataframe
lat = trees.latitude[trees.latitude.notnull()].values
long = trees.longitude[trees.longitude.notnull()].values

spec = trees.species[trees.longitude.notnull()]
spec = spec.str.split(',', expand=True)
spec = spec[1] + ' ' + spec[0]

cond = trees.condition_percent.values

size = trees.diameter_breast_height.values

tree_vals = [list(a) for a in zip(lat, long, cond, size, spec)]
tree_vals = pd.DataFrame(tree_vals, columns=['lat', 'lng', 'cond', 'size', 'spec'])
tree_vals = tree_vals.values

# callback for custom marker action
# size is scaled down (treesz = ln(size)*2)
callback = """
function (row) {
    var condtxt;
    var condcol;
        if(row[2] > 50 && row[2] < 69){
            condtxt = "Average";
            condcol = "orange";
            } else if(row[2] > 69){
                condtxt = "Above average";
                condcol = "green";
                } else {
                    condtxt = "Below Average";
                    condcol = "crimson";}
    var treesz;
        if(row[3] == 0){
            treesz = 1;
            } else {treesz = (Math.log(row[3])*2);}
    var marker;
    marker = L.circleMarker(new L.LatLng(row[0], row[1]), {color:condcol, radius:treesz});
    marker.bindPopup("<b>Species:</b> " + row[4] +"<br>\
		     <b>Condition:</b> " + condtxt + " (" + row[2] +"%) <br>\
                     <b>Diameter at breast height:</b> " + row[3] + " cm")
    return marker;
};
"""

fmap = folium.Map(location=[53.52, -113.5]
                  , zoom_start=10.5
                  , prefer_canvas=True
                  )

fmap_chor = folium.Choropleth(geo_data = bdry
                              , data = treedens
                              # first value is key in the dataframe, second is the data to display
                              , columns = ['neighbourhood_name','treepersqkm']
                              # name of key in json file
                              , key_on = 'feature.properties.name'
                              , fill_color = 'BuPu'
                              , legend_name = '# of trees per sq. km'
                              , highlight=True
                              , name = 'Neighbourhood Tree Density'
                             )

fmap_fmc = plugins.FastMarkerCluster(tree_vals
                                     , callback=callback
                                     , options={'spiderfyOnMaxZoom': False
                                     # will only show individual points at this zoom level or higher
                                                , 'disableClusteringAtZoom': 17
                                                , 'chunkedLoading': True
                                               }
                                     , name='Tree Locations'
                                    )

fmap_chor.add_to(fmap)
fmap_fmc.add_to(fmap)
folium.LayerControl().add_to(fmap)

fmap.save('index.html')
