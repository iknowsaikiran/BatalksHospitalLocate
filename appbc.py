from flask import Flask, render_template, request, redirect, url_for, session, flash, json, jsonify
from flask_mysqldb import MySQL
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'hospital'

mysql = MySQL(app)

# Function to calculate distance between two coordinates using Haversine formula
def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat1 - lat2
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r


@app.route('/')
def home():
    user_lat = request.args.get('latitude', type=float)
    user_lon = request.args.get('longitude', type=float)

    if user_lat is None or user_lon is None:
        return render_template('index.html', hospitals=[])

    cur = mysql.connection.cursor()
    cur.execute("SELECT hospital_name, timings, years_since_established, opcard_price, latitude, longitude FROM hospitals")
    hospitals = cur.fetchall()

    nearby_hospitals = []
    for hospital in hospitals:
        hospital_name, timings, years_since_established, opcard_price, lat, lon = hospital
        distance = haversine(user_lat, user_lon, lat, lon)
        if distance <= 5:
            nearby_hospitals.append({
                'hospital_name': hospital_name,
                'timings': timings,
                'years_since_established': years_since_established,
                'opcard_price': opcard_price,
                'distance': round(distance, 2)
            })
    
    print("Nearby hospitals:", nearby_hospitals)

    return render_template('index.html', hospitals=nearby_hospitals)

@app.route('/category')
def category():
    return render_template('category.html')

@app.route('/about_us')
def about_us():
    return render_template('about-us.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8520, debug=True)