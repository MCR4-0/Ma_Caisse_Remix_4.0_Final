from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Regexp, ValidationError, Length

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message="L'email est requis."),
        Email(message="Veuillez entrer une adresse email valide.")
    ])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(message="Le mot de passe est requis."),
        Regexp(
            r'^[a-zA-Z0-9_]+$',
            message="Le mot de passe ne doit contenir que des lettres, des chiffres ou des underscores (pas de caractères spéciaux)."
        ),
        Length(
            min=5,
            max=10,
            message="Le mot de passe doit contenir entre 5 et 10 caractères."
        )
    ])
    submit = SubmitField('Se connecter')

    def validate_email(self, field):
        valid_domains = [
            'gmail.com', 'yahoo.com', 'hotmail.com', 'mcr4.com',
            'outlook.com', 'aol.com', 'icloud.com', 'protonmail.com'
        ]
        email = field.data.lower()
        domain = email.split('@')[-1] if '@' in email else ''
        if domain not in valid_domains:
            raise ValidationError(
                f"L'email doit utiliser un domaine valide parmi : {', '.join(valid_domains)}."
            )