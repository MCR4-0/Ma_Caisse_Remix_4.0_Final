from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from forms.client_form import ClientForm
from forms.transaction_form import TransactionForm
from models.user import User, Role
from models.client import Client
from models.transaction import Transaction, TransactionType
from models.database import db_session
from utils.decorators import dealer_required
from datetime import datetime, timedelta
from sqlalchemy import or_, func
from werkzeug.exceptions import NotFound
import uuid

dealer_bp = Blueprint('dealer', __name__)

@dealer_bp.route('/dashboard', methods=['GET'])
@login_required
@dealer_required
def dashboard():
    # Get search query from request
    search_query = request.args.get('search', '').strip()

    # Base query for all clients (no dealer_id filter to show all clients)
    client_query = Client.query

    # Apply search filter if provided
    if search_query:
        client_query = client_query.filter(
            or_(
                Client.first_name.ilike(f'%{search_query}%'),
                Client.last_name.ilike(f'%{search_query}%'),
                Client.code.ilike(f'%{search_query}%'),
                Client.account_number.ilike(f'%{search_query}%')
            )
        )

    # Get all clients (filtered or not)
    clients = client_query.all()
    client_count = len(clients)

    # Calculate statistics
    active_clients = [client for client in clients if client.is_active]
    inactive_clients = [client for client in clients if not client.is_active]
    active_client_count = len(active_clients)
    inactive_client_count = len(inactive_clients)

    # Total balance (sum of client balances)
    total_balance = sum(client.balance for client in clients)

    # Total activation fees (sum of ACTIVATION transactions)
    total_activation_fees = db_session.query(
        func.sum(Transaction.amount)
    ).filter(
        Transaction.transaction_type == TransactionType.ACTIVATION,
        Transaction.client_id.in_([client.id for client in clients])
    ).scalar() or 0

    # Get recent transactions for all clients
    recent_transactions = Transaction.query.join(Client).order_by(
        Transaction.transaction_date.desc()
    ).limit(10).all()

    return render_template(
        'dealer/dashboard.html',
        title='Tableau de bord du dealer',
        client_count=client_count,
        active_client_count=active_client_count,
        inactive_client_count=inactive_client_count,
        total_balance=total_balance,
        total_activation_fees=total_activation_fees,
        clients=clients,
        active_clients=active_clients,
        inactive_clients=inactive_clients,
        recent_transactions=recent_transactions,
        search_query=search_query
    )

@dealer_bp.route('/client/add', methods=['GET', 'POST'])
@login_required
@dealer_required
def add_client():
    form = ClientForm()
    
    if form.validate_on_submit():
        # Generate unique code and account number
        code = f"CLT{uuid.uuid4().hex[:6].upper()}"
        account_number = f"{datetime.now().strftime('%y%m%d')}{uuid.uuid4().hex[:8].upper()}"
        
        # Create new client
        new_client = Client(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            gender=form.gender.data,
            code=code,
            account_number=account_number,
            dealer_id=current_user.id
        )
        
        db_session.add(new_client)
        db_session.commit()
        flash(f'Client {new_client.full_name} créé avec succès', 'success')
        return redirect(url_for('dealer.dashboard'))
    
    return render_template('dealer/add_client.html', form=form, title='Ajouter un client')

@dealer_bp.route('/client/<int:client_id>')
@login_required
@dealer_required
def view_client(client_id):
    # Get client (no dealer_id restriction to allow all dealers to view)
    client = Client.query.filter_by(id=client_id).first()
    if not client:
        raise NotFound('Client non trouvé')
    
    # Get the dealer who added the client
    dealer = User.query.filter_by(id=client.dealer_id).first()
    dealer_name = dealer.full_name if dealer else 'Inconnu'

    # Get all transactions for this client
    transactions = Transaction.query.filter_by(client_id=client_id).order_by(
        Transaction.transaction_date.desc()
    ).all()
    
    # Calculate available balance (considering 30-day rule)
    withdrawable_balance = 0
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    for transaction in transactions:
        if transaction.transaction_type == TransactionType.DEPOSIT and transaction.transaction_date <= thirty_days_ago:
            withdrawable_balance += transaction.amount
        elif transaction.transaction_type == TransactionType.WITHDRAWAL:
            withdrawable_balance -= transaction.amount
    
    return render_template(
        'dealer/view_client.html',
        client=client,
        dealer_name=dealer_name,
        transactions=transactions,
        withdrawable_balance=withdrawable_balance,
        title=f'Client: {client.full_name}'
    )

@dealer_bp.route('/client/<int:client_id>/activate', methods=['GET', 'POST'])
@login_required
@dealer_required
def activate_client(client_id):
    # Get client (no dealer_id restriction)
    client = Client.query.filter_by(id=client_id).first()
    if not client:
        raise NotFound('Client non trouvé')
    
    if client.is_active:
        flash('Le compte client est déjà actif', 'info')
        return redirect(url_for('dealer.view_client', client_id=client_id))
    
    activation_fee = 3000  # Frais d'activation de 3000fc
    
    if client.balance < activation_fee:
        flash(f'Le client doit avoir au moins {activation_fee}fc sur son compte pour l\'activer', 'warning')
        return redirect(url_for('dealer.view_client', client_id=client_id))
    
    if client.activate_account(activation_fee):
        # Record activation transaction
        activation_transaction = Transaction(
            amount=activation_fee,
            transaction_type=TransactionType.ACTIVATION,
            description="Frais d'activation du compte",
            client_id=client.id,
            performed_by_id=current_user.id
        )
        
        db_session.add(activation_transaction)
        db_session.commit()
        
        flash('Compte client activé avec succès', 'success')
    else:
        flash('Échec de l\'activation du compte client', 'danger')
    
    return redirect(url_for('dealer.view_client', client_id=client_id))

@dealer_bp.route('/client/<int:client_id>/deposit', methods=['GET', 'POST'])
@login_required
@dealer_required
def deposit(client_id):
    # Get client (no dealer_id restriction)
    client = Client.query.filter_by(id=client_id).first()
    if not client:
        raise NotFound('Client non trouvé')
    
    form = TransactionForm()
    
    if form.validate_on_submit():
        # Process deposit
        amount = form.amount.data
        description = form.description.data
        
        # Update client balance
        client.balance += amount
        
        # Create transaction record
        transaction = Transaction(
            amount=amount,
            transaction_type=TransactionType.DEPOSIT,
            description=description,
            client_id=client.id,
            performed_by_id=current_user.id
        )
        
        db_session.add(transaction)
        db_session.commit()
        
        flash(f'Dépôt de {amount}fc effectué avec succès', 'success')
        return redirect(url_for('dealer.view_client', client_id=client_id))
    
    return render_template(
        'dealer/deposit.html',
        form=form,
        client=client,
        title=f'Dépôt pour {client.full_name}'
    )

@dealer_bp.route('/client/<int:client_id>/withdraw', methods=['GET', 'POST'])
@login_required
@dealer_required
def withdraw(client_id):
    # Get client (no dealer_id restriction)
    client = Client.query.filter_by(id=client_id).first()
    if not client:
        raise NotFound('Client non trouvé')
    
    if not client.is_active:
        flash('Impossible de retirer depuis un compte inactif', 'warning')
        return redirect(url_for('dealer.view_client', client_id=client_id))
    
    form = TransactionForm()
    
    # Calculate withdrawable balance (considering 30-day rule)
    withdrawable_balance = 0
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    transactions = Transaction.query.filter_by(client_id=client_id).all()
    for transaction in transactions:
        if transaction.transaction_type == TransactionType.DEPOSIT and transaction.transaction_date <= thirty_days_ago:
            withdrawable_balance += transaction.amount
        elif transaction.transaction_type == TransactionType.WITHDRAWAL:
            withdrawable_balance -= transaction.amount
    
    if form.validate_on_submit():
        # Process withdrawal
        amount = form.amount.data
        description = form.description.data
        
        if amount > withdrawable_balance:
            flash(f'Impossible de retirer plus que le solde disponible de {withdrawable_balance}fc', 'danger')
            return redirect(url_for('dealer.withdraw', client_id=client_id))
        
        # Update client balance
        client.balance -= amount
        
        # Create transaction record
        transaction = Transaction(
            amount=amount,
            transaction_type=TransactionType.WITHDRAWAL,
            description=description,
            client_id=client.id,
            performed_by_id=current_user.id
        )
        
        db_session.add(transaction)
        db_session.commit()
        
        flash(f'Retrait de {amount}fc effectué avec succès', 'success')
        return redirect(url_for('dealer.view_client', client_id=client_id))
    
    return render_template(
        'dealer/withdraw.html',
        form=form,
        client=client,
        withdrawable_balance=withdrawable_balance,
        title=f'Retrait pour {client.full_name}'
    )

@dealer_bp.route('/client/<int:client_id>/transactions')
@login_required
@dealer_required
def client_transactions(client_id):
    # Get client (no dealer_id restriction)
    client = Client.query.filter_by(id=client_id).first()
    if not client:
        raise NotFound('Client non trouvé')
    
    # Get all transactions for this client
    transactions = Transaction.query.filter_by(client_id=client_id).order_by(
        Transaction.transaction_date.desc()
    ).all()
    
    return render_template(
        'dealer/transactions.html',
        client=client,
        transactions=transactions,
        title=f'Transactions pour {client.full_name}'
    )