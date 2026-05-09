import geopandas as gpd
from shapely.geometry import Point
import folium

class GeoProcessor:
    def create_map(self, images_df):
        m = folium.Map(
            location=[images_df['latitude'].mean(), images_df['longitude'].mean()],
            zoom_start=10
        )
        
        for idx, row in images_df.iterrows():
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=f"{row['image_name']}<br>{row.get('tags', '')}"
            ).add_to(m)
        
        return m