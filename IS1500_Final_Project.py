from flask import Flask,request, jsonify
import mysql.connector

app = Flask(__name__)

con = mysql.connector.connect(
    host = 'localhost',
    user='root',
    password='root',
    database='airline_management'
)

@app.route('/getTable', methods=['GET'])
def get_tables():
    cursor=con.cursor()
    cursor.execute("SHOW TABLES;")
    tables = cursor.fetchall()
    cursor.close()
    #con.close()
    table_names=[table[0] for table in tables]
    return jsonify({"tables":table_names}),200

@app.route('/addBooking', methods=['POST'])
def add_booking():
    data = request.get_json()
    flight_id = data.get("FlightID")
    passenger_id = data.get("PassengerD")
    seat_number = data.get("SeatNumber")
    if not flight_id or not passenger_id:
        return jsonify({"error":"You must input a flight and passenger ID"}), 400
    try:
        cursor = con.cursor
        booking_number = str(uuid.uuid4())[:8].upper()
        query = """
            INSERT INTO Booking (
                FlightID, PassengerID, BookingNumber, BookingDate, SeatNumber, CheckInStatus
            )
            VALUES (%s, %s, %s, NOW(), %s, %s)
        """
        values = (
            flight_id,
            passenger_id,
            booking_number,
            seat_number,
            "Not Checked In"
        )
        cursor.execute(query, values)
        con.commit()

        return jsonify({
            "message": "Booking created successfully",
            "BookingID": cursor.lastrowid,
            "BookingNumber": booking_number
        }), 201

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500

    finally:
        cursor.close()
@app.route('bookings/<int:booking_id>', methods=['GET'])
def get_tables():
    try:
        cursor = con.cursor()
        query = """
                SELECT 
                b.BookingID,
                b.BookingNumber,
                b.BookingDate,
                b.SeatNumber,
                b.CheckInStatus,

                f.FlightID,
                f.FlightNumber,
                f.DepartureTime,
                f.ArrivalTime,

                p.PassengerID,
                p.Name AS PassengerName,
                p.Email AS PassengerEmail
            FROM Booking b
            JOIN Flight f ON b.FlightID = f.FlightID
            JOIN Passenger p ON b.PassengerID = p.PassengerID
            WHERE b.BookingID = %s
        """
        cursor.execute(query, (booking_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({"error": "Booking not found"}), 404

        return jsonify(result), 200

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500

    finally:
        cursor.close()

@app.route('/bookings/passenger/<int:passenger_id>', methods=['GET'])
def get_bookings_by_passenger(passenger_id):
    try:
        cursor = con.cursor(dictionary=True)

        query = """
            SELECT 
                b.BookingID,
                b.BookingNumber,
                b.BookingDate,
                b.SeatNumber,
                b.CheckInStatus,

                f.FlightID,
                f.FlightNumber,
                f.DepartureAirport,
                f.ArrivalAirport,
                f.DepartureTime,
                f.ArrivalTime
            FROM Booking b
            JOIN Flight f ON b.FlightID = f.FlightID
            WHERE b.PassengerID = %s
            ORDER BY b.BookingDate DESC
        """

        cursor.execute(query, (passenger_id,))
        bookings = cursor.fetchall()

        if not bookings:
            return jsonify({"message": "No bookings found for this passenger"}), 404

        return jsonify(bookings), 200

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500

    finally:
        cursor.close()



if __name__=="__main__":
    print("connecting to DB...")
    app.run(debug=True)