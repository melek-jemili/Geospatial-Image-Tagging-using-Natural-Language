"""Geospatial processing and visualization."""

import folium
from folium import plugins
import pandas as pd
import logging
import numpy as np

logger = logging.getLogger(__name__)

class GeoProcessor:
    """Process and visualize geospatial data."""
    
    def __init__(self):
        self.colors = [
            'red', 'blue', 'green', 'purple', 'orange',
            'darkred', 'darkblue', 'darkgreen', 'pink', 'cadetblue'
        ]
    
    def create_map(self, df: pd.DataFrame) -> folium.Map:
        """Créer simple map (pour pipeline classique)."""
        
        logger.info("Creating simple map...")
        
        center_lat = df['latitude'].mean()
        center_lon = df['longitude'].mean()
        
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        # Ajouter markers
        for idx, row in df.iterrows():
            popup_text = f"""
            <b>{row['image_name']}</b><br>
            Lat: {row['latitude']:.4f}<br>
            Lon: {row['longitude']:.4f}<br>
            """
            
            popup = folium.Popup(popup_text, max_width=300)
            
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=6,
                popup=popup,
                color='blue',
                fill=True,
                fillColor='blue',
                fillOpacity=0.6,
                weight=2
            ).add_to(m)
        
        logger.info("Simple map created")
        return m
    
    def create_map_with_clusters(self, df: pd.DataFrame) -> folium.Map:
        """Créer carte interactive avec clusters colorés."""
        
        logger.info("Creating map with clusters...")
        
        # Centre
        center_lat = df['latitude'].mean()
        center_lon = df['longitude'].mean()
        
        # Créer map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        # Ajouter markers par cluster
        if 'cluster' in df.columns:
            unique_clusters = sorted(df['cluster'].unique())
            
            for cluster_id in unique_clusters:
                cluster_df = df[df['cluster'] == cluster_id]
                color = self.colors[int(cluster_id) % len(self.colors)]
                
                logger.info(f"  Cluster {cluster_id}: {len(cluster_df)} images ({color})")
                
                # Feature group
                fg = folium.FeatureGroup(name=f"Cluster {cluster_id} ({len(cluster_df)} images)")
                
                for idx, row in cluster_df.iterrows():
                    # Popup
                    popup_text = f"""
                    <b>{row['image_name']}</b><br>
                    Lat: {row['latitude']:.4f}<br>
                    Lon: {row['longitude']:.4f}<br>
                    Cluster: {int(row['cluster'])}<br>
                    """
                    
                    if 'tags' in row and row['tags']:
                        popup_text += f"Tags: {row['tags']}<br>"
                    
                    if 'objects' in row and row['objects']:
                        popup_text += f"Objects: {row['objects']}<br>"
                    
                    popup = folium.Popup(popup_text, max_width=300)
                    
                    # Marker
                    folium.CircleMarker(
                        location=[row['latitude'], row['longitude']],
                        radius=8,
                        popup=popup,
                        color=color,
                        fill=True,
                        fillColor=color,
                        fillOpacity=0.7,
                        weight=2
                    ).add_to(fg)
                
                fg.add_to(m)
        
        else:
            # Sans clusters
            logger.info("No clusters, adding all markers...")
            
            for idx, row in df.iterrows():
                popup_text = f"""
                <b>{row['image_name']}</b><br>
                Lat: {row['latitude']:.4f}<br>
                Lon: {row['longitude']:.4f}<br>
                """
                
                if 'tags' in row and row['tags']:
                    popup_text += f"Tags: {row['tags']}<br>"
                
                popup = folium.Popup(popup_text, max_width=300)
                
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=6,
                    popup=popup,
                    color='blue',
                    fill=True,
                    fillColor='blue',
                    fillOpacity=0.6,
                    weight=2
                ).add_to(m)
        
        # Layer control
        folium.LayerControl().add_to(m)
        
        # Titre
        title_html = '''
        <div style="position: fixed; 
                    top: 10px; left: 50px; width: 450px; height: 90px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px; border-radius: 5px;">
            <b>Spatial Georeferencing Map</b><br>
            Geographic Clustering with Quantum Optimization<br>
            <small>Images: %d | Clusters: %d</small>
        </div>
        ''' % (len(df), df['cluster'].nunique() if 'cluster' in df.columns else 1)
        
        m.get_root().html.add_child(folium.Element(title_html))
        
        logger.info("Map with clusters created successfully")
        
        return m