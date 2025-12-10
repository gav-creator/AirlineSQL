from flask import Flask, request, jsonify
app = Flask(__name__)

# ---------------------------
# DATABASE CONNECTION
# ---------------------------
from dbConnect import get_db_connection
db = get_db_connection()
cursor = db.cursor(dictionary=True)

# ---------------------------
# HELPER FUNCTIONS
# ---------------------------
def validate_fields(data, required_fields):
    missing = [field for field in required_fields if field not in data or data[field] is None]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    return True, None

# ---------------------------
# PASSENGER ROUTES
# ---------------------------
@app.route('/passengers', methods=['POST'])
def create_passenger():
    data = request.json
    valid, error = validate_fields(data, ['Name', 'DateofBirth', 'Email'])
    if not valid:
        return jsonify({"error": error}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Passenger (Name, DateofBirth, Address, Phone, Email)
            VALUES (%s,%s,%s,%s,%s)
        """, (data['Name'], data['DateofBirth'], data.get('Address'), data.get('Phone'), data['Email']))
        conn.commit()
        passenger_id = cursor.lastrowid
        cursor.close()
        return jsonify({"PassengerID": passenger_id}), 201
    except Error as e:
        cursor.close()
        return jsonify({"error": str(e)}), 500

@app.route('/passengers/<int:passengerID>', methods=['GET'])
def get_passenger(passengerID):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Passenger WHERE PassengerID=%s", (passengerID,))
    passenger = cursor.fetchone()
    cursor.close()
    if passenger:
        return jsonify(passenger)
    return jsonify({"error": "Passenger not found"}), 404

@app.route('/passengers/<int:passengerID>', methods=['PUT'])
def update_passenger(passengerID):
    data = request.json
    valid, error = validate_fields(data, ['Name', 'DateofBirth', 'Email'])
    if not valid:
        return jsonify({"error": error}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Passenger SET Name=%s, DateofBirth=%s, Address=%s, Phone=%s, Email=%s
        WHERE PassengerID=%s
    """, (data['Name'], data['DateofBirth'], data.get('Address'), data.get('Phone'), data['Email'], passengerID))
    if cursor.rowcount == 0:
        cursor.close()
        return jsonify({"error": "Passenger not found"}), 404
    conn.commit()
    cursor.close()
    return jsonify({"message": "Passenger updated"})

@app.route('/passengers/<int:passengerID>', methods=['DELETE'])
def delete_passenger(passengerID):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Passenger WHERE PassengerID=%s", (passengerID,))
    if cursor.rowcount == 0:
        cursor.close()
        return jsonify({"error": "Passenger not found"}), 404
    conn.commit()
    cursor.close()
    return jsonify({"message": "Passenger deleted"})

# ---------------------------
# FLIGHT ROUTES
# ---------------------------
@app.route('/flights', methods=['POST'])
def create_flight():
    data = request.json
    required = ['FlightNumber', 'DepartureTime', 'ArrivalTime', 'DepartureAirport', 'ArrivalAirport', 'AirlineID']
    valid, error = validate_fields(data, required)
    if not valid:
        return jsonify({"error": error}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Flight (FlightNumber, DepartureTime, ArrivalTime, DepartureAirport, ArrivalAirport, AirlineID, ActualDepartureTime, ActualArrivalTime)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (data['FlightNumber'], data['DepartureTime'], data['ArrivalTime'], data['DepartureAirport'], data['ArrivalAirport'], data['AirlineID'], data.get('ActualDepartureTime'), data.get('ActualArrivalTime')))
    conn.commit()
    flight_id = cursor.lastrowid
    cursor.close()
    return jsonify({"FlightID": flight_id}), 201

@app.route('/flights', methods=['GET'])
def get_flights():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    origin = request.args.get('from')
    dest = request.args.get('to')
    date = request.args.get('date')
    query = "SELECT * FROM Flight WHERE 1=1"
    params = []
    if origin:
        query += " AND DepartureAirport=%s"
        params.append(origin)
    if dest:
        query += " AND ArrivalAirport=%s"
        params.append(dest)
    if date:
        query += " AND DATE(DepartureTime)=%s"
        params.append(date)
    cursor.execute(query, params)
    flights = cursor.fetchall()
    cursor.close()
    return jsonify(flights)

@app.route('/flights/<int:flightID>', methods=['GET'])
def get_flight(flightID):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Flight WHERE FlightID=%s", (flightID,))
    flight = cursor.fetchone()
    cursor.close()
    if flight:
        return jsonify(flight)
    return jsonify({"error": "Flight not found"}), 404

@app.route('/flights/<int:flightID>', methods=['PUT'])
def update_flight(flightID):
    data = request.json
    required = ['FlightNumber', 'DepartureTime', 'ArrivalTime', 'DepartureAirport', 'ArrivalAirport', 'AirlineID']
    valid, error = validate_fields(data, required)
    if not valid:
        return jsonify({"error": error}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Flight SET FlightNumber=%s, DepartureTime=%s, ArrivalTime=%s,
        DepartureAirport=%s, ArrivalAirport=%s, AirlineID=%s, ActualDepartureTime=%s,
        ActualArrivalTime=%s WHERE FlightID=%s
    """, (data['FlightNumber'], data['DepartureTime'], data['ArrivalTime'], data['DepartureAirport'], data['ArrivalAirport'], data['AirlineID'], data.get('ActualDepartureTime'), data.get('ActualArrivalTime'), flightID))
    if cursor.rowcount == 0:
        cursor.close()
        return jsonify({"error": "Flight not found"}), 404
    conn.commit()
    cursor.close()
    return jsonify({"message": "Flight updated"})

@app.route('/flights/<int:flightID>', methods=['DELETE'])
def delete_flight(flightID):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Flight WHERE FlightID=%s", (flightID,))
    if cursor.rowcount == 0:
        cursor.close()
        return jsonify({"error": "Flight not found"}), 404
    conn.commit()
    cursor.close()
    return jsonify({"message": "Flight deleted"})

# ---------------------------
# BOOKING ROUTES
# ---------------------------
@app.route('/bookings', methods=['POST'])
def create_booking():
    data = request.json
    required = ['FlightID', 'PassengerID', 'SeatNumber']
    valid, error = validate_fields(data, required)
    if not valid:
        return jsonify({"error": error}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Booking (FlightID, PassengerID, BookingDate, SeatNumber, CheckInStatus)
        VALUES (%s,%s,NOW(),%s,%s)
    """, (data['FlightID'], data['PassengerID'], data['SeatNumber'], data.get('CheckInStatus','Not Checked In')))
    conn.commit()
    booking_id = cursor.lastrowid
    cursor.close()
    return jsonify({"BookingID": booking_id}), 201

@app.route('/bookings/<int:bookingID>', methods=['GET'])
def get_booking(bookingID):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Booking WHERE BookingID=%s", (bookingID,))
    booking = cursor.fetchone()
    cursor.close()
    if booking:
        return jsonify(booking)
    return jsonify({"error": "Booking not found"}), 404

@app.route('/bookings/passenger/<int:passengerID>', methods=['GET'])
def get_bookings_by_passenger(passengerID):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Booking WHERE PassengerID=%s", (passengerID,))
    bookings = cursor.fetchall()
    cursor.close()
    return jsonify(bookings)

@app.route('/bookings/<int:bookingID>', methods=['PATCH'])
def update_booking(bookingID):
    data = request.json
    if not data.get('SeatNumber') and not data.get('CheckInStatus'):
        return jsonify({"error": "Provide SeatNumber or CheckInStatus"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Booking SET SeatNumber=COALESCE(%s,SeatNumber), CheckInStatus=COALESCE(%s,CheckInStatus)
        WHERE BookingID=%s
    """, (data.get('SeatNumber'), data.get('CheckInStatus'), bookingID))
    if cursor.rowcount == 0:
        cursor.close()
        return jsonify({"error": "Booking not found"}), 404
    conn.commit()
    cursor.close()
    return jsonify({"message": "Booking updated"})

@app.route('/bookings/<int:bookingID>', methods=['DELETE'])
def delete_booking(bookingID):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Booking WHERE BookingID=%s", (bookingID,))
    if cursor.rowcount == 0:
        cursor.close()
        return jsonify({"error": "Booking not found"}), 404
    conn.commit()
    cursor.close()
    return jsonify({"message": "Booking deleted"})

# Aggregate Functionality!



# ---------------------------
# RUN APP
# ---------------------------
if __name__ == '__main__':
    app.run(debug=True, port=5001)