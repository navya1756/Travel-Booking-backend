from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_session import Session
from flask_bcrypt import Bcrypt
from mysql.connector import connection
from datetime import datetime, timedelta
import razorpay
import re
import os

from otp import genotp
from cmail import send_mail
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
client = razorpay.Client(auth=("rzp_test_TV8fsr6CvPSfAT", "pF4KQtxPPLl433O1ly8pppUv"))
BASE_DIR=os.path.dirname(os.path.abspath(__file__)) #finding base directory path D:\pfs33\ecom33
UPLOAD_FOLDER=os.path.join(BASE_DIR,'static','uploads') #static path defining D:\pfs33\ecom33\static\uploads
os.makedirs(UPLOAD_FOLDER,exist_ok=True) #creating floders
ALLOWED_EXTENSION={'jpg','jpeg','png','gif','webp'}
MAX_LENGTH_CONTENT=6*1024*1024
def get_db_connection():
    return connection.MySQLConnection (user='root',host='localhost',password='navya123',database='travelgo',port=3306)
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SECRET_KEY"] = "TravelGo345"

CORS(
    app,
    origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    supports_credentials=True
)

app.config["SESSION_COOKIE_NAME"] = "travelgo_session"
app.config["SESSION_TYPE"] = "filesystem"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=1)
app.config["SESSION_COOKIE_SECURE"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
Session(app)
bcrypt = Bcrypt(app)

@app.route('/')
def home():

    return jsonify({
        "status": "success",
        "message": "Welcome to TravelGo API"
    }), 200
@app.route('/api/packages', methods=['GET'])
def get_packages():
    mydb = None
    cursor = None
    try:
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        cursor.execute(""" SELECT package_id,name,location,price,duration,image,description FROM packages""")
        packages_data = cursor.fetchall()
        packages = []
        for package in packages_data:
            packages.append({
                "package_id": package[0],
                "name": package[1],
                "location": package[2],
                "price": float(package[3]),
                "duration": package[4],
                "image": package[5],
                "description": package[6]
            })
        return jsonify({"status": "success","packages": packages }), 200
    except Exception as e:
        print("GET PACKAGES ERROR:", e)
        return jsonify({"status": "failed","message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close()    
@app.route('/api/packages/<int:package_id>', methods=['GET'])
def get_package(package_id):
    print("PACKAGE ID RECEIVED:", package_id)
    mydb = None
    cursor = None
    try:
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        cursor.execute("""SELECT package_id,name,location,price,duration,image,description FROM packages WHERE package_id = %s""", [package_id])
        package = cursor.fetchone()
        if not package:
            return jsonify({"status": "failed","message": "Package not found"}), 404
        package_data = {
            "package_id": package[0],
            "name": package[1],
            "location": package[2],
            "price": float(package[3]),
            "duration": package[4],
            "image": package[5],
            "description": package[6]
        }
        return jsonify({
            "status": "success",
            "package": package_data
        }), 200
    except Exception as e:
        print("GET PACKAGE ERROR:", e)
        return jsonify({"status": "failed", "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close()

@app.route('/api/packages/search', methods=['GET'])
def search_packages():
    mydb = None
    cursor = None
    try:
        search = request.args.get('q', '').strip()
        if not search:
            return jsonify({"status": "failed","message": "Search query required"}), 400
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        search_pattern = f"%{search}%"
        cursor.execute("""SELECT package_id,name,location,price, duration,image,description FROM packages WHERE name LIKE %s OR location LIKE %s OR description LIKE %s""", [search_pattern,search_pattern,search_pattern])
        packages_data = cursor.fetchall()
        packages = []
        for package in packages_data:
            packages.append({
                "package_id": package[0],
                "name": package[1],
                "location": package[2],
                "price": float(package[3]),
                "duration": package[4],
                "image": package[5],
                "description": package[6]
            })
        return jsonify({
            "status": "success",
            "total_packages": len(packages),
            "packages": packages
        }), 200
    except Exception as e:
        print("SEARCH ERROR:", e)
        return jsonify({"status": "failed","message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close()

@app.route('/api/user/register', methods=['POST'])
def user_register():
    mydb = None
    cursor = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "failed","message": "No input data given"}), 400
        username = data.get("name", "").strip()
        useremail = data.get("email", "").strip()
        userphone = data.get("phone", "").strip()
        userpassword = data.get("password", "")
        if not username:
            return jsonify({"status": "failed","message": "Name is required"}), 400
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_pattern, useremail):
            return jsonify({"status": "failed","message": "Invalid email" }), 400
        if len(userpassword) < 6:
            return jsonify({
                "status": "failed",
                "message": "Password must contain at least 6 characters"
            }), 400
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        cursor.execute("""SELECT userid, verified FROM users WHERE email = %s""", [useremail])
        existing_user = cursor.fetchone()
        userotp = genotp()
        otp_expiry = datetime.now() + timedelta(minutes=5)
        hashed_password = bcrypt.generate_password_hash(
            userpassword
        ).decode("utf-8")    
        if existing_user:
            if existing_user[1] == 1:
                return jsonify({"status": "failed","message": "User already exists"}), 400
            cursor.execute(""" UPDATE users SET name = %s, phone = %s, password = %s, otp = %s, otp_expiry = %s, verified = 0 WHERE email = %s """, [username,userphone,hashed_password,userotp,otp_expiry,useremail])
        else:
            cursor.execute("""INSERT INTO users (userid,name,email,phone,password,otp,otp_expiry,verified) VALUES(UUID(),%s,%s,%s,%s,%s,%s,0)""",[username, useremail, userphone, hashed_password, userotp, otp_expiry])
        mydb.commit()
        subject = "TravelGo Registration OTP"
        body = f"""
Hello {username},
Your TravelGo registration OTP is:
{userotp}
This OTP is valid for 5 minutes.
Thank you,
TravelGo Team
"""
        send_mail(
            to=useremail,
            subject=subject,
            body=body
        )
        return jsonify({"status": "success","message": "OTP sent successfully", "email": useremail}), 200
    except Exception as e:
        mydb.rollback()
        print("REGISTER ERROR:", e)
        return jsonify({"status": "failed","message": str(e)}), 500

@app.route('/api/user/verify-otp', methods=['POST'])
def verify_otp():
    mydb = None
    cursor = None
    try:
        data = request.get_json(silent = True)
        if not data:
            return jsonify({"status": "failed","message": "No input data given"}), 400
        email = data.get("email", "").strip()
        userotp = data.get("otp", "").strip()
        if not email:
            return jsonify({
                "status": "failed",
                "message": "Email required"
            }), 400
        if not userotp:
            return jsonify({"status": "failed","message": "OTP required"}), 400
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        cursor.execute("""SELECT userid,otp,otp_expiry,verified FROM users WHERE email = %s""", [email])
        user = cursor.fetchone()
        if not user:
            return jsonify({
                "status": "failed",
                "message": "User not found"
            }), 404
        if user[3] == 1:
            return jsonify({"status": "failed","message": "User already verified"}), 400
        if not user[2]:
            return jsonify({"status": "failed","message": "OTP expired"}), 400
        if datetime.now() > user[2]:
            return jsonify({"status": "failed","message": "OTP expired"}), 400
        if userotp != user[1]:
            return jsonify({"status": "failed","message": "Invalid OTP"}), 400
        cursor.execute("""UPDATE users SET otp = NULL,otp_expiry = NULL,verified = 1 WHERE email = %s""", [email])
        mydb.commit()
        return jsonify({"status": "success","message": "OTP verified successfully"}), 200
    except Exception as e:
        mydb.rollback()
        print("OTP ERROR:", e)
        return jsonify({"status": "failed","message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close()
@app.route('/api/user/login', methods=['POST'])
def user_login():
    mydb = None
    cursor = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "failed","message": "No input data given"}), 400
        login_email = data.get("email", "").strip()
        login_password = data.get("password", "")
        if not login_email or not login_password:
            return jsonify({"status": "failed","message": "Email and password required"}), 400
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        cursor.execute(""" SELECT userid,name,email,phone,password,verified,role FROM users WHERE email = %s""", [login_email])
        user = cursor.fetchone()
        print("LOGIN USER TUPLE:", user)
        print("LOGIN USER LENGTH:", len(user) if user else 0)
        if not user:
            return jsonify({"status": "failed","message": "User not found"}), 404
        if user[5] != 1:
            return jsonify({"status": "failed","message": "Please verify your email first"}), 400
        if not bcrypt.check_password_hash(user[4],login_password):
            return jsonify({"status": "failed","message": "Invalid password"}), 400
        session.permanent = True
        session["userid"] = user[0]
        session["useremail"] = user[2]
        session["username"] = user[1]
        session["role"] = user[6]
        print("LOGIN SESSION:", dict(session))
        return jsonify({
            "status": "success",
            "message": "Login successful",
            "user": {
                "userid": user[0],
                "name": user[1],
                "email": user[2],
                "phone": user[3],
                "role": user[6]
            }
        }), 200
    except Exception as e:
        print("LOGIN ERROR:", e)
        return jsonify({"status": "failed","message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close()
@app.route('/api/user/check-login', methods=['GET'])
def check_login():
    print("CHECK LOGIN SESSION:", dict(session))
    print("REQUEST COOKIES:", request.cookies)

    if not session.get("userid"):
        return jsonify({"status": "failed","logged_in": False,"message": "User not logged in"}), 401
    return jsonify({
        "status": "success",
        "logged_in": True,
        "user": {
            "userid": session.get("userid"),
            "name": session.get("username"),
            "email": session.get("useremail"),
            "role": session.get("role")
        }
    }), 200

@app.route('/api/user/logout', methods=['POST'])
def user_logout():
    if not session.get("userid"):
        return jsonify({"status": "failed","message": "User not logged in"}), 401
    session.clear()
    return jsonify({"status": "success","message": "Logout successful"}), 200
def admin_required():
    if not session.get("userid"):
        return jsonify({
            "status": "failed","message": "Please login first"}), 401
    if session.get("role") != "admin":
        return jsonify({"status": "failed", "message": "Admin access required"}), 403

    return None
@app.route('/api/admin/users', methods=['GET'])
def admin_users():
    auth_error = admin_required()
    if auth_error:
        return auth_error
    mydb = None
    cursor = None
    try:
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        cursor.execute("""
            SELECT userid, name, email, phone, verified, role, created_at
            FROM users
            ORDER BY created_at DESC
        """)
        users_data = cursor.fetchall()
        users = []
        for user in users_data:
            users.append({
                "userid": user[0],
                "name": user[1],
                "email": user[2],
                "phone": user[3],
                "verified": user[4],
                "role": user[5],
                "created_at": str(user[6])
            })
        return jsonify({"status": "success","users": users}), 200
    except Exception as e:
        print("ADMIN USERS ERROR:", e)
        return jsonify({"status": "failed","message": str(e)}), 500
    finally:

        if cursor:
            cursor.close()
        if mydb:
            mydb.close()
@app.route('/api/admin/bookings', methods=['GET'])
def admin_bookings():
    auth_error = admin_required()
    if auth_error:
        return auth_error
    mydb = None
    cursor = None
    try:
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        cursor.execute("""SELECT booking_id,userid,name,email,phone,destination,travel_date,persons,message,amount,payment_status,status,razorpay_order_id,razorpay_payment_id, created_at FROM bookings ORDER BY booking_id DESC""")
        booking_data = cursor.fetchall()
        bookings = []
        for booking in booking_data:
            bookings.append({
                "booking_id": booking[0],
                "userid": booking[1],
                "name": booking[2],
                "email": booking[3],
                "phone": booking[4],
                "destination": booking[5],
                "travel_date": str(booking[6]),
                "persons": booking[7],
                "message": booking[8],
                "amount": float(booking[9] or 0),
                "payment_status": booking[10],
                "status": booking[11],
                "razorpay_order_id": booking[12],
                "razorpay_payment_id": booking[13],
                "created_at": str(booking[14])
            })

        return jsonify({"status": "success","bookings": bookings}), 200
    except Exception as e:
        print("ADMIN BOOKINGS ERROR:", e)
        return jsonify({"status": "failed","message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close()
@app.route('/api/admin/bookings/<int:booking_id>', methods=['PUT'])
def admin_update_booking(booking_id):
    auth_error = admin_required()
    if auth_error:
        return auth_error
    mydb = None
    cursor = None
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"status": "failed","message": "No data given"}), 400
        status = data.get("status", "").strip()
        allowed_statuses = [
            "Pending",
            "Confirmed",
            "Cancelled"
        ]
        if status not in allowed_statuses:
            return jsonify({"status": "failed","message": "Invalid booking status"}), 400
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        cursor.execute("""UPDATE bookings SET status = %s WHERE booking_id = %s""", [status, booking_id])
        mydb.commit()
        if cursor.rowcount == 0:
            return jsonify({"status": "failed","message": "Booking not found"}), 404
        return jsonify({"status": "success", "message": "Booking status updated successfully"}), 200
    except Exception as e:
        mydb.rollback()
        print("ADMIN UPDATE BOOKING ERROR:", e)
        return jsonify({ "status": "failed","message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close()
@app.route('/api/admin/bookings/<int:booking_id>', methods=['DELETE'])
def admin_delete_booking(booking_id):
    auth_error = admin_required()
    if auth_error:
        return auth_error
    mydb = None
    cursor = None
    try:
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        cursor.execute(""" SELECT booking_id FROM bookings WHERE booking_id = %s""", [booking_id])
        booking = cursor.fetchone()
        if not booking:
            return jsonify({"status": "failed","message": "Booking not found"}), 404
        cursor.execute(""" DELETE FROM bookings WHERE booking_id = %s """, [booking_id])
        mydb.commit()
        return jsonify({ "status": "success", "message": "Booking deleted successfully"}), 200
    except Exception as e:
        if mydb:
            mydb.rollback()
        print("ADMIN DELETE BOOKING ERROR:", e)
        return jsonify({
            "status": "failed",
            "message": str(e)
        }), 500
    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close()
@app.route('/api/admin/contact-messages', methods=['GET'])
def admin_contact_messages():
    auth_error = admin_required()
    if auth_error:
        return auth_error
    mydb = None
    cursor = None
    try:
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)

        cursor.execute("""
            SELECT id, name, email, phone, message, created_at
            FROM contact_messages
            ORDER BY id DESC
        """)

        messages_data = cursor.fetchall()
        messages = []
        for msg in messages_data:
            messages.append({
                "id": msg[0],
                "name": msg[1],
                "email": msg[2],
                "phone": msg[3],
                "message": msg[4],
                "created_at": str(msg[5])
            })

        return jsonify({
            "status": "success",
            "messages": messages
        }), 200

    except Exception as e:

        print("ADMIN CONTACT ERROR:", e)

        return jsonify({
            "status": "failed",
            "message": str(e)
        }), 500

    finally:

        if cursor:
            cursor.close()
        if mydb:
            mydb.close()
@app.route('/api/admin/packages', methods=['POST'])
def admin_add_package():
    auth_error = admin_required()
    if auth_error:
        return auth_error
    mydb = None
    cursor = None
    try:
        name = request.form.get("name", "").strip()
        location = request.form.get("location", "").strip()
        price = request.form.get("price", "").strip()
        duration = request.form.get("duration", "").strip()
        description = request.form.get("description", "").strip()
        image = request.files.get("image")
        if not name or not location or not price or not duration or not description:
            return jsonify({"status": "failed", "message": "All fields are required"}), 400
        if not image:
            return jsonify({"status": "failed","message": "Destination image is required"}), 400
        if image.filename == "":
            return jsonify({"status": "failed","message": "Please select an image"}), 400
        allowed_extensions = {
            "jpg",
            "jpeg",
            "png",
            "gif",
            "webp"
        }
        extension = image.filename.rsplit(".", 1)[-1].lower()
        if extension not in allowed_extensions:
            return jsonify({"status": "failed","message": "Invalid image format"}), 400
        try:
            price_value = float(price)
        except ValueError:
            return jsonify({"status": "failed","message": "Price must be a number"}), 400
        import uuid
        filename = str(uuid.uuid4()) + "." + extension
        upload_folder = app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)
        image.save(os.path.join(upload_folder, filename))
        image_path = "uploads/" + filename
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        cursor.execute("""INSERT INTO packages(name, location, price, duration, image, description) VALUES (%s, %s, %s, %s, %s, %s)""", [name,location,price_value,duration,image_path, description])
        mydb.commit()
        return jsonify({ "status": "success", "message": "Destination added successfully"}), 201
    except Exception as e:
        if mydb:
            mydb.rollback()
        print("ADMIN ADD PACKAGE ERROR:", e)
        return jsonify({"status": "failed", "message": str(e)}), 500
    finally:

        if cursor:
            cursor.close()
        if mydb:
            mydb.close()
@app.route('/api/admin/packages', methods=['GET'])
def admin_get_packages():
    auth_error = admin_required()
    if auth_error:
        return auth_error
    mydb = None
    cursor = None
    try:
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        cursor.execute("""SELECT package_id,name, location, price,duration,image,description FROM packages ORDER BY package_id DESC """)
        package_data = cursor.fetchall()
        packages = []
        for package in package_data:
            packages.append({
                "package_id": package[0],
                "name": package[1],
                "location": package[2],
                "price": float(package[3] or 0),
                "duration": package[4],
                "image": package[5],
                "description": package[6]
            })

        return jsonify({
            "status": "success",
            "packages": packages
        }), 200
    except Exception as e:
        print("ADMIN GET PACKAGES ERROR:", e)
        return jsonify({"status": "failed","message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close()
@app.route('/api/bookings', methods=['POST'])
def create_booking():
    mydb = None
    cursor = None
    try:
        if not session.get("userid"):
            return jsonify({"status": "failed","message": "Please login first"}), 401
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"status": "failed","message": "No booking data given"}), 400
        name = data.get("name", "").strip()
        email = data.get("email", "").strip()
        phone = data.get("phone", "").strip()
        destination = data.get("destination", "").strip()
        travel_date = data.get("travel_date", "").strip()
        persons = data.get("persons")
        message = data.get("message", "").strip()
        package_id = data.get("package_id")
        if package_id == "":
            package_id = None
        if not name:
            return jsonify({"status": "failed","message": "Name required"}), 400
        if not email:
            return jsonify({"status": "failed","message": "Email required"}), 400
        if not phone:
            return jsonify({"status": "failed","message": "Phone required"}), 400
        if not destination:
            return jsonify({"status": "failed","message": "Destination required"}), 400
        if not travel_date:
            return jsonify({ "status": "failed","message": "Travel date required"}), 400
        if not persons:
            return jsonify({"status": "failed","message": "Number of persons required"}), 400
        try:
            persons = int(persons)
        except (ValueError, TypeError):
            return jsonify({"status": "failed","message": "Persons must be a number"}), 400
        if persons <= 0:
            return jsonify({"status": "failed","message": "Persons must be greater than zero"}), 400
        try:
            datetime.strptime(travel_date,"%Y-%m-%d")
        except ValueError:
            return jsonify({"status": "failed","message": "Travel date must be YYYY-MM-DD"}), 400
           
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        if package_id is not None:
            try:
                package_id = int(package_id)
            except (ValueError, TypeError):
                return jsonify({"status": "failed","message": "Invalid package ID"}), 400
            cursor.execute("""SELECT package_id,name,price FROM packages WHERE package_id = %s""",(package_id,))
            package = cursor.fetchone()
        else:
            cursor.execute("""SELECT package_id,name,price FROM packages WHERE name = %s LIMIT 1""",(destination,))
            package = cursor.fetchone()
        if not package:
            return jsonify({
                "status": "failed",
                "message": "Package not found for this destination"
            }), 404
        package_id_db = package[0] 
        package_name = package[1]
        package_price = float(package[2])
        total_amount = package_price * persons
        cursor.execute("""INSERT INTO bookings(userid,name,email,phone,destination,travel_date,persons,message,amount,payment_status,status)VALUES(%s, %s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(session.get("userid"),name,email,phone,destination,travel_date,persons,message,total_amount,"Pending","Pending"))
        mydb.commit()
        booking_id = cursor.lastrowid
        amount_in_paise = int(
            total_amount * 100
        )
        razorpay_order = client.order.create({
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": f"booking_{booking_id}"
        })
        razorpay_order_id = razorpay_order["id"]
        cursor.execute("""UPDATE bookings SET razorpay_order_id = %s WHERE booking_id = %s """,(razorpay_order_id,booking_id))
        mydb.commit()
        return jsonify({
            "status": "success",
            "message":
                "Booking created and Razorpay order created",
            "booking_id":
                booking_id,
            "package_id":
                package_id_db,
            "package_name":
                package_name,
            "amount":
                total_amount,
            "razorpay_order_id":
                razorpay_order_id
        }), 201
    except Exception as e:
        mydb.rollback()
        print("BOOKING ERROR:",e)
        return jsonify({"status": "failed","message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close

@app.route('/api/payment/verify', methods=['POST'])
def verify_payment():
    mydb = None
    cursor = None
    try:
        # Check login
        if not session.get("userid"):
            return jsonify({"status": "failed","message": "Please login first"}), 401
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"status": "failed","message": "No payment data given"}), 400
        booking_id = data.get("booking_id")
        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_payment_id = data.get("razorpay_payment_id")
        razorpay_signature = data.get("razorpay_signature")
        if not booking_id:
            return jsonify({"status": "failed","message": "Booking ID required"}), 400
        if not razorpay_order_id:
            return jsonify({"status": "failed","message": "Razorpay order ID required"}), 400
        if not razorpay_payment_id:
            return jsonify({"status": "failed","message": "Razorpay payment ID required"}), 400
        if not razorpay_signature:
            return jsonify({"status": "failed","message": "Razorpay signature required"}), 400
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        cursor.execute("""SELECT booking_id, razorpay_order_id FROM bookings WHERE booking_id = %s AND userid = %s""", (booking_id,session.get("userid")))
        booking = cursor.fetchone()
        if not booking:
            return jsonify({"status": "failed","message": "Booking not found"}), 404
        if booking[1] != razorpay_order_id:
            return jsonify({"status": "failed","message": "Invalid Razorpay order ID"}), 400
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        })
        cursor.execute("""UPDATE bookings SET payment_status = %s,status = %s,razorpay_payment_id = %s WHERE booking_id = %s AND userid = %s """, ( "Paid", "Confirmed",razorpay_payment_id, booking_id, session.get("userid")))
        mydb.commit()
        return jsonify({
            "status": "success",
            "message": "Payment verified successfully",
            "booking_id": booking_id,
            "payment_status": "Paid",
            "booking_status": "Confirmed"
        }), 200

    except razorpay.errors.SignatureVerificationError:
        mydb.rollback()

        return jsonify({"status": "failed","message": "Payment verification failed"}), 400
    except Exception as e:
        mydb.rollback()
        print("PAYMENT VERIFICATION ERROR:", e)
        return jsonify({"status": "failed","message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close()   
@app.route('/api/my-bookings', methods=['GET'])
def my_bookings():
    mydb = None
    cursor = None
    try:
        if not session.get("userid"):
            return jsonify({"status": "failed","message": "Please login first"}), 401
        userid = session.get("userid")
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        cursor.execute("""SELECT booking_id,name,email,phone,destination,travel_date,persons,message,status,created_at FROM bookings WHERE userid = %s ORDER BY booking_id DESC """, [userid])
        booking_data = cursor.fetchall()
        bookings = []
        for booking in booking_data:
            bookings.append({
                "booking_id": booking[0],
                "name": booking[1],
                "email": booking[2],
                "phone": booking[3],
                "destination": booking[4],
                "travel_date": str(booking[5]),
                "persons": booking[6],
                "message": booking[7],
                "status": booking[8],
                "created_at": str(booking[9])
            })
        return jsonify({"status": "success","bookings": bookings}), 200
    except Exception as e:
        print("MY BOOKINGS ERROR:", e)
        return jsonify({"status": "failed","message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close

@app.route('/api/bookings/<int:booking_id>', methods=['GET'])
def get_booking(booking_id):
    mydb = None
    cursor = None
    try:
        if not session.get("userid"):
            return jsonify({ "status": "failed","message": "Please login first"}), 401
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        cursor.execute("""SELECT booking_id,name,email,phone,destination,travel_date,persons,message,status,created_at FROM bookings WHERE booking_id = %s AND userid = %s""", [booking_id,session.get("userid")])
        booking = cursor.fetchone()
        if not booking:
            return jsonify({"status": "failed","message": "Booking not found"}), 404
        booking_data = {
            "booking_id": booking[0],
            "name": booking[1],
            "email": booking[2],
            "phone": booking[3],
            "destination": booking[4],
            "travel_date": str(booking[5]),
            "persons": booking[6],
            "message": booking[7],
            "status": booking[8],
            "created_at": str(booking[9])
        }
        return jsonify({"status": "success","booking": booking_data}), 200
    except Exception as e:
        print("BOOKING DETAILS ERROR:", e)
        return jsonify({
            "status": "failed","message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close()
@app.route('/api/bookings/<int:booking_id>', methods=['PUT'])
def customize_booking(booking_id):
    mydb = None
    cursor = None
    try:
        # Check login
        if not session.get("userid"):
            return jsonify({
                "status": "failed",
                "message": "Please login first"
            }), 401

        data = request.get_json(silent=True)
        print("CONTENT TYPE:", request.content_type)
        print("RAW DATA:", request.data)
        print("JSON DATA:", data)

        if not data:
            return jsonify({
                "status": "failed",
                "message": "No booking data given"
            }), 400

        # Get values from request
        name = data.get("name", "").strip()
        phone = data.get("phone", "").strip()
        travel_date = data.get("travel_date", "").strip()
        persons = data.get("persons")
        message = data.get("message", "").strip()

        # Validation
        if not name:
            return jsonify({
                "status": "failed",
                "message": "Name required"
            }), 400

        if not phone:
            return jsonify({
                "status": "failed",
                "message": "Phone required"
            }), 400

        if not travel_date:
            return jsonify({
                "status": "failed",
                "message": "Travel date required"
            }), 400

        if persons is None or persons == "":
            return jsonify({
                "status": "failed",
                "message": "Number of persons required"
            }), 400

        # Convert persons to integer
        try:
            persons = int(persons)
        except (ValueError, TypeError):
            return jsonify({
                "status": "failed",
                "message": "Persons must be a number"
            }), 400

        if persons <= 0:
            return jsonify({
                "status": "failed",
                "message": "Persons must be greater than zero"
            }), 400

        # Validate date format
        try:
            datetime.strptime(travel_date, "%Y-%m-%d")
        except ValueError:
            return jsonify({
                "status": "failed",
                "message": "Travel date must be YYYY-MM-DD"
            }), 400

        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)

        # Check that this booking belongs to logged-in user
        cursor.execute("""
            SELECT booking_id, status
            FROM bookings
            WHERE booking_id = %s AND userid = %s
        """, [booking_id, session.get("userid")])

        booking = cursor.fetchone()

        if not booking:
            return jsonify({
                "status": "failed",
                "message": "Booking not found"
            }), 404

        # Don't allow customization after cancellation
        if booking[1] == "Cancelled":
            return jsonify({
                "status": "failed",
                "message": "Cancelled booking cannot be customized"
            }), 400

        # Update booking
        cursor.execute("""
            UPDATE bookings
            SET name = %s,
                phone = %s,
                travel_date = %s,
                persons = %s,
                message = %s
            WHERE booking_id = %s
            AND userid = %s
        """, (
            name,
            phone,
            travel_date,
            persons,
            message,
            booking_id,
            session.get("userid")
        ))

        mydb.commit()

        return jsonify({
            "status": "success",
            "message": "Booking customized successfully",
            "booking_id": booking_id
        }), 200

    except Exception as e:

        if mydb:
            mydb.rollback()

        print("CUSTOMIZE BOOKING ERROR:", e)

        return jsonify({
            "status": "failed",
            "message": str(e)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if mydb:
            mydb.close()

@app.route('/api/bookings/<int:booking_id>', methods=['DELETE'])
def cancel_booking(booking_id):
    mydb = None
    cursor = None

    try:
        # Check login
        if not session.get("userid"):
            return jsonify({
                "status": "failed",
                "message": "Please login first"
            }), 401

        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)

        # Check whether this booking belongs to the logged-in user
        cursor.execute("""
            SELECT booking_id, status
            FROM bookings
            WHERE booking_id = %s
            AND userid = %s
        """, [
            booking_id,
            session.get("userid")
        ])

        booking = cursor.fetchone()

        # Booking not found
        if not booking:
            return jsonify({
                "status": "failed",
                "message": "Booking not found"
            }), 404

        # Already cancelled
        if booking[1] == "Cancelled":
            return jsonify({
                "status": "failed",
                "message": "Booking is already cancelled"
            }), 400

        # Cancel booking
        cursor.execute("""
            UPDATE bookings
            SET status = 'Cancelled'
            WHERE booking_id = %s
            AND userid = %s
        """, [
            booking_id,
            session.get("userid")
        ])

        mydb.commit()

        return jsonify({
            "status": "success",
            "message": "Booking cancelled successfully"
        }), 200

    except Exception as e:

        if mydb:
            mydb.rollback()

        print("CANCEL BOOKING ERROR:", e)

        return jsonify({
            "status": "failed",
            "message": str(e)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if mydb:
            mydb.close()

@app.route('/api/contact', methods=['POST'])
def contact():
    mydb = None
    cursor = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({ "status": "failed","message": "No input data given" }), 400
        name = data.get("name", "").strip()
        email = data.get("email", "").strip()
        phone = data.get("phone", "").strip()
        message = data.get("message", "").strip()
        if not name:
            return jsonify({"status": "failed","message": "Name required" }), 400
        if not email:
            return jsonify({"status": "failed", "message": "Email required"}), 400
        if not message:
            return jsonify({"status": "failed","message": "Message required" }), 400
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_pattern, email):
            return jsonify({"status": "failed","message": "Invalid email" }), 400
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        cursor.execute("""INSERT INTO contact_messages (name,email,phone,message)VALUES(%s,%s, %s,%s)""", [name,email,phone,message])
        mydb.commit()
        return jsonify({"status": "success", "message": "Your message has been submitted successfully"}), 201
    except Exception as e:
        mydb.rollback()
        print("CONTACT ERROR:", e)
        return jsonify({"status": "failed","message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close()

@app.route('/api/user/profile', methods=['GET'])
def user_profile():
    mydb = None
    cursor = None
    try:
        if not session.get("userid"):
            return jsonify({"status": "failed","message": "Please login first"}), 401
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        cursor.execute("""SELECT userid,name,email,phone,created_at FROM users WHERE userid = %s""", [session.get("userid")])
        user = cursor.fetchone()
        if not user:
            return jsonify({"status": "failed","message": "User not found"}), 404
        return jsonify({
            "status": "success",
            "user": {
                "userid": user[0],
                "name": user[1],
                "email": user[2],
                "phone": user[3],
                "created_at": str(user[4])
            }
        }), 200
    except Exception as e:
        print("PROFILE ERROR:", e)
        return jsonify({"status": "failed","message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close()
@app.route('/api/user/profile', methods=['PUT'])
def update_profile():
    mydb = None
    cursor = None
    try:
        if not session.get("userid"):
            return jsonify({"status": "failed","message": "Please login first"}), 401
        data = request.get_json()
        if not data:
            return jsonify({"status": "failed","message": "No data given"}), 400
        name = data.get("name", "").strip()
        phone = data.get("phone", "").strip()
        if not name:
            return jsonify({"status": "failed","message": "Name required"}), 400
        mydb = get_db_connection()
        cursor = mydb.cursor(buffered=True)
        cursor.execute(""" UPDATE users SET name = %s,phone = %s WHERE userid = %s""", [name, phone,session.get("userid")])
        mydb.commit()
        session["username"] = name
        return jsonify({"status": "success","message": "Profile updated successfully"}), 200
    except Exception as e:
        mydb.rollback()
        print("UPDATE PROFILE ERROR:", e)
        return jsonify({"status": "failed","message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if mydb:
            mydb.close()

print("REGISTERED ROUTES:")
for rule in app.url_map.iter_rules():
    print(rule)

if __name__ == "__main__":
    app.run()