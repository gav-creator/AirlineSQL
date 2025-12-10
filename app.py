from flask import Flask, render_template, jsonify, request, flash, redirect, url_for

app = Flask(__name__,template_folder="Front_end/templates")
app.secret_key = "secret_123"

from dbConnect import get_db_connection

db = get_db_connection()
cursor = db.cursor(dictionary=True)

@app.route('/')
def home():
    return render_template('login.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    # POST request handling
    user_id = request.form["id"]
    name = request.form["name"]

    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM Employee 
        WHERE EmployeeID = %s AND Name = %s
    """, (user_id, name))

    employee = cursor.fetchone()

    # If no employee found assume they are a customer
    if not employee:
        return render_template("search_flights.html")

    # Employee found: check designation
    if employee["Designation"].upper() == "ADMIN" or employee["Designation"].upper() == "CEO":
        return redirect("/admin")

    # Otherwise they are regular employee
    return render_template("employee.html")

#Employee button selected
@app.route('/employee')
def employee():
    return render_template('employee.html')

@app.route("/admin")
def admin_dashboard():
    cursor = db.cursor(dictionary=True)

    # 1. Airline with most flights
    cursor.execute("""
        SELECT a.Name AS AirlineName, COUNT(f.FlightID) AS TotalFlights
        FROM Airline a
        LEFT JOIN Flight f ON a.AirlineID = f.AirlineID
        GROUP BY a.AirlineID
        ORDER BY TotalFlights DESC
        LIMIT 1;
    """)
    airlineMostFlights = cursor.fetchone()

    # 2. Passengers per flight
    cursor.execute("""
        SELECT f.FlightNumber, COUNT(b.PassengerID) AS PassengerCount
        FROM Flight f
        LEFT JOIN Booking b ON f.FlightID = b.FlightID
        GROUP BY f.FlightID;
    """)
    passengersPerFlight = cursor.fetchall()

    # 3. Luggage weight per flight
    cursor.execute("""
        SELECT f.FlightNumber, SUM(l.Weight) AS TotalLuggageWeight
        FROM Flight f
        LEFT JOIN Booking b ON f.FlightID = b.FlightID
        LEFT JOIN Luggage l ON b.BookingID = l.BookingID
        GROUP BY f.FlightID;
    """)
    luggageWeight = cursor.fetchall()

    # 4. Revenue per flight
    cursor.execute("""
        SELECT f.FlightNumber, SUM(p.Amount) AS Revenue
        FROM Flight f
        LEFT JOIN Booking b ON f.FlightID = b.FlightID
        LEFT JOIN Payment p ON b.BookingID = p.BookingID
        GROUP BY f.FlightID;
    """)
    revenuePerFlight = cursor.fetchall()

    return render_template(
        'admin.html',  # this is your combined HTML template
        airlineMostFlights=airlineMostFlights,
        passengersPerFlight=passengersPerFlight,
        luggageWeight=luggageWeight,
        revenuePerFlight=revenuePerFlight
    )



#Customer button selected
@app.route("/search_flights", methods=["GET", "POST"])
def search_flights():
    if request.method == "POST":
        origin = request.form["DepartureAirport"]
        destination = request.form["ArrivalAirport"]

        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT f.FlightID, f.FlightNumber, f.DepartureTime, f.ArrivalTime,
                   da.City AS DepartureCity, aa.City AS ArrivalCity,
                   f.AirlineID,
                   (SELECT COUNT(*) FROM Booking b WHERE b.FlightID = f.FlightID) AS booked_seats
            FROM Flight f
            JOIN Airport da ON f.DepartureAirport = da.AirportID
            JOIN Airport aa ON f.ArrivalAirport = aa.AirportID
            WHERE da.City = %s AND aa.City = %s
        """, (origin, destination))

        flights = cursor.fetchall()

        # Calculate remaining seats
        for flight in flights:
            flight['remaining_seats'] = 50 - flight['booked_seats']

        return render_template("flight_search_results.html", flights=flights)

    return render_template("search_flights.html")


@app.route("/book_flight", methods=["GET", "POST"])
def book_flight():
    flight_id = request.form.get("flight_id") or request.args.get("flight_id")

    cursor = db.cursor(dictionary=True)

    # STEP 1 — GET: show form
    if request.method == "GET":
        flight_number = request.args.get("FlightNumber")

        cursor = db.cursor(dictionary=True)
        cursor.execute("""
    SELECT 
        f.FlightID,
        f.FlightNumber,
        f.DepartureTime,
        f.ArrivalTime,
        da.Name AS DepartureAirportName,
        da.City AS DepartureCity,
        aa.Name AS ArrivalAirportName,
        aa.City AS ArrivalCity
    FROM Flight f
    JOIN Airport da ON f.DepartureAirport = da.AirportID
    JOIN Airport aa ON f.ArrivalAirport = aa.AirportID
    WHERE f.FlightNumber = %s
""", (flight_number,))
        flight = cursor.fetchone()

        if not flight:
            flash("Invalid flight selected.", "error")
            return render_template("search_flights.html")

        return render_template("book_flight.html", flight=flight)

    # STEP 2 — POST: read form
    passport = request.form.get("passport")
    name = request.form.get("name")
    dob = request.form.get("dob")
    phone = request.form.get("phone")
    credit_card = request.form.get("credit_card")
    amount = request.form.get("amount")

    # SAFETY CHECK — catch missing fields
    if not passport or not name or not dob or not phone:
        flash("Missing passenger information.", "error")
        return render_template("book_flight.html", flight={"FlightID": flight_id})

    # Insert passenger
    cursor.execute("""
        INSERT INTO Passenger (PassportNumber, Name, DateofBirth, Phone)
        VALUES (%s, %s, %s, %s)
    """, (passport, name, dob, phone))
    passenger_id = cursor.lastrowid

    # Next seat
    cursor.execute("""
        SELECT COALESCE(MAX(SeatNumber), 0) + 1 AS NextSeat
        FROM Booking
        WHERE FlightID = %s
    """, (flight_id,))
    next_seat = cursor.fetchone()["NextSeat"]

    # Insert booking
    cursor.execute("""
        INSERT INTO Booking (PassengerID, FlightID, SeatNumber, BookingDate, BookingNumber, CheckInStatus)
        VALUES (%s, %s, %s, NOW(), '', 'Not Checked In')
    """, (passenger_id, flight_id, next_seat))

    booking_id = cursor.lastrowid

    # Update booking number (to be same as booking ID for simplicity)
    cursor.execute("""
        UPDATE Booking
        SET BookingNumber = %s
        WHERE BookingID = %s
    """, (str(booking_id), booking_id))

    # Insert payment
    cursor.execute("""
        INSERT INTO Payment (BookingID, PaymentMethod, Amount, TransactionDateTime, Currency)
        VALUES (%s, 'Credit Card', %s, NOW(), 'USD')
    """, (booking_id, amount))

    db.commit()

    return redirect(url_for("transaction_complete",
                        passenger_id=passenger_id,
                        flight_id=flight_id,
                        booking_id=booking_id))


@app.route("/transaction_complete")
def transaction_complete():
    passenger_id = request.args.get("passenger_id")
    flight_id = request.args.get("flight_id")
    booking_id = request.args.get("booking_id")

    cursor = db.cursor(dictionary=True)

    # Fetch passenger
    cursor.execute("SELECT * FROM Passenger WHERE PassengerID = %s", (passenger_id,))
    passenger = cursor.fetchone()

    # Fetch flight with joined airport data
    cursor.execute("""
        SELECT 
            f.FlightID,
            f.FlightNumber,
            f.DepartureTime,
            f.ArrivalTime,
            da.Name AS DepartureAirportName,
            da.City AS DepartureCity,
            aa.Name AS ArrivalAirportName,
            aa.City AS ArrivalCity
        FROM Flight f
        JOIN Airport da ON f.DepartureAirport = da.AirportID
        JOIN Airport aa ON f.ArrivalAirport = aa.AirportID
        WHERE f.FlightID = %s
    """, (flight_id,))
    flight = cursor.fetchone()

    # Fetch booking
    cursor.execute("SELECT * FROM Booking WHERE BookingID = %s", (booking_id,))
    booking = cursor.fetchone()

    return render_template("transaction_complete.html",
                           passenger=passenger,
                           flight=flight,
                           booking=booking)



#Add query definitions here
@app.route("/add_flight", methods=["GET", "POST"])
def add_flight():
    message = None

    cursor = db.cursor(dictionary=True)

    # Load dropdown data
    cursor.execute("SELECT AirportID, City FROM Airport ORDER BY City")
    airports = cursor.fetchall()

    cursor.execute("SELECT AirlineID, Name FROM Airline ORDER BY Name")
    airlines = cursor.fetchall()

    if request.method == "POST":
        flight_number = request.form.get("flight_number")
        departure_time = request.form.get("departure_time")
        arrival_time = request.form.get("arrival_time")
        departure_airport = request.form.get("departure_airport")
        arrival_airport = request.form.get("arrival_airport")
        airline_id = request.form.get("airline_id")

        # ---------------- VALIDATION ----------------
        if not all([flight_number, departure_time, arrival_time, departure_airport, arrival_airport, airline_id]):
            message = "Error: All fields are required."
        elif departure_airport == arrival_airport:
            message = "Error: Departure and arrival airport cannot be the same."
        else:
            try:
                cursor2 = db.cursor()
                cursor2.execute("""
                    INSERT INTO Flight (
                        FlightNumber, DepartureTime, ArrivalTime,
                        DepartureAirport, ArrivalAirport, AirlineID
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (flight_number, departure_time, arrival_time, departure_airport, arrival_airport, airline_id))
                db.commit()
                message = "Flight added successfully!"
            except Exception as e:
                message = f"Database error: {e}"

    # Render template with dropdown data + message
    return render_template("add_flight.html",
                           airports=airports,
                           airlines=airlines,
                           message=message)

@app.route("/add_airline", methods=["GET", "POST"])
def add_airline():
    if request.method == "POST":
        action = request.form.get("action")
        airline_id = request.form.get("airline_id")
        name = request.form.get("name")
        phone = request.form.get("phone")

        cursor = db.cursor()

        # -----------------------------
        # ADD
        # -----------------------------
        if action == "add":
            if not name or not phone:
                return render_template("add_airline.html", message="Error: Name and Phone cannot be empty for adding.")

            try:
                cursor.execute("""
                    INSERT INTO Airline (Name, Phone)
                    VALUES (%s, %s)
                """, (name, phone))
                db.commit()
                return render_template("add_airline.html", message="Airline added successfully!")
            except Exception as e:
                return render_template("add_airline.html", message=f"Database Error: {e}")

        # -----------------------------
        # UPDATE
        # -----------------------------
        if action == "update":
            if not airline_id:
                return render_template("add_airline.html", message="Error: AirlineID required for update.")

            if not name or not phone:
                return render_template("add_airline.html", message="Error: Name and Phone cannot be empty for updating.")

            try:
                cursor.execute("""
                    UPDATE Airline
                    SET Name=%s, Phone=%s
                    WHERE AirlineID=%s
                """, (name, phone, airline_id))
                db.commit()

                if cursor.rowcount == 0:
                    return render_template("add_airline.html", message="Error: AirlineID not found.")

                return render_template("add_airline.html", message="Airline updated successfully!")
            except Exception as e:
                return render_template("add_airline.html", message=f"Database Error: {e}")

        # -----------------------------
        # DELETE
        # -----------------------------
        if action == "delete":
            if not airline_id:
                return render_template("add_airline.html", message="Error: AirlineID required for delete.")

            try:
                cursor.execute("DELETE FROM Airline WHERE AirlineID = %s", (airline_id,))
                db.commit()

                if cursor.rowcount == 0:
                    return render_template("add_airline.html", message="Error: AirlineID not found.")

                return render_template("add_airline.html", message="Airline deleted successfully!")
            except Exception as e:
                return render_template("add_airline.html", message=f"Database Error: {e}")
    
    # -----------------------------
    # Fetch all airlines for display
    # -----------------------------
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Airline ORDER BY AirlineID")
    airlines = cursor.fetchall()

    # Render template with message + airlines
    return render_template("add_airline.html", airlines=airlines)

@app.route("/update_crew", methods=["GET", "POST"])
def update_crew():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    message = None

    # Load all flights for dropdown
    cursor.execute("SELECT FlightID, FlightNumber FROM Flight ORDER BY FlightNumber")
    flights = cursor.fetchall()

    selected_flight_id = None
    crew_list = []

    if request.method == "POST":
        action = request.form.get("action")
        selected_flight_id = request.form.get("flight_id")

        # Load crew list if a flight is selected
        if selected_flight_id:
            cursor.execute("""
                SELECT fc.EmployeeID, e.Name, fc.Role
                FROM FlightCrew fc
                JOIN Employee e ON fc.EmployeeID = e.EmployeeID
                WHERE fc.FlightID=%s
            """, (selected_flight_id,))
            crew_list = cursor.fetchall()

        # ---------------- ADD CREW MEMBER ----------------
        if action == "add":
            new_emp_id = request.form.get("new_employee_id")
            new_role = request.form.get("new_role")

            if not new_emp_id or not new_role:
                message = "Error: Employee ID and Role required to add."
            elif not new_emp_id.isdigit():
                message = "Error: Employee ID must be a number."
            else:
                # Check if the employee exists
                cursor.execute("SELECT * FROM Employee WHERE EmployeeID=%s", (new_emp_id,))
                employee = cursor.fetchone()
                if not employee:
                    message = f"Error: Employee ID {new_emp_id} does not exist."
                else:
                    # Check if already assigned to this flight
                    cursor.execute("""
                        SELECT * FROM FlightCrew WHERE FlightID=%s AND EmployeeID=%s
                    """, (selected_flight_id, new_emp_id))
                    already_assigned = cursor.fetchone()
                    if already_assigned:
                        message = f"Error: Employee {employee['Name']} is already assigned to this flight."
                    else:
                        cursor.execute("""
                            INSERT INTO FlightCrew (FlightID, EmployeeID, Role)
                            VALUES (%s, %s, %s)
                        """, (selected_flight_id, new_emp_id, new_role))
                        db.commit()
                        message = f"Crew member {employee['Name']} added to flight."
            
            # Refresh crew list
            cursor.execute("""
                SELECT fc.EmployeeID, e.Name, fc.Role
                FROM FlightCrew fc
                JOIN Employee e ON fc.EmployeeID = e.EmployeeID
                WHERE fc.FlightID=%s
            """, (selected_flight_id,))
            crew_list = cursor.fetchall()

        # ---------------- REMOVE CREW MEMBER ----------------
        elif action == "remove":
            emp_id_to_remove = request.form.get("remove_employee_id")
            if not emp_id_to_remove:
                message = "Error: Employee ID required to remove."
            elif not emp_id_to_remove.isdigit():
                message = "Error: Employee ID must be a number."
            else:
                # Check if the employee is on this flight
                cursor.execute("""
                    SELECT * FROM FlightCrew WHERE FlightID=%s AND EmployeeID=%s
                """, (selected_flight_id, emp_id_to_remove))
                crew_member = cursor.fetchone()

                if not crew_member:
                    message = "Error: This crew member is not assigned to this flight."
                else:
                    cursor.execute("""
                        DELETE FROM FlightCrew WHERE FlightID=%s AND EmployeeID=%s
                    """, (selected_flight_id, emp_id_to_remove))
                    db.commit()
                    message = "Crew member removed from flight."

                    # Refresh crew list
                    cursor.execute("""
                        SELECT fc.EmployeeID, e.Name, fc.Role
                        FROM FlightCrew fc
                        JOIN Employee e ON fc.EmployeeID = e.EmployeeID
                        WHERE fc.FlightID=%s
                    """, (selected_flight_id,))
                    crew_list = cursor.fetchall()

    return render_template(
        "update_crew.html",
        flights=flights,
        crew_list=crew_list,
        selected_flight_id=selected_flight_id,
        message=message
    )

@app.route("/add_employee", methods=["GET", "POST"])
def add_employee():
    cursor = db.cursor(dictionary=True)
    message = None

    # Handle POST actions
    if request.method == "POST":
        action = request.form.get("action")

        # ADD employee
        if action == "add":
            name = request.form.get("name")
            dob = request.form.get("dob")
            phone = request.form.get("phone")
            designation = request.form.get("designation")

            if not name or not dob or not phone or not designation:
                message = "Error: All fields are required."
            else:
                cursor.execute("""
                    INSERT INTO Employee (Name, DateofBirth, Phone, Designation)
                    VALUES (%s, %s, %s, %s)
                """, (name, dob, phone, designation))
                db.commit()
                message = "Employee added successfully!"

        # UPDATE employee
        elif action == "update":
            emp_id = request.form.get("employee_id")
            name = request.form.get("name")
            dob = request.form.get("dob")
            phone = request.form.get("phone")
            designation = request.form.get("designation")

            cursor.execute("SELECT * FROM Employee WHERE EmployeeID = %s", (emp_id,))
            existing = cursor.fetchone()

            if not existing:
                message = "Employee ID not found."
            else:
                cursor.execute("""
                    UPDATE Employee
                    SET Name=%s, DateofBirth=%s, Phone=%s, Designation=%s
                    WHERE EmployeeID=%s
                """, (name, dob, phone, designation, emp_id))
                db.commit()
                message = "Employee updated successfully!"

        # DELETE employee
        # DELETE employee
        elif action == "delete":
            emp_id = request.form.get("employee_id")

            # Fetch the employee
            cursor.execute("SELECT * FROM Employee WHERE EmployeeID = %s", (emp_id,))
            existing = cursor.fetchone()

            if not existing:
                message = "Employee ID not found."
            elif existing["Designation"].upper() == "ADMIN":
                message = "Error: ADMIN employees cannot be removed."
            else:
                cursor.execute("DELETE FROM Employee WHERE EmployeeID = %s", (emp_id,))
                db.commit()
                message = "Employee deleted successfully!"


    # Load employee list for display
    cursor.execute("SELECT * FROM Employee ORDER BY EmployeeID")
    employees = cursor.fetchall()

    return render_template("add_employee.html",
                           message=message,
                           employees=employees)


@app.route('/add_passenger', methods=['GET', 'POST'])
def add_passenger():
    data = request.get_json()

    pass

# Aggregate Dashboard Analytics Implementation


if __name__ == '__main__':
    app.run(debug=True)