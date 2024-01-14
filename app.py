from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import DictCursor
from flask_cors import CORS  # Import CORS extension
import sys

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Database connection parameters
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASSWORD = 'admin'

# Connect to the PostGIS database
def connect_to_database():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn

# API endpoint to compute zonal statistics for a polygon geometry
@app.route('/get_zonal_stats', methods=['POST'])
def get_zonal_stats():
    # Get the GeoJSON features from the request
    data = request.get_json()
    features = data['features']
    import json
    # Extract the geometry from each feature and convert it into a valid GeoJSON string
    geometries_str = [json.dumps({"type": "Feature", "coordinates": feature['geometry']['coordinates'], "type": "Polygon"}) for feature in features]
    # print(geometries_str, file=sys.stderr)
    # Connect to the database
    try:
        conn = connect_to_database()
        cursor = conn.cursor(cursor_factory=DictCursor)
    except Exception as e:
        return jsonify({"error": "Database connection error: " + str(e)})

    # SQL query to compute zonal statistics
    for geometry_str in geometries_str:
        try:
            query = f"""
                WITH polygon AS (
                    SELECT ST_SetSRID(ST_GeomFromGeoJSON('{geometry_str}'), 4326) AS geom
                ),
                stats AS (
                    SELECT (stats).* FROM (
                        SELECT
                            ST_valuecount(ST_Clip(r.rast, p.geom, TRUE)::raster, 1) AS stats
                        FROM rasters.esri_lcover_2022 r
                        JOIN polygon p ON ST_Intersects(r.rast, p.geom)
                    ) q
                )
                SELECT value, (sum(count) * 100)/10000 AS count FROM stats
                GROUP BY value
                ORDER BY count DESC
            """
            # print(query, file=sys.stderr)
            cursor.execute(query)
            results = cursor.fetchall()  # Fetch all rows
            # print(results, file=sys.stderr)

        except Exception as e:
            cursor.close()
            conn.close()
            return jsonify({"error": "SQL query execution error: " + str(e)})

    

    if results:
        # Extract 'value' and 'count' columns from results
        zonal_stats = [{"value": row['value'], "count": row['count']} for row in results]
        return jsonify({"zonal_statistics": zonal_stats})
    else:
        return jsonify({"error": "No data found for the specified polygon geometry"})



if __name__ == '__main__':
    app.run(debug=True)
