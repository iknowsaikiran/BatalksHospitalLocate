from flask import Flask, render_template, request, redirect, url_for, session, flash, json, jsonify
from flask_mysqldb import MySQL
from math import radians, cos, sin, asin, sqrt
from flask_mysqldb import MySQL
import logging
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'


# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root123'
app.config['MYSQL_DB'] = 'hospital'

mysql = MySQL(app)

# Function to calculate distance between two coordinates using Haversine formula
# Function to calculate distance between two coordinates using Haversine formula
from math import radians, sin, cos, sqrt, atan2

def haversine(lat1, lon1, lat2, lon2):
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat / 2)*2 + cos(lat1) * cos(lat2) * sin(dlon / 2)*2
    
    # Clamp a between 0 and 1 to avoid math domain errors
    a = max(0, min(1, a))
    
    c = 2 * atan2(sqrt(a), sqrt(1 - a))  # Use atan2 instead of asin
    
    radius = 6371  # Radius of Earth in kilometers
    distance = radius * c
    
    return distance




@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # Handle POST request (when the geolocation data is sent)
        data = request.get_json()
        print("Received data:", data)  # Add this line to verify if the data is being received
        user_latitude = float(data.get('latitude'))
        user_longitude = float(data.get('longitude'))

        # Debugging: print the received values
        print(f"Received Latitude: {user_latitude}")
        print(f"Received Longitude: {user_longitude}")

        cur = mysql.connection.cursor()
        cur.execute("SELECT hospital_id,hospital_name, timings, years_since_established, opcard_price, latitude, longitude FROM hospitals")
        hospitals = cur.fetchall()
        print(hospitals)

        nearby_hospitals = []
        for hospital in hospitals:
            hospital_id,hospital_name, timings, years_since_established, opcard_price, lat, lon = hospital
            distance = haversine(user_latitude, user_longitude, lat, lon)
            if distance <= 5:
                nearby_hospitals.append({
                    'hospital_id': hospital_id,
                    'hospital_name': hospital_name,
                    'timings': timings,
                    'years_since_established': years_since_established,
                    'opcard_price': opcard_price,
                    'distance': round(distance, 2)
                })

        print("Nearby hospitals:", nearby_hospitals)

        return jsonify(nearby_hospitals)  # Return hospitals as JSON to the frontend

    # If GET request (when the page is first loaded)
    return render_template('index.html', hospitals=[])



# register the hosiptal in register table
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Check if user is logged in
        if 'username' not in session:
            flash("Please log in to register a hospital.", "info")
            return redirect(url_for('signuplogin'))

        # Extract form data
        hospital_name = request.form.get('hospitalName')
        status = request.form.get('status')
        patient_count = request.form.get('patientcount')
        description = request.form.get('description')
        experience = request.form.get('experience')
        address = request.form.get('address')
        timings = int(request.form.get('timings'))
        price = int(request.form.get('price'))
        open_days = request.form.get('opendays')

        # Extract category (stored as JSON string)
        selected_categories_json = request.form.get('selectedCategoriesJson')
        selected_categories = ','.join(json.loads(selected_categories_json)) if selected_categories_json else None

        # Handle the image upload
        uploaded_image = request.files.get('upload_hospital_image')
        if uploaded_image and uploaded_image.filename != '':
            filename = secure_filename(uploaded_image.filename)  # Use secure filename

            # Set the image directory
            upload_dir = "static/uploads"
            image_path = os.path.join(upload_dir, filename)

            # Ensure the directory exists
            os.makedirs(upload_dir, exist_ok=True)

            # Save the image file to the directory
            uploaded_image.save(image_path)

            # Save the relative path to the image (excluding the static folder prefix)
            image_path = os.path.join('uploads', filename)
        else:
            image_path = None

        # Save form data to the database
        try:
            cur = mysql.connection.cursor()
            sql = """
            INSERT INTO hospital.register (
                hospital_name, availability_status, description, 
                number_of_patients_deals_with, years_of_experience, address, 
                hospital_timing, op_price, hospital_open_days, category, image_path
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(sql, (
                hospital_name, status, description, 
                int(patient_count), int(experience), address, 
                timings, price, open_days, selected_categories, image_path
            ))
            mysql.connection.commit()  # Commit the transaction
            cur.close()
            flash("Hospital registered successfully!", "success")
        except Exception as e:
            mysql.connection.rollback()  # Rollback the transaction in case of an error
            flash(f"An error occurred: {e}", "error")
            print(f"An error occurred: {e}")

    return render_template('register.html')

#To get the hospital list from register table
@app.route('/hospitallist')
def hospitallist():   

    if 'username' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM register")
        data = cur.fetchall()
        cur.close()
        print(data)
        return render_template('hospitallist.html',users=data)
    else:
        return redirect(url_for('index'))


@app.route('/category')
def category():
    category_type = request.args.get('type')
    
    if category_type is None:
        return render_template('category.html', hospitals=[])
    
    username = session.get('username')
    
    # Fetch hospitals and check if they're favorites for the logged-in user
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT h.hospital_id, h.hospital_name, h.timings, h.years_since_established, h.opcard_price,
               CASE WHEN f.hospital_id IS NOT NULL THEN TRUE ELSE FALSE END AS is_favorite
        FROM hospitals h
        LEFT JOIN favourites f ON h.hospital_id = f.hospital_id AND f.username = %s
        WHERE h.category = %s
    """, (username, category_type))
    
    hospitals = cur.fetchall()
    cur.close()
    
    return render_template('bookappointment.html', hospitals=hospitals, category=category_type)





def toggle_favorite(hospital_id, action):
    """Helper function to add or remove a hospital from favorites."""
    username = session['username']
    try:
        cur = mysql.connection.cursor()
        if action == 'add':
            cur.execute("SELECT * FROM favourites WHERE username = %s AND hospital_id = %s", (username, hospital_id))
            existing_fav = cur.fetchone()
            if existing_fav:
                # Remove from favorites
                cur.execute("DELETE FROM favourites WHERE username = %s AND hospital_id = %s", (username, hospital_id))
                flash("Hospital removed from your favorites.", "success")
            else:
                # Add to favorites
                cur.execute("INSERT INTO favourites (username, hospital_id) VALUES (%s, %s)", (username, hospital_id))
                flash("Hospital added to your favorites!", "success")
        elif action == 'remove':
            cur.execute("DELETE FROM favourites WHERE username = %s AND hospital_id = %s", (username, hospital_id))
            flash("Hospital removed from your favorites.", "success")
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        mysql.connection.rollback()  # Rollback the transaction in case of an error
        logging.error(f"Error in toggle_favorite: {e}")
        flash(f"An error occurred: {e}", "error")


@app.route('/add_favourite', methods=['POST'])
def add_favourite():
    if 'username' not in session:
        return jsonify({'success': False}), 401  # Unauthorized access

    hospital_id = int(request.form.get('hospital_id'))  # Convert to int
    toggle_favorite(hospital_id, 'add')
    
    return jsonify({'success': True})  # Return JSON response

@app.route('/remove_favourite', methods=['POST'])
def remove_favourite():
    if 'username' not in session:
        return jsonify({'success': False}), 401  # Unauthorized access

    hospital_id = int(request.form.get('hospital_id'))  # Convert to int
    toggle_favorite(hospital_id, 'remove')
    
    return jsonify({'success': True})  # Return JSON response




@app.route('/favourite')
def favourite():
    if 'username' not in session:
        flash("Please log in to view your favorites.", "info")
        return redirect(url_for('signuplogin'))

    username = session['username']
    try:
        cur = mysql.connection.cursor()
        cur.execute(""" 
            SELECT h.hospital_id, h.hospital_name, h.timings, h.years_since_established, h.opcard_price 
            FROM favourites f 
            JOIN hospitals h ON f.hospital_id = h.hospital_id
            WHERE f.username = %s
        """, (username,))
        favourite_hospitals = cur.fetchall()
        cur.close()
    except Exception as e:
        logging.error(f"Error fetching favorites: {e}")
        flash(f"An error occurred: {e}", "error")
        favourite_hospitals = []

    return render_template('favourite.html', hospitals=favourite_hospitals)



@app.route('/about_us')
def about_us():
    return render_template('about-us.html')

@app.route('/userdetails')
def userdetails():
    return render_template('userdetails.html')



# Setup logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/bookappointment', methods=['GET', 'POST'])
def bookappointment():
    if request.method == 'POST':
        try:
            appointment_date = request.form.get('appointmentDate', '').strip()
            reason = request.form.get('reason', '').strip()

            if not appointment_date:
                return jsonify({"error": "Appointment date is required."}), 400
            
            if 'firstName' in request.form:
                # New Patient Form
                first_name = request.form.get('firstName', '').strip()
                last_name = request.form.get('lastName', '').strip()
                phone_number = request.form.get('number', '').strip()
                address = request.form.get('address', '').strip()

                cur = mysql.connection.cursor()
                cur.execute("SELECT * FROM newpatients WHERE phone_number = %s", (phone_number,))
                patient = cur.fetchone()

                if patient:
                    cur.close()
                    return jsonify({"error": "Patient already exists with this phone number."}), 400

                cur.execute("INSERT INTO newpatients (first_name, last_name, phone_number, address, reason, appointment_date) VALUES (%s, %s, %s, %s, %s, %s)", 
                            (first_name, last_name, phone_number, address, reason, appointment_date))
                mysql.connection.commit()
                cur.close()
                return redirect(url_for('signuplogin'))  # Redirect to signup page
            
            elif 'opName' in request.form:
                # Existing Patient Form
                op_name = request.form.get('opName', '').strip()
                op_phone = request.form.get('opPhone', '').strip()
                op_number = request.form.get('opNumber', '').strip()

                cur = mysql.connection.cursor()
                cur.execute("SELECT * FROM existingpatients WHERE op_number = %s AND phone_number = %s ", (op_number, op_phone))
                existing_patient = cur.fetchone()
                
                if existing_patient:
                    cur.execute("INSERT INTO appointments (op_number, appointment_date, reason) VALUES (%s, %s, %s)",
                                (op_number, appointment_date, reason))
                    mysql.connection.commit()
                    cur.close()
                    return redirect(url_for('signuplogin'))  # Redirect to login page
                else:
                    cur.close()
                    return jsonify({"error": "Patient does not exist with these details."}), 400

        except Exception as e:
            app.logger.error(f"Error processing request: {e}")
            return jsonify({"error": f"Internal server error. Please try again later. Details: {str(e)}"}), 500

    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')
    
from werkzeug.security import generate_password_hash, check_password_hash

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/header')
def header():
    return render_template('header.html')
@app.route('/signuplogin', methods=['GET', 'POST'])
def signuplogin():
    if request.method == 'POST':
        username = request.form.get('username')
        mail = request.form.get('mail')
        password = request.form.get('password')
        action = request.form.get('action')

        if action == 'login':
            # Login logic
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM signup WHERE username = %s AND password = %s", (username, password))
            user = cur.fetchone()
            cur.close()

            if user:
                session['username'] = username
                return redirect(url_for('index'))  # Redirect to index.html page
            else:
                flash('Incorrect username or password', 'error')
                return redirect(url_for('signuplogin'))

        elif action == 'signup':
            # Signup logic
            if not username or not mail or not password:
                flash('All fields are required!', 'error')
                return redirect(url_for('signuplogin'))

            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM signup WHERE username = %s", (username,))
            existing_user = cur.fetchone()

            if existing_user:
                flash('Username already exists! Please choose a different one.', 'error')
                cur.close()
                return redirect(url_for('signuplogin'))

            # No password hashing for this example (you should hash passwords in production)
            cur.execute("INSERT INTO signup (username, mail, password) VALUES (%s, %s, %s)", (username, mail, password))
            mysql.connection.commit()
            cur.close()

            flash('Signup successful! You can now log in.', 'success')
            return redirect(url_for('signuplogin'))

    # If the request method is GET, render the signuplogin page
    return render_template('signuplogin.html')


@app.route('/logout')
def logout():
    # Remove the username from the session
    session.pop('username', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))



@app.route('/profile')
def profile():
    # Check if the user is logged in
    if 'username' not in session:
        flash("Please log in to view your profile.", "info")
        return redirect(url_for('signuplogin'))
    
    username = session['username']
    
    # Fetch user email
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT mail FROM signup WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        
        user_email = user[0] if user else ""
    except Exception as e:
        flash(f"An error occurred: {e}", "error")
        user_email = ""
    
    # Fetch favorite hospitals
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT h.hospital_name, h.timings, h.years_since_established, h.opcard_price
            FROM favourites f
            JOIN hospitals h ON f.hospital_id = h.slno
            WHERE f.username = %s
        """, (username,))
        favourite_hospitals = cur.fetchall()
        cur.close()
    except Exception as e:
        flash(f"An error occurred: {e}", "error")
        favourite_hospitals = []

    return render_template('profile.html', user_email=user_email, hospitals=favourite_hospitals)


@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'username' not in session:
        flash("Please log in to update your profile.", "info")
        return redirect(url_for('signuplogin'))

    name = session['username']
    
    username=request.form.get('name')
    email = request.form.get('email')
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')


    try:
        cur = mysql.connection.cursor()

        # Check if the current password is correct
        cur.execute("SELECT password FROM signup WHERE username = %s", (username,))
        stored_password = cur.fetchone()
        if stored_password and stored_password[0] == current_password:
            if new_password == confirm_password:
                cur.execute("use hospital; UPDATE signup SET username= %s mail = %s, password = %s WHERE username = %s", (username,email, new_password, name))
                mysql.connection.commit()
                flash("Profile updated successfully!", "success")
            else:
                flash("New passwords do not match.", "error")
        else:
            flash("Current password is incorrect.", "error")

        cur.close()
    except Exception as e:
        mysql.connection.rollback()
        flash(f"An error occurred: {e}", "error")

    return redirect(url_for('profile'))





if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8520, debug=True)