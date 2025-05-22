from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from datetime import datetime, timedelta
import os
from models.database import init_db, db_session
from models.user import User, Role
from models.client import Client
from models.transaction import Transaction
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.supervisor import supervisor_bp
from routes.dealer import dealer_bp
from routes.client import client_bp
from routes.api import api_bp
from utils.date_utils import get_formatted_date

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cash_management.db'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)

# Activer CORS pour les routes API
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(supervisor_bp, url_prefix='/supervisor')
app.register_blueprint(dealer_bp, url_prefix='/dealer')
app.register_blueprint(client_bp, url_prefix='/client')
app.register_blueprint(api_bp)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize database
init_db()

# Register template filters
@app.template_filter('format_date')
def format_date(date):
    return get_formatted_date(date)

@app.template_filter('format_currency')
def format_currency(value, currency='CDF'):
    try:
        formatted = f"{float(value):,.2f}"
        return f"{formatted} {currency}"
    except (TypeError, ValueError):
        return f"0.00 {currency}"

# Register context processors
@app.context_processor
def inject_user_role():
    if current_user.is_authenticated:
        return {'user_role': current_user.role}
    return {'user_role': None}

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == Role.ADMIN:
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == Role.SUPERVISOR:
            return redirect(url_for('supervisor_dashboard'))
        elif current_user.role == Role.DEALER:
            return redirect(url_for('dealer_dashboard'))
    return render_template('index.html')

# Admin Routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != Role.ADMIN:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    # Appeler /api/stats pour les données du tableau de bord
    token = generate_token(current_user.id, current_user.role.value)
    headers = {'Authorization': f'Bearer {token}'}
    try:
        import requests
        response = requests.get('http://localhost:5000/api/stats', headers=headers)
        stats = response.json() if response.status_code == 200 else {}
    except:
        stats = {}
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/add_supervisor', methods=['GET', 'POST'])
@login_required
def admin_add_supervisor():
    if current_user.role != Role.ADMIN:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        data = {
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'username': request.form['username'],
            'email': request.form['email'],
            'password': request.form['password'],
            'phone_number': request.form.get('phone_number', ''),
            'commune': request.form.get('commune', ''),
            'city': request.form.get('city', 'Kinshasa'),
            'gender': request.form['gender'],
            'marital_status': request.form.get('marital_status', '')
        }
        token = generate_token(current_user.id, current_user.role.value)
        headers = {'Authorization': f'Bearer {token}'}
        try:
            import requests
            response = requests.post('http://localhost:5000/api/supervisors', json=data, headers=headers)
            if response.status_code == 201:
                flash('Superviseur ajouté avec succès', 'success')
                return redirect(url_for('admin_view_supervisor'))
            else:
                flash(response.json().get('error', 'Erreur lors de l\'ajout'), 'error')
        except Exception as e:
            flash(f'Erreur: {str(e)}', 'error')
    return render_template('admin/add_supervisor.html')

@app.route('/admin/edit_supervisor/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_edit_supervisor(id):
    if current_user.role != Role.ADMIN:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    token = generate_token(current_user.id, current_user.role.value)
    headers = {'Authorization': f'Bearer {token}'}
    if request.method == 'POST':
        data = {
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'username': request.form['username'],
            'email': request.form['email'],
            'phone_number': request.form.get('phone_number', ''),
            'commune': request.form.get('commune', ''),
            'city': request.form.get('city', 'Kinshasa'),
            'gender': request.form['gender'],
            'marital_status': request.form.get('marital_status', ''),
            'is_active': request.form.get('is_active', 'off') == 'on'
        }
        try:
            import requests
            response = requests.put(f'http://localhost:5000/api/supervisors/{id}', json=data, headers=headers)
            if response.status_code == 200:
                flash('Superviseur modifié avec succès', 'success')
                return redirect(url_for('admin_view_supervisor'))
            else:
                flash(response.json().get('error', 'Erreur lors de la modification'), 'error')
        except Exception as e:
            flash(f'Erreur: {str(e)}', 'error')
    try:
        import requests
        response = requests.get(f'http://localhost:5000/api/supervisors/{id}', headers=headers)
        if response.status_code == 200:
            supervisor = response.json()
            return render_template('admin/edit_supervisor.html', supervisor=supervisor)
        flash('Superviseur non trouvé', 'error')
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'error')
    return redirect(url_for('admin_view_supervisor'))

@app.route('/admin/view_supervisor')
@login_required
def admin_view_supervisor():
    if current_user.role != Role.ADMIN:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    token = generate_token(current_user.id, current_user.role.value)
    headers = {'Authorization': f'Bearer {token}'}
    try:
        import requests
        response = requests.get('http://localhost:5000/api/supervisors', headers=headers)
        supervisors = response.json() if response.status_code == 200 else []
    except:
        supervisors = []
    return render_template('admin/view_supervisor.html', supervisors=supervisors)

# Dealer Routes
@app.route('/dealer/dashboard')
@login_required
def dealer_dashboard():
    if current_user.role != Role.DEALER:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    return render_template('dealer/dashboard.html')

@app.route('/dealer/add_client', methods=['GET', 'POST'])
@login_required
def dealer_add_client():
    if current_user.role != Role.DEALER:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        data = {
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'post_nom': request.form.get('post_nom', ''),
            'gender': request.form['gender'],
            'marital_status': request.form.get('marital_status', ''),
            'email': request.form.get('email', ''),
            'phone_number': request.form.get('phone_number', ''),
            'commune': request.form.get('commune', ''),
            'city': request.form.get('city', 'Kinshasa')
        }
        token = generate_token(current_user.id, current_user.role.value)
        headers = {'Authorization': f'Bearer {token}'}
        try:
            import requests
            response = requests.post('http://localhost:5000/api/clients', json=data, headers=headers)
            if response.status_code == 201:
                flash('Client ajouté avec succès', 'success')
                return redirect(url_for('dealer_view_client'))
            else:
                flash(response.json().get('error', 'Erreur lors de l\'ajout'), 'error')
        except Exception as e:
            flash(f'Erreur: {str(e)}', 'error')
    return render_template('dealer/add_client.html')

@app.route('/dealer/view_client')
@login_required
def dealer_view_client():
    if current_user.role != Role.DEALER:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    token = generate_token(current_user.id, current_user.role.value)
    headers = {'Authorization': f'Bearer {token}'}
    try:
        import requests
        response = requests.get('http://localhost:5000/api/clients', headers=headers)
        clients = response.json() if response.status_code == 200 else []
    except:
        clients = []
    return render_template('dealer/view_client.html', clients=clients)

@app.route('/dealer/deposit', methods=['GET', 'POST'])
@login_required
def dealer_deposit():
    if current_user.role != Role.DEALER:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        client_id = request.form['client_id']
        data = {
            'amount': float(request.form['amount']),
            'description': request.form.get('description', '')
        }
        token = generate_token(current_user.id, current_user.role.value)
        headers = {'Authorization': f'Bearer {token}'}
        try:
            import requests
            response = requests.post(f'http://localhost:5000/api/clients/{client_id}/deposit', json=data, headers=headers)
            if response.status_code == 200:
                flash('Dépôt effectué avec succès', 'success')
                return redirect(url_for('dealer_view_client'))
            else:
                flash(response.json().get('error', 'Erreur lors du dépôt'), 'error')
        except Exception as e:
            flash(f'Erreur: {str(e)}', 'error')
    return render_template('dealer/deposit.html')

@app.route('/dealer/withdraw', methods=['GET', 'POST'])
@login_required
def dealer_withdraw():
    if current_user.role != Role.DEALER:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        client_id = request.form['client_id']
        data = {
            'amount': float(request.form['amount']),
            'description': request.form.get('description', '')
        }
        token = generate_token(current_user.id, current_user.role.value)
        headers = {'Authorization': f'Bearer {token}'}
        try:
            import requests
            response = requests.post(f'http://localhost:5000/api/clients/{client_id}/withdraw', json=data, headers=headers)
            if response.status_code == 200:
                flash('Retrait effectué avec succès', 'success')
                return redirect(url_for('dealer_view_client'))
            else:
                flash(response.json().get('error', 'Erreur lors du retrait'), 'error')
        except Exception as e:
            flash(f'Erreur: {str(e)}', 'error')
    return render_template('dealer/withdraw.html')

@app.route('/dealer/transaction', methods=['GET', 'POST'])
@login_required
def dealer_transaction():
    if current_user.role != Role.DEALER:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        client_id = request.form['client_id']
        transaction_type = request.form['type']
        token = generate_token(current_user.id, current_user.role.value)
        headers = {'Authorization': f'Bearer {token}'}
        try:
            import requests
            if transaction_type == 'activate':
                response = requests.post(f'http://localhost:5000/api/clients/{client_id}/activate', headers=headers)
            else:
                data = {
                    'amount': float(request.form['amount']),
                    'description': request.form.get('description', '')
                }
                response = requests.post(f'http://localhost:5000/api/clients/{client_id}/{transaction_type}', json=data, headers=headers)
            if response.status_code in [200, 201]:
                flash(f'{transaction_type.capitalize()} effectué avec succès', 'success')
                return redirect(url_for('dealer_view_client'))
            else:
                flash(response.json().get('error', f'Erreur lors du {transaction_type}'), 'error')
        except Exception as e:
            flash(f'Erreur: {str(e)}', 'error')
    return render_template('dealer/transaction.html')

# Supervisor Routes
@app.route('/supervisor/dashboard')
@login_required
def supervisor_dashboard():
    if current_user.role != Role.SUPERVISOR:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    return render_template('supervisor/dashboard.html')

@app.route('/supervisor/add_dealer', methods=['GET', 'POST'])
@login_required
def supervisor_add_dealer():
    if current_user.role != Role.SUPERVISOR:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        data = {
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'username': request.form['username'],
            'email': request.form['email'],
            'password': request.form['password'],
            'phone_number': request.form.get('phone_number', ''),
            'commune': request.form.get('commune', ''),
            'city': request.form.get('city', 'Kinshasa'),
            'gender': request.form['gender'],
            'marital_status': request.form.get('marital_status', '')
        }
        token = generate_token(current_user.id, current_user.role.value)
        headers = {'Authorization': f'Bearer {token}'}
        try:
            import requests
            response = requests.post('http://localhost:5000/api/dealers', json=data, headers=headers)
            if response.status_code == 201:
                flash('Dealer ajouté avec succès', 'success')
                return redirect(url_for('supervisor_view_dealer'))
            else:
                flash(response.json().get('error', 'Erreur lors de l\'ajout'), 'error')
        except Exception as e:
            flash(f'Erreur: {str(e)}', 'error')
    return render_template('supervisor/add_dealer.html')

@app.route('/supervisor/edit_dealer/<int:id>', methods=['GET', 'POST'])
@login_required
def supervisor_edit_dealer(id):
    if current_user.role != Role.SUPERVISOR:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    token = generate_token(current_user.id, current_user.role.value)
    headers = {'Authorization': f'Bearer {token}'}
    if request.method == 'POST':
        data = {
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'username': request.form['username'],
            'email': request.form['email'],
            'phone_number': request.form.get('phone_number', ''),
            'commune': request.form.get('commune', ''),
            'city': request.form.get('city', 'Kinshasa'),
            'gender': request.form['gender'],
            'marital_status': request.form.get('marital_status', ''),
            'is_active': request.form.get('is_active', 'off') == 'on'
        }
        try:
            import requests
            response = requests.put(f'http://localhost:5000/api/dealers/{id}', json=data, headers=headers)
            if response.status_code == 200:
                flash('Dealer modifié avec succès', 'success')
                return redirect(url_for('supervisor_view_dealer'))
            else:
                flash(response.json().get('error', 'Erreur lors de la modification'), 'error')
        except Exception as e:
            flash(f'Erreur: {str(e)}', 'error')
    try:
        import requests
        response = requests.get(f'http://localhost:5000/api/dealers/{id}', headers=headers)
        if response.status_code == 200:
            dealer = response.json()
            return render_template('supervisor/edit_dealer.html', dealer=dealer)
        flash('Dealer non trouvé', 'error')
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'error')
    return redirect(url_for('supervisor_view_dealer'))

@app.route('/supervisor/view_dealer')
@login_required
def supervisor_view_dealer():
    if current_user.role != Role.SUPERVISOR:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    token = generate_token(current_user.id, current_user.role.value)
    headers = {'Authorization': f'Bearer {token}'}
    try:
        import requests
        response = requests.get('http://localhost:5000/api/dealers', headers=headers)
        dealers = response.json() if response.status_code == 200 else []
    except:
        dealers = []
    return render_template('supervisor/view_dealer.html', dealers=dealers)

@app.route('/supervisor/add_premium_client', methods=['GET', 'POST'])
@login_required
def supervisor_add_premium_client():
    if current_user.role != Role.SUPERVISOR:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        data = {
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'post_nom': request.form.get('post_nom', ''),
            'gender': request.form['gender'],
            'marital_status': request.form.get('marital_status', ''),
            'email': request.form.get('email', ''),
            'phone_number': request.form.get('phone_number', ''),
            'commune': request.form.get('commune', ''),
            'city': request.form.get('city', 'Kinshasa')
        }
        token = generate_token(current_user.id, current_user.role.value)
        headers = {'Authorization': f'Bearer {token}'}
        try:
            import requests
            response = requests.post('http://localhost:5000/api/premium_clients', json=data, headers=headers)
            if response.status_code == 201:
                flash('Client premium ajouté avec succès', 'success')
                return redirect(url_for('supervisor_view_premium_client'))
            else:
                flash(response.json().get('error', 'Erreur lors de l\'ajout'), 'error')
        except Exception as e:
            flash(f'Erreur: {str(e)}', 'error')
    return render_template('supervisor/add_premium_client.html')

@app.route('/supervisor/edit_premium_client/<int:id>', methods=['GET', 'POST'])
@login_required
def supervisor_edit_premium_client(id):
    if current_user.role != Role.SUPERVISOR:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    token = generate_token(current_user.id, current_user.role.value)
    headers = {'Authorization': f'Bearer {token}'}
    if request.method == 'POST':
        data = {
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'post_nom': request.form.get('post_nom', ''),
            'gender': request.form['gender'],
            'marital_status': request.form.get('marital_status', ''),
            'email': request.form.get('email', ''),
            'phone_number': request.form.get('phone_number', ''),
            'commune': request.form.get('commune', ''),
            'city': request.form.get('city', 'Kinshasa'),
            'is_active': request.form.get('is_active', 'off') == 'on'
        }
        try:
            import requests
            response = requests.put(f'http://localhost:5000/api/premium_clients/{id}', json=data, headers=headers)
            if response.status_code == 200:
                flash('Client premium modifié avec succès', 'success')
                return redirect(url_for('supervisor_view_premium_client'))
            else:
                flash(response.json().get('error', 'Erreur lors de la modification'), 'error')
        except Exception as e:
            flash(f'Erreur: {str(e)}', 'error')
    try:
        import requests
        response = requests.get(f'http://localhost:5000/api/premium_clients/{id}', headers=headers)
        if response.status_code == 200:
            client = response.json()
            return render_template('supervisor/edit_premium_client.html', client=client)
        flash('Client premium non trouvé', 'error')
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'error')
    return redirect(url_for('supervisor_view_premium_client'))

@app.route('/supervisor/view_premium_client')
@login_required
def supervisor_view_premium_client():
    if current_user.role != Role.SUPERVISOR:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    token = generate_token(current_user.id, current_user.role.value)
    headers = {'Authorization': f'Bearer {token}'}
    try:
        import requests
        response = requests.get('http://localhost:5000/api/premium_clients', headers=headers)
        clients = response.json() if response.status_code == 200 else []
    except:
        clients = []
    return render_template('supervisor/view_premium_client.html', clients=clients)

@app.route('/supervisor/deposit_premium_client', methods=['GET', 'POST'])
@login_required
def supervisor_deposit_premium_client():
    if current_user.role != Role.SUPERVISOR:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        client_id = request.form['client_id']
        data = {
            'amount': float(request.form['amount']),
            'description': request.form.get('description', '')
        }
        token = generate_token(current_user.id, current_user.role.value)
        headers = {'Authorization': f'Bearer {token}'}
        try:
            import requests
            response = requests.post(f'http://localhost:5000/api/premium_clients/{client_id}/deposit', json=data, headers=headers)
            if response.status_code == 200:
                flash('Dépôt effectué avec succès', 'success')
                return redirect(url_for('supervisor_view_premium_client'))
            else:
                flash(response.json().get('error', 'Erreur lors du dépôt'), 'error')
        except Exception as e:
            flash(f'Erreur: {str(e)}', 'error')
    return render_template('supervisor/deposit_premium_client.html')

@app.route('/supervisor/withdraw_premium_client', methods=['GET', 'POST'])
@login_required
def supervisor_withdraw_premium_client():
    if current_user.role != Role.SUPERVISOR:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        client_id = request.form['client_id']
        data = {
            'amount': float(request.form['amount']),
            'description': request.form.get('description', '')
        }
        token = generate_token(current_user.id, current_user.role.value)
        headers = {'Authorization': f'Bearer {token}'}
        try:
            import requests
            response = requests.post(f'http://localhost:5000/api/premium_clients/{client_id}/withdraw', json=data, headers=headers)
            if response.status_code == 200:
                flash('Retrait effectué avec succès', 'success')
                return redirect(url_for('supervisor_view_premium_client'))
            else:
                flash(response.json().get('error', 'Erreur lors du retrait'), 'error')
        except Exception as e:
            flash(f'Erreur: {str(e)}', 'error')
    return render_template('supervisor/withdraw_premium_client.html')

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

if __name__ == '__main__':
    app.run(debug=True)