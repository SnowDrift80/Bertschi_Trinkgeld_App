# app/routes.py

# 1. Standard Library
import os
import re
import locale
import tempfile
import textwrap
import time
import pytz
import json
from decimal import Decimal, InvalidOperation
from io import BytesIO
from datetime import datetime, date, timedelta
from datetime import time as dt_time
from functools import wraps

# 2. Third-party
import pandas as pd

from flask import (
    render_template, request, session, redirect, url_for, abort,
    flash, jsonify, send_file, after_this_request, make_response,
    Response
)
from flask_wtf.csrf import generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFError

from sqlalchemy import desc, or_, and_, func
from openpyxl import Workbook


# 3. Local application (your models)
from app.models import (
    db, User, LocationList,TipH, TipD
)
from .helpers.helper import AppDate, FileHandling



limiter = Limiter(get_remote_address)
locale.setlocale(locale.LC_TIME, "de_CH.UTF-8") 



def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated


def setup_routes(app):

    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=lambda: f'<input type="hidden" name="csrf_token" value="{generate_csrf()}">')


    @app.route("/")
    @limiter.limit("20 per minute")
    def index():
        # already logged in? → skip login form
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        user = None
        if "user_id" in session:
            user = User.query.get(session["user_id"])
        return render_template("index.html", topbar_title="Trinkgelderfassung - Login", current_date=AppDate.get_current_date_header(), user=user)


    @app.route("/login", methods=["GET", "POST"])
    @limiter.limit("20 per minute")
    def login():
        if request.method == "POST":
            email = request.form["email"]
            password = request.form["password"]
            user = User.query.filter_by(email=email).first()

            if user and user.check_password(password):
                session["user_id"] = user.id
                # optional: reset location on fresh login
                session.pop("selected_location", None)
                return redirect(url_for("dashboard"))

            # failed login → show form again
            return render_template(
                "index.html",
                topbar_title="Trinkgelderfassung - Login",
                current_date=AppDate.get_current_date_header(),
                user=None,
            )

        # GET request → show login form
        return render_template(
            "index.html",
            topbar_title="Trinkgelderfassung - Login",
            current_date=AppDate.get_current_date_header(),
            user=None,
        )


    @app.get("/api/users-for-export")
    @login_required
    def api_users_for_export():
        # Expected query params:
        #   all=1|0  (1 => all locations)
        #   location=<code> (only used when all=0 and provided)
        get_all = request.args.get("all") == "1"
        location = request.args.get("location")

        q = User.query
        if not get_all and location:
            q = q.filter(User.location == location)

        users = q.order_by(User.location.asc(), User.name.asc()).all()

        return jsonify([
            {
                "id": u.id,
                "name": u.name,           # or u.full_name
                "username": u.email,
                "location": u.location,
            }
            for u in users
        ])


    @app.route("/dashboard")
    @login_required
    def dashboard():
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("index"))

        user = User.query.get(user_id)
        today = date.today()

        # Default location is the user's own location
        selected_location = session.get("selected_location")

        # === Initial lists for export modal: show ALL users by default (superadmin stats) ===
        all_users_sorted = (
            User.query
                .order_by(User.location.asc(), User.name.asc())
                .all()
        )
        current_location_users = []  # empty "current" section by default
        other_location_users = all_users_sorted

        # Step 1: Get all TipH reports for today
        reports_today = (
            db.session.query(TipH.location, TipH.username)
            .filter(func.date(TipH.timestamp) == today)
            .all()
        )

        # Step 2: Build a set of locations that were reported today by someone else
        locations_with_report_by_other = {
            location for location, username in reports_today if username != user.name
        }

        # Step 3: Filter all_locations to exclude those
        all_locations = (
            LocationList.query
            .filter(~LocationList.location.in_(locations_with_report_by_other))
            .order_by(LocationList.location)
            .all()
        )

        full_locations_list = (
            LocationList.query
            .order_by(LocationList.location)
            .all()
        )

        seven_days_ago = today - timedelta(days=6)

        # Check if today's report exists for selected location
        existing_report = (
            TipH.query
            .filter(
                db.func.date(TipH.timestamp) == today,
                TipH.location == selected_location,
                TipH.username == user.name
            )
            .first()
        )

        # Tip list: if no selection yet and user is not superadmin, show nothing
        if user.role == "superadmin":
            tiph_entries = (
                TipH.query
                .filter(db.func.date(TipH.timestamp) >= seven_days_ago)
                .order_by(TipH.timestamp.desc(), TipH.location)
                .all()
            )
        else:
            tiph_entries = (
                TipH.query
                .filter(
                    db.func.date(TipH.timestamp) >= seven_days_ago,
                    TipH.location == selected_location
                )
                .order_by(TipH.timestamp.desc())
                .all()
            )

        tip_totals = {
            tip.tiph_id: db.session.query(func.coalesce(func.sum(TipD.amount_chf), 0))
                .filter_by(tiph_id=tip.tiph_id)
                .scalar()
            for tip in tiph_entries
        }

        return render_template(
            "dashboard.html",
            topbar_title="Trinkgelderfassung - Dashboard",
            user=user,
            current_date=AppDate.get_current_date_header(),
            existing_report=existing_report,
            tiph_entries=tiph_entries,
            selected_location=selected_location, 
            all_locations=all_locations,
            full_locations_list=full_locations_list,
            tip_totals=tip_totals,
            # lists for the modal user dropdown (initially "all users")
            current_location_users=current_location_users,
            other_location_users=other_location_users,
        )

    

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        session.clear()
        return redirect(url_for("index"))
    

    @app.route("/admin")
    @login_required
    def admin():
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("index"))

        user = User.query.get(user_id)
        if user.role not in ["admin", "superadmin"]:
            return abort(403)  # Forbidden

        return render_template("admin/admin.html", topbar_title="RP Trinkgelderfassung - Administration", user=user, current_date=AppDate.get_current_date_header())


    @app.route("/admin/users/<int:user_id>", methods=["GET"])
    @login_required
    def get_user(user_id):
        user_id_session = session.get("user_id")
        if not user_id_session:
            return redirect(url_for("index"))

        current_user = User.query.get(user_id_session)
        if current_user.role not in ["admin", "superadmin"]:
            abort(403)

        user_to_edit = User.query.get_or_404(user_id)
        locations = LocationList.query.order_by(LocationList.location).all()  # 🔥 Fetch location list        
        return render_template("admin/users/partials/user_form.html", user_to_edit=user_to_edit, user=current_user, locations=locations)


    @app.route("/admin/users", methods=["GET", "POST"])
    @login_required
    def user_management():
        user_id_session = session.get("user_id")
        if not user_id_session:
            return redirect(url_for("index"))

        current_user = User.query.get(user_id_session)
        if current_user.role not in  ["admin", "superadmin"]:
            abort(403)

        if request.method == "POST":
            user_id = request.form.get("user_id")
            name = request.form["name"]
            email = request.form["email"]
            password = request.form.get("password")
            location = request.form["location"]
            role = request.form["role"]

            if user_id:
                # Update existing user
                user = User.query.get(int(user_id))
                user.name = name
                user.email = email
                user.location = location
                user.role = role
                if password:
                    user.set_password(password)
            else:
                # Check if email already exists
                existing_user = User.query.filter_by(email=email).first()
                if existing_user:
                    flash("Ein Benutzer mit dieser E-Mail-Adresse existiert bereits.", "email_exists")
                    return redirect(url_for("user_management"))  # or render_template if you want to keep form state

                # Create new user
                user = User(name=name, email=email, location=location, role=role)
                if password:
                    user.set_password(password)
                db.session.add(user)

            db.session.commit()
            return redirect(url_for("user_management"))

        users = User.query.all()
        locations = LocationList.query.order_by(LocationList.location).all()  # 🔥 Fetch location list        
        return render_template("admin/users/user_management.html", user=current_user, users=users, topbar_title="Administration - Benutzer", locations=locations, current_date=AppDate.get_current_date_header())


    @app.route("/admin/users/<int:user_id>/deactivate", methods=["POST"])
    @login_required
    def deactivate_user(user_id):
        user_id_session = session.get("user_id")
        if not user_id_session:
            return redirect(url_for("index"))

        current_user = User.query.get(user_id_session)
        if current_user.role not in ["admin", "superadmin"]:
            abort(403)

        user_to_deactivate = User.query.get_or_404(user_id)
        db.session.delete(user_to_deactivate)
        db.session.commit()
        return redirect(url_for("user_management"))


    @app.route("/admin/masterdata")
    @login_required
    def masterdata_import():
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("index"))

        current_user = User.query.get(user_id)
        if current_user.role != "superadmin":
            abort(403)

        from datetime import date
        return render_template("admin/masterdata/masterdata_import.html", user=current_user, topbar_title="Administration - Stammdaten", current_date=AppDate.get_current_date_header())


    @app.route("/admin/masterdata/location-list")
    @login_required
    def import_location_list():
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("index"))

        user = User.query.get(user_id)

        locations = LocationList.query.order_by(LocationList.location).all()

        return render_template("admin/masterdata/location_list_import.html", user=user, topbar_title="Stammdaten - Standortliste", current_date=AppDate.get_current_date_header(), locations=locations)


    @app.route("/admin/masterdata/location-list/upload", methods=["POST"])
    @login_required
    def import_location_list_upload():
        file = request.files.get("file")
        if not file or not FileHandling.allowed_file(file.filename):
            flash("Bitte eine gültige Excel-Datei (.xlsx) hochladen.")
            return redirect(url_for("import_location_list"))

        try:
            df = pd.read_excel(file)
            required_columns = ["Ort", "Firma", "Strasse", "Plz_Ort", "Tel", "Email", "Url"]
            if not all(col in df.columns for col in required_columns):
                flash("Die Excel-Datei muss die folgenden Spalten enthalten: " + ", ".join(required_columns))
                return redirect(url_for("import_location_list"))

            LocationList.query.delete()

            for _, row in df.iterrows():
                location = LocationList(
                    location=row["Ort"],
                    entity=row["Firma"],
                    street_no=row["Strasse"],
                    zip_place=row["Plz_Ort"],
                    phone=row["Tel"],
                    email=row["Email"],
                    url=row["Url"]
                )
                db.session.add(location)

            db.session.commit()
            flash("Standortliste erfolgreich importiert.")
        except Exception as e:
            flash(f"Fehler beim Import: {e}")

        return redirect(url_for("import_location_list"))


    @app.route("/admin/masterdata/location-list/export", methods=["GET"])
    @login_required
    def export_location_list():
        output = BytesIO()

        locations = LocationList.query.all()
        df = pd.DataFrame([{
            "Ort": l.location,
            "Firma": l.entity,
            "Strasse": l.street_no,
            "Plz_Ort": l.zip_place,
            "Tel": l.phone,
            "Email": l.email,
            "Url": l.url
        } for l in locations])

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)

        output.seek(0)

        return send_file(output,
                        download_name="standortliste.xlsx",
                        as_attachment=True,
                        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    


    @app.route("/tip/create")
    @login_required
    def create_tip():
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("index"))
        
        if not session.get('selected_location'):
            flash('Bitte wählen Sie zuerst einen Standort.')
            return redirect(url_for('dashboard'))        

        user = User.query.get(user_id)

        zurich_tz = pytz.timezone("Europe/Zurich")
        now_local = datetime.now(zurich_tz).replace(tzinfo=None)

        # Use selected location from session if available
        selected_location = session.get("selected_location", user.location)

        new_tip = TipH(
            location=selected_location,
            username=user.name,
            timestamp=now_local
        )

        db.session.add(new_tip)
        db.session.commit()

        return redirect(url_for("edit_tip", tiph_id=new_tip.tiph_id))


    @app.route("/tip/edit/<int:tiph_id>")
    @login_required
    def edit_tip(tiph_id):
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("index"))

        operator = User.query.get(user_id)
        tip = TipH.query.get_or_404(tiph_id)


        # Fetch all users
        all_users = User.query.order_by(User.location, User.name).all()

        # Get used usernames from TipD
        details = TipD.query.filter_by(tiph_id=tip.tiph_id).order_by(TipD.tipd_id).all()
        used_usernames = {d.username for d in details}

        # Filter out users already in details
        available_users = [
            u for u in all_users
            if u.name not in used_usernames and u.name.lower() != "admin"
        ]

        # Separate users by location
        users_by_location = {}
        for user in available_users:
            users_by_location.setdefault(user.location, []).append(user)

        # Optional: sort user lists within each location
        for user_list in users_by_location.values():
            user_list.sort(key=lambda u: u.name)

        # Location name for current location group header
        current_location = tip.location

        # User location lookup for display in the table
        user_location_lookup = {u.name: u.location for u in all_users}

        total_amount = db.session.query(func.coalesce(func.sum(TipD.amount_chf), 0)).filter_by(tiph_id=tip.tiph_id).scalar()

        return render_template(
            "edit_tip.html",
            tip=tip,
            details=details,
            users_by_location=users_by_location,
            current_location=current_location,
            user_location_lookup=user_location_lookup,
            total_amount=total_amount,
            topbar_title="Trinkgeldabrechnung bearbeiten",
            current_date=AppDate.get_current_date_header(),
            operator=operator
        )


    @app.route("/tip/<int:tiph_id>/add", methods=["POST"])
    @login_required
    def add_tip_detail(tiph_id):
        username = request.form.get("username")
        duration = request.form.get("duration")
        amount_chf = request.form.get("amount_chf")

        new_detail = TipD(
            tiph_id=tiph_id,
            username=username,
            duration=duration,
            amount_chf=amount_chf
        )
        db.session.add(new_detail)
        db.session.commit()

        return redirect(url_for("edit_tip", tiph_id=tiph_id))



    @app.route("/tip/detail/<int:tipd_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_tip_detail(tipd_id):
        detail = TipD.query.get_or_404(tipd_id)
        tip = TipH.query.get_or_404(detail.tiph_id)

        users_current_loc = User.query.filter_by(location=tip.location).order_by(User.name).all()
        users_other_locs = User.query.filter(User.location != tip.location).order_by(User.name).all()

        if request.method == "POST":
            detail.username = request.form.get("username")
            detail.duration = request.form.get("duration")
            detail.amount_chf = request.form.get("amount_chf")
            db.session.commit()
            return redirect(url_for("edit_tip", tiph_id=tip.tiph_id))

        return render_template(
            "edit_tip_detail.html",
            detail=detail,
            tip=tip,
            users_current_loc=users_current_loc,
            users_other_locs=users_other_locs
        )



    @app.route("/tip/detail/<int:tipd_id>/delete", methods=["POST"])
    @login_required
    def delete_tip_detail(tipd_id):
        detail = TipD.query.get_or_404(tipd_id)
        tiph_id = detail.tiph_id

        db.session.delete(detail)
        db.session.commit()

        return redirect(url_for("edit_tip", tiph_id=tiph_id))


    @app.route("/delete-tip/<int:tiph_id>", methods=["POST"])
    @login_required
    def delete_tip(tiph_id):
        tiph = TipH.query.get_or_404(tiph_id)
        db.session.delete(tiph)
        db.session.commit()
        flash("Trinkgeldabrechnung wurde gelöscht.", "success")
        return redirect(url_for("dashboard"))


    @app.route("/select-location", methods=["POST"])
    @login_required
    def select_location():
        location = request.form.get("location")
        if location:
            session["selected_location"] = location
        return redirect(url_for("dashboard"))




    @app.route("/export-tip-data", methods=["POST"])
    @login_required
    def export_tip_data():
        from_date = request.form.get("date_from")
        to_date = request.form.get("date_to")
        all_locations = request.form.get("all_locations") == "on"
        selected_location = request.form.get("location")
        # NEW: user filter
        user_id_raw = (request.form.get("user_id") or "").strip()
        user_id = int(user_id_raw) if user_id_raw.isdigit() else None

        from_dt = datetime.strptime(from_date, "%Y-%m-%d")
        to_dt = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)

        query = (
            db.session.query(
                TipH.timestamp,
                TipH.location,
                TipH.username.label("reporter"),
                TipD.username.label("worker"),
                TipD.duration,
                TipD.amount_chf
            )
            .join(TipD, TipH.tiph_id == TipD.tiph_id)
            .filter(TipH.timestamp >= from_dt)
            .filter(TipH.timestamp < to_dt)
        )

        if not all_locations and selected_location:
            query = query.filter(TipH.location == selected_location)

        # 🔧 NEW: filter by selected employee (maps id -> User.name -> TipD.username)
        if user_id is not None:
            u = User.query.get(user_id)
            chosen_name = (u.name.strip() if u and u.name else None)
            if chosen_name:
                query = query.filter(TipD.username == chosen_name)
            else:
                current_app.logger.warning(
                    "Export user filter requested but user not found or has no name: user_id=%s", user_id
                )

        records = query.all()

        df = pd.DataFrame(records, columns=[
            "timestamp",
            "location",
            "reporter",
            "worker",
            "duration",
            "amount_chf"
        ])

        if df.empty:
            # keep headers in the export even if no matches
            df = pd.DataFrame(columns=["timestamp","location","reporter","worker","duration","amount_chf"])

        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.date
        df["amount_chf"] = pd.to_numeric(df["amount_chf"]).round(2)
        df["duration"] = df["duration"].apply(lambda d: {
            "vormittag": "Vormittag",
            "nachmittag": "Nachmittag",
            "ganzer_tag": "ganzer Tag"
        }.get(d.name if hasattr(d, "name") else str(d), str(d)))

        df.rename(columns={
            "timestamp": "Datum",
            "location": "Standort",
            "reporter": "Melder",
            "worker": "Mitarbeiter",
            "duration": "Einsatzzeit",
            "amount_chf": "Trinkgeld_CHF"
        }, inplace=True)

        df.sort_values(by=["Datum", "Standort", "Mitarbeiter"], inplace=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Trinkgelder")
        output.seek(0)

        return send_file(
            output,
            download_name="trinkgelder_export.xlsx",
            as_attachment=True,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        flash("Deine Sitzung ist abgelaufen. Bitte aktualisiere die Seite oder melde dich erneut an.", "error")
        return redirect(url_for("index"))


    @app.route("/debug-csrf-timeout")
    def debug_csrf_timeout():
        return f"WTF_CSRF_TIME_LIMIT is set to: {app.config.get('WTF_CSRF_TIME_LIMIT')}"


    @app.route("/admin/users/search", methods=["GET"])
    def search_users():
        q = (request.args.get("q") or "").strip()

        if q:
            # Postgres:
            users = (User.query
                    .filter(or_(User.name.ilike(f"%{q}%"),
                                User.email.ilike(f"%{q}%")))
                    .order_by(User.name.asc())
                    .all())
        else:
            users = User.query.order_by(User.name.asc()).all()

        # Return only the rows so HTMX swaps the <tbody> content
        return render_template("admin/users/partials/user_rows.html", users=users)
    

    def _calc_total_for_header(tiph_id):
        total = db.session.query(func.coalesce(func.sum(TipD.amount_chf), 0)) \
                        .filter(TipD.tiph_id == tiph_id).scalar()
        # ensure Decimal with 2 dp
        if total is None:
            total = Decimal("0.00")
        if not isinstance(total, Decimal):
            total = Decimal(total)
        return total.quantize(Decimal("0.01"))
    

    @app.get("/tip-detail/<int:tipd_id>/amount/edit")
    def edit_tipd_amount(tipd_id):
        d = TipD.query.get_or_404(tipd_id)
        return render_template("partials/tipd_row_edit_amount.html", d=d)

    @app.get("/tip-detail/<int:tipd_id>/row/view")
    def view_tipd_row(tipd_id):
        d = TipD.query.get_or_404(tipd_id)
        return render_template("partials/tipd_row_view.html", d=d)


    @app.post("/tip-detail/<int:tipd_id>/amount/update", endpoint="update_tipd_amount")
    def update_tipd_amount(tipd_id):
        d = TipD.query.get_or_404(tipd_id)
        raw = (request.form.get("amount_chf") or "").strip()

        if raw == "":
            return _render_row_edit_with_error(d, "Bitte Betrag eingeben.")
        try:
            amount = Decimal(raw.replace(",", "."))
        except InvalidOperation:
            return _render_row_edit_with_error(d, "Ungültiger Betrag.")
        if amount < 0:
            return _render_row_edit_with_error(d, "Negativer Betrag ist nicht erlaubt.")

        d.amount_chf = amount.quantize(Decimal("0.01"))
        db.session.commit()

        # return only the <tr>
        html_row = render_template("partials/tipd_row_view.html", d=d)
        total_amount = _calc_total_for_header(d.tiph_id)  # Decimal(2dp)

        resp = make_response(html_row, 200)
        # 🔁 fire AFTER the swap so the listener definitely sees it
        resp.headers["HX-Trigger-After-Swap"] = json.dumps({"update-total": float(total_amount)})
        return resp


    def _render_row_edit_with_error(d, msg):
        # Keep error path simple: just re-render the edit row (no OOB/trigger)
        html_row = render_template("partials/tipd_row_edit_amount.html", d=d, error=msg)
        return html_row, 400
