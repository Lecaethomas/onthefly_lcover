# C:\Program Files\PostgreSQL\15\bin> "raster2pgsql.exe" -s 4326 -N 0 -t 2700x2700 -I -C -M -d C:\Users\tl_59\Downloads\31T_20220101-20230101_4326.tif rasters.esri_lcover_2022 |  "psql.exe" -d postgres -h localhost -U postgres -p 5432 -W
# curl -X POST -H "Content-Type: application/json" -d "{\"minx\": 1.3359375, \"miny\": 43.512335, \"maxx\": 1.532135, \"maxy\": 43.697165}" http://127.0.0.1:5000/get_zonal_stats
from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import DictCursor

app = Flask(__name__)

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

# API endpoint to compute zonal statistics for a bounding box
@app.route('/get_zonal_stats', methods=['POST'])
def get_zonal_stats():
    # Get the bounding box parameters from the request
    data = request.get_json()
    minx = data['minx']
    miny = data['miny']
    maxx = data['maxx']
    maxy = data['maxy']

    # Connect to the database
    try:
        conn = connect_to_database()
        cursor = conn.cursor(cursor_factory=DictCursor)
    except Exception as e:
        return jsonify({"error": "Database connection error: " + str(e)})

    # SQL query to compute zonal statistics
    try:
        query = f"""
            WITH bounding_box AS (
                SELECT ST_MakeEnvelope({minx}, {miny}, {maxx}, {maxy}, 4326) AS geom
            )
            SELECT (stats).* FROM (
                SELECT
                    ST_valuecount(ST_Clip(r.rast, bb.geom, TRUE)::raster, 1) AS stats
                FROM rasters.esri_lcover_2022 r
                RIGHT JOIN bounding_box bb ON ST_Intersects(r.rast, bb.geom)
            ) q
        """
        
        cursor.execute(query)
        results = cursor.fetchall()  # Fetch all rows
    except Exception as e:
        cursor.close()
        conn.close()
        return jsonify({"error": "SQL query execution error: " + str(e)})

    # Close the database connection
    cursor.close()
    conn.close()

    if results:
        # Extract 'value' and 'count' columns from results
        zonal_stats = [{"value": row['value'], "count": row['count']} for row in results]
        return jsonify({"zonal_statistics": zonal_stats})
    else:
        return jsonify({"error": "No data found for the specified bounding box"})


if __name__ == '__main__':
    app.run(debug=True)
