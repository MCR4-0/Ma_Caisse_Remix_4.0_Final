from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, Email, ValidationError, Regexp
from models.user import User

class DealerForm(FlaskForm):
    first_name = StringField('Prénom', validators=[
        DataRequired(message="Le prénom est requis"),
        Length(min=2, max=50, message="Le prénom doit contenir entre 2 et 50 caractères")
    ])
    last_name = StringField('Nom', validators=[
        DataRequired(message="Le nom est requis"),
        Length(min=2, max=50, message="Le nom doit contenir entre 2 et 50 caractères")
    ])
    email = StringField('Email', validators=[
        DataRequired(message="L'email est requis"),
        Email(message="Veuillez entrer une adresse email valide"),
        Length(max=120, message="L'email ne peut pas dépasser 120 caractères")
    ])
    username = StringField('Nom d\'utilisateur', validators=[
        DataRequired(message="Le nom d'utilisateur est requis"),
        Length(min=4, max=50, message="Le nom d'utilisateur doit contenir entre 4 et 50 caractères"),
        Regexp(r'^[a-zA-Z0-9_]+$', message="Le nom d'utilisateur ne peut contenir que des lettres, chiffres et underscores")
    ])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(message="Le mot de passe est requis"),
        Length(min=6, max=50, message="Le mot de passe doit contenir entre 6 et 50 caractères")
    ])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[
        DataRequired(message="La confirmation du mot de passe est requise"),
        EqualTo('password', message="Les mots de passe doivent correspondre")
    ])
    gender = SelectField('Genre', choices=[('', 'Sélectionnez un genre'), ('M', 'Homme'), ('F', 'Femme')], validators=[
        DataRequired(message="Le genre est requis")
    ])
    marital_status = SelectField('État civil', choices=[
        ('', 'Sélectionnez un état civil'),
        ('SINGLE', 'Célibataire'),
        ('MARRIED', 'Marié(e)'),
        ('DIVORCED', 'Divorcé(e)'),
        ('WIDOWED', 'Veuf/Veuve')
    ], validators=[
        DataRequired(message="L'état civil est requis")
    ])
    phone_number = StringField('Numéro de téléphone', validators=[
        DataRequired(message="Le numéro de téléphone est requis"),
        Length(min=10, max=13, message="Le numéro de téléphone doit contenir entre 10 et 13 chiffres"),
        Regexp(r'^\+243\d{9}$', message="Veuillez entrer un numéro valide commençant par +243 suivi de 9 chiffres (ex. +243123456789)")
    ])
    commune = SelectField('Commune', choices=[
        ('', 'Sélectionnez une commune'),
        ('Bandalungwa', 'Bandalungwa'),
        ('Barumbu', 'Barumbu'),
        ('Bumbu', 'Bumbu'),
        ('Gombe', 'Gombe'),
        ('Kalamu', 'Kalamu'),
        ('Kasa-Vubu', 'Kasa-Vubu'),
        ('Kimbanseke', 'Kimbanseke'),
        ('Kinshasa', 'Kinshasa'),
        ('Kintambo', 'Kintambo'),
        ('Kisenso', 'Kisenso'),
        ('Lemba', 'Lemba'),
        ('Limete', 'Limete'),
        ('Lingwala', 'Lingwala'),
        ('Makala', 'Makala'),
        ('Maluku', 'Maluku'),
        ('Masina', 'Masina'),
        ('Matete', 'Matete'),
        ('Mont-Ngafula', 'Mont-Ngafula'),
        ('Ndjili', 'Ndjili'),
        ('Ngaba', 'Ngaba'),
        ('Ngaliema', 'Ngaliema'),
        ('Ngiri-Ngiri', 'Ngiri-Ngiri'),
        ('Nsele', 'Nsele'),
        ('Selembao', 'Selembao')
    ], validators=[
        DataRequired(message="La commune est requise")
    ])
    city = StringField('Ville', default='Kinshasa', validators=[
        DataRequired(message="La ville est requise"),
        Length(max=100, message="La ville ne peut pas dépasser 100 caractères")
    ])
    submit = SubmitField('Enregistrer le dealer')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Ce nom d\'utilisateur existe déjà. Veuillez en choisir un autre.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Cet email est déjà utilisé. Veuillez en choisir un autre.')

    def validate_phone_number(self, phone_number):
        user = User.query.filter_by(phone_number=phone_number.data).first()
        if user:
            raise ValidationError('Ce numéro de téléphone est déjà utilisé. Veuillez en choisir un autre.')