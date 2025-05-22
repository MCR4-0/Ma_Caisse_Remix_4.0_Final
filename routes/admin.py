from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from forms.supervisor_form import SupervisorForm
from models.user import User, Role
from models.database import db_session
from utils.decorators import admin_required
from passlib.hash import pbkdf2_sha256
from sqlalchemy import func
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='app.log')
logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """
    Affiche le tableau de bord administrateur avec les statistiques des superviseurs et dealers.
    """
    # Compter les superviseurs
    supervisor_count = User.query.filter_by(role=Role.SUPERVISOR).count()
    
    # Compter tous les dealers
    dealer_count = User.query.filter_by(role=Role.DEALER).count()
    
    # Liste des superviseurs
    supervisors = User.query.filter_by(role=Role.SUPERVISOR).order_by(User.created_at.desc()).all()
    
    # Répartition des superviseurs par commune
    supervisor_locations = db_session.query(User.commune, func.count(User.id)).filter_by(
        role=Role.SUPERVISOR
    ).group_by(User.commune).all() or [('Aucune donnée', 0)]
    
    # Répartition des dealers par commune
    dealer_locations = db_session.query(User.commune, func.count(User.id)).filter_by(
        role=Role.DEALER
    ).group_by(User.commune).all() or [('Aucune donnée', 0)]

    return render_template(
        'admin/dashboard.html',
        title='Tableau de bord administrateur',
        supervisor_count=supervisor_count,
        dealer_count=dealer_count,
        supervisors=supervisors,
        supervisor_locations=supervisor_locations,
        dealer_locations=dealer_locations
    )

@admin_bp.route('/supervisor/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_supervisor():
    """
    Permet d'ajouter un nouveau superviseur avec un formulaire.
    """
    form = SupervisorForm()
    if request.method == 'POST':
        logger.debug(f"Form data: {form.data}")
        if form.validate_on_submit():
            logger.info("Formulaire validé avec succès")
            # Vérifier l'unicité des champs
            if User.query.filter_by(email=form.email.data).first():
                flash("Cet email est déjà utilisé.", 'danger')
                return render_template('admin/add_supervisor.html', form=form, title='Ajouter un superviseur')
            if User.query.filter_by(username=form.username.data).first():
                flash("Ce nom d'utilisateur est déjà utilisé.", 'danger')
                return render_template('admin/add_supervisor.html', form=form, title='Ajouter un superviseur')
            if User.query.filter_by(phone_number=form.phone_number.data).first():
                flash("Ce numéro de téléphone est déjà utilisé.", 'danger')
                return render_template('admin/add_supervisor.html', form=form, title='Ajouter un superviseur')
            
            # Générer un code unique
            while True:
                code = f"SUP{uuid.uuid4().hex[:6].upper()}"
                if not User.query.filter_by(code=code).first():
                    break
            
            try:
                new_supervisor = User(
                    first_name=form.first_name.data,
                    last_name=form.last_name.data,
                    email=form.email.data,
                    username=form.username.data,
                    password=pbkdf2_sha256.hash(form.password.data),
                    gender=form.gender.data,
                    marital_status=form.marital_status.data,
                    phone_number=form.phone_number.data,
                    commune=form.commune.data,
                    city=form.city.data,
                    code=code,
                    role=Role.SUPERVISOR,
                    created_by_id=current_user.id,
                    is_active=True
                )
                db_session.add(new_supervisor)
                db_session.commit()
                flash(f"Superviseur {new_supervisor.full_name} créé avec succès.", 'success')
                return redirect(url_for('admin.dashboard'))
            except Exception as e:
                db_session.rollback()
                logger.error(f"Erreur lors de l'ajout du superviseur : {str(e)}")
                flash(f"Erreur lors de l'ajout du superviseur : {str(e)}", 'danger')
        else:
            logger.warning(f"Échec de la validation du formulaire : {form.errors}")
            flash("Veuillez corriger les erreurs dans le formulaire.", 'danger')
    return render_template('admin/add_supervisor.html', form=form, title='Ajouter un superviseur')

@admin_bp.route('/supervisor/<int:supervisor_id>')
@login_required
@admin_required
def view_supervisor(supervisor_id):
    """
    Affiche les détails d'un superviseur et ses dealers associés.
    """
    supervisor = User.query.filter_by(id=supervisor_id, role=Role.SUPERVISOR).first()
    if not supervisor:
        logger.warning(f"Superviseur avec ID {supervisor_id} non trouvé.")
        flash("Superviseur non trouvé.", 'danger')
        abort(404)
    dealers = User.query.filter_by(created_by_id=supervisor_id, role=Role.DEALER).all()
    return render_template(
        'admin/view_supervisor.html',
        supervisor=supervisor,
        dealers=dealers,
        title=f'Superviseur : {supervisor.full_name}'
    )

@admin_bp.route('/supervisor/<int:supervisor_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_supervisor(supervisor_id):
    """
    Permet de modifier les informations d'un superviseur.
    """
    supervisor = User.query.filter_by(id=supervisor_id, role=Role.SUPERVISOR).first()
    if not supervisor:
        logger.warning(f"Superviseur avec ID {supervisor_id} non trouvé.")
        flash("Superviseur non trouvé.", 'danger')
        abort(404)
    
    form = SupervisorForm(obj=supervisor)
    
    if request.method == 'POST':
        logger.debug(f"Form data (edit): {form.data}")
        if form.validate_on_submit():
            logger.info("Formulaire d'édition validé avec succès")
            # Vérifier l'unicité des champs, sauf si la valeur est inchangée
            if form.email.data != supervisor.email and User.query.filter(User.email == form.email.data).first():
                flash("Cet email est déjà utilisé par un autre utilisateur.", 'danger')
                return render_template('admin/edit_supervisor.html', form=form, supervisor=supervisor, title=f'Modifier le superviseur : {supervisor.full_name}')
            if form.username.data != supervisor.username and User.query.filter(User.username == form.username.data).first():
                flash("Ce nom d'utilisateur est déjà utilisé par un autre utilisateur.", 'danger')
                return render_template('admin/edit_supervisor.html', form=form, supervisor=supervisor, title=f'Modifier le superviseur : {supervisor.full_name}')
            if form.phone_number.data != supervisor.phone_number and User.query.filter(User.phone_number == form.phone_number.data).first():
                flash("Ce numéro de téléphone est déjà utilisé par un autre utilisateur.", 'danger')
                return render_template('admin/edit_supervisor.html', form=form, supervisor=supervisor, title=f'Modifier le superviseur : {supervisor.full_name}')
            
            try:
                # Mettre à jour les champs
                supervisor.first_name = form.first_name.data
                supervisor.last_name = form.last_name.data
                supervisor.email = form.email.data
                supervisor.username = form.username.data
                supervisor.gender = form.gender.data
                supervisor.marital_status = form.marital_status.data
                supervisor.phone_number = form.phone_number.data
                supervisor.commune = form.commune.data
                supervisor.city = form.city.data
                
                db_session.commit()
                flash(f"Superviseur {supervisor.full_name} mis à jour avec succès.", 'success')
                return redirect(url_for('admin.view_supervisor', supervisor_id=supervisor_id))
            except Exception as e:
                db_session.rollback()
                logger.error(f"Erreur lors de la mise à jour du superviseur : {str(e)}")
                flash(f"Erreur lors de la mise à jour du superviseur : {str(e)}", 'danger')
        else:
            logger.warning(f"Échec de la validation du formulaire d'édition : {form.errors}")
            flash("Veuillez corriger les erreurs dans le formulaire.", 'danger')
    
    return render_template(
        'admin/edit_supervisor.html',
        form=form,
        supervisor=supervisor,
        title=f'Modifier le superviseur : {supervisor.full_name}'
    )

@admin_bp.route('/supervisor/<int:supervisor_id>/disable', methods=['POST'])
@login_required
@admin_required
def disable_supervisor(supervisor_id):
    """
    Désactive le compte d'un superviseur (is_active=False).
    """
    supervisor = User.query.filter_by(id=supervisor_id, role=Role.SUPERVISOR).first()
    if not supervisor:
        logger.warning(f"Superviseur avec ID {supervisor_id} non trouvé.")
        flash("Superviseur non trouvé.", 'danger')
        abort(404)
    if supervisor.id == current_user.id:
        flash("Vous ne pouvez pas désactiver votre propre compte.", 'danger')
        return redirect(url_for('admin.view_supervisor', supervisor_id=supervisor_id))
    try:
        supervisor.is_active = False
        db_session.commit()
        flash(f"Le compte de {supervisor.full_name} a été désactivé avec succès.", 'success')
    except Exception as e:
        db_session.rollback()
        logger.error(f"Erreur lors de la désactivation du superviseur : {str(e)}")
        flash(f"Erreur lors de la désactivation du superviseur : {str(e)}", 'danger')
    return redirect(url_for('admin.view_supervisor', supervisor_id=supervisor_id))

@admin_bp.route('/supervisor/<int:supervisor_id>/enable', methods=['POST'])
@login_required
@admin_required
def enable_supervisor(supervisor_id):
    """
    Réactive le compte d'un superviseur (is_active=True).
    """
    supervisor = User.query.filter_by(id=supervisor_id, role=Role.SUPERVISOR).first()
    if not supervisor:
        logger.warning(f"Superviseur avec ID {supervisor_id} non trouvé.")
        flash("Superviseur non trouvé.", 'danger')
        abort(404)
    try:
        supervisor.is_active = True
        db_session.commit()
        flash(f"Le compte de {supervisor.full_name} a été réactivé avec succès.", 'success')
    except Exception as e:
        db_session.rollback()
        logger.error(f"Erreur lors de la réactivation du superviseur : {str(e)}")
        flash(f"Erreur lors de la réactivation du superviseur : {str(e)}", 'danger')
    return redirect(url_for('admin.view_supervisor', supervisor_id=supervisor_id))