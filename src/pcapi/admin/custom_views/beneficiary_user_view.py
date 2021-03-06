from flask.helpers import flash
from flask_login import current_user
from sqlalchemy.orm import query
from sqlalchemy.sql.functions import func
from wtforms import Form
from wtforms import SelectField
from wtforms import validators
from wtforms.validators import DataRequired

from pcapi import settings
from pcapi.admin.base_configuration import BaseAdminView
from pcapi.core.users.models import User
from pcapi.domain.user_emails import send_activation_email
from pcapi.models import UserOfferer

from .suspension_mixin import SuspensionMixin


class BeneficiaryUserView(SuspensionMixin, BaseAdminView):
    can_edit = True

    @property
    def can_create(self) -> bool:
        if settings.IS_PROD:
            return current_user.email in settings.SUPER_ADMIN_EMAIL_ADDRESSES

        return True

    column_list = [
        "id",
        "isBeneficiary",
        "email",
        "firstName",
        "lastName",
        "publicName",
        "dateOfBirth",
        "departementCode",
        "phoneNumber",
        "postalCode",
        "resetPasswordToken",
        "validationToken",
        "deposit_version",
        "actions",
    ]
    column_labels = dict(
        email="Email",
        isBeneficiary="Est bénéficiaire",
        firstName="Prénom",
        lastName="Nom",
        publicName="Nom d'utilisateur",
        dateOfBirth="Date de naissance",
        departementCode="Département",
        phoneNumber="Numéro de téléphone",
        postalCode="Code postal",
        resetPasswordToken="Jeton d'activation et réinitialisation de mot de passe",
        validationToken="Jeton de validation d'adresse email",
        deposit_version="Version du dépot",
    )
    column_searchable_list = ["id", "publicName", "email", "firstName", "lastName"]
    column_filters = ["postalCode", "isBeneficiary"]
    form_columns = [
        "email",
        "firstName",
        "lastName",
        "dateOfBirth",
        "departementCode",
        "postalCode",
        "phoneNumber",
        "isBeneficiary",
    ]

    form_args = dict(
        firstName=dict(validators=[DataRequired()]),
        lastName=dict(validators=[DataRequired()]),
        dateOfBirth=dict(validators=[DataRequired()]),
    )

    def get_create_form(self):
        form_class = super().scaffold_form()

        if not settings.IS_PROD:
            form_class.depositVersion = SelectField(
                "Version du déposit",
                [DataRequired()],
                choices=[
                    (1, "500€ - Deux seuils de dépense (300€ en physique et 200€ en numérique)"),
                    (2, "300€ - Un seuil de dépense (100€ en offres numériques)"),
                ],
            )

        return form_class

    def on_model_change(self, form: Form, model: User, is_created: bool) -> None:
        model.publicName = f"{model.firstName} {model.lastName}"
        # If a user is an admin, he shouldn't be able to be beneficiary
        if form.isBeneficiary.data and model.isAdmin:
            raise validators.ValidationError("Un admin ne peut pas être bénéficiaire")

        if is_created:
            # This is to prevent a circulary import dependency
            from pcapi.core.users.api import fulfill_user_data

            deposit_version = int(form.depositVersion.data) if not settings.IS_PROD else None
            fulfill_user_data(model, "pass-culture-admin", deposit_version)

        super().on_model_change(form, model, is_created)

    def after_model_change(self, form: Form, model: User, is_created: bool) -> None:
        if is_created and not send_activation_email(model):
            flash("L'envoi d'email a échoué", "error")
        super().after_model_change(form, model, is_created)

    def get_query(self) -> query:
        return User.query.outerjoin(UserOfferer).filter(UserOfferer.userId.is_(None))

    def get_count_query(self) -> query:
        return (
            self.session.query(func.count("*"))
            .select_from(self.model)
            .outerjoin(UserOfferer)
            .filter(UserOfferer.userId.is_(None))
        )
