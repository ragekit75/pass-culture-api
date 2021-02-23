from pcapi.core.object_storage.backends.ovh import OVHBackend
from pcapi.core.offers.models import Mediation
from pcapi.models import db
from pcapi.utils.human_ids import dehumanize
from pcapi.utils.human_ids import humanize


def delete_obsolete_mediations(dry_run: bool = True) -> None:
    """
    This function will delete:
    - Mediations that are NOT active (the user replaced it with another one)
    - Mediations that have a thumbCount of 0 (unexpected)
    """
    if dry_run:
        print("This a dry run; if you are sure about the changes, call this function with dry_run=False")

    db.session.commit()

    inactive_to_delete = Mediation.query.filter(Mediation.isActive.is_(False)).delete()
    no_thumb_to_delete = Mediation.query.filter(Mediation.thumbCount == 0).delete()
    print(f"{inactive_to_delete} inactive Mediations are about to be deleted")
    print(f"{no_thumb_to_delete} Mediations without thumb are about to be deleted")

    if dry_run:
        db.session.rollback()
    else:
        db.session.commit()

    inactive_count = Mediation.query.filter(Mediation.isActive.is_(False)).count()
    no_thumb_count = Mediation.query.filter(Mediation.thumbCount == 0).count()
    print(f"There are now {inactive_count} inactive Mediations")
    print(f"There are now {no_thumb_count} Mediations without thumb")


def delete_thumbnails_in_object_storage(dry_run: bool = True) -> None:
    """
    This function will collect all assets stored for a Mediation and the former model name MediationSQLEntity
    It will then compare the set to existing Mediations, and delete orphan assets ie for which no Mediation has the same ID)
    It will also delete all assets tied to MediationSQLEntities
    It will also delete multiple thumbs of the same Mediation (ind
    """
    if dry_run:
        print("This a dry run; if you are sure about the changes, call this function with dry_run=False")

    db.session.commit()

    old_mediationsqlentities_asset_names = set()
    current_mediation_asset_ids = set()
    extra_thumb_asset_names = set()
    # get_container() returns a tuple of (dict of headers, list(dict of asset properties))
    mediation_assets = OVHBackend().get_container(
        marker="thumbs/mediations",
        end_marker="thumbs/mf",
    )[1]
    for mediation_asset in mediation_assets:
        asset_name = mediation_asset["name"]
        if asset_name.startswith("thumbs/mediationsqlentities/"):
            old_mediationsqlentities_asset_names.add(asset_name.lstrip("thumbs/mediationsqlentities/"))
        if asset_name.startswith("thumbs/mediations/"):
            asset_name = asset_name.lstrip("thumbs/mediations/")
            # Mediations should not have several thumbs
            if "_" in asset_name:
                extra_thumb_asset_names.add(asset_name)
            else:
                mediation_id = dehumanize(asset_name)
                current_mediation_asset_ids.add(mediation_id)

    # create a set of Mediation IDs out of the list of tuples returned by the query
    current_mediation_ids = set((mediation_id for mediation_id, in Mediation.query.with_entities(Mediation.id).all()))

    # Mediations without assets
    orphan_mediation_ids = current_mediation_ids - current_mediation_asset_ids
    deleted_mediations_without_assets = Mediation.query.filter(Mediation.id in orphan_mediation_ids).delete()
    print(f"{deleted_mediations_without_assets} Mediations without assets are about to be deleted")
    if dry_run:
        db.session.rollback()
    else:
        db.session.commit()

    # Assets of extra thumbs
    print(f"{len(extra_thumb_asset_names)} assets that are not unique to a Mediation are about to be deleted")
    if dry_run:
        pass
    else:
        for asset_name in extra_thumb_asset_names:
            OVHBackend().delete_public_object(bucket="", object_id=asset_name)

    # Assets without mediations
    orphan_mediation_asset_ids = current_mediation_asset_ids - current_mediation_ids
    print(f"{len(orphan_mediation_asset_ids)} assets that are not related to a Mediation are about to be deleted")
    if dry_run:
        pass
    else:
        for numerical_id in orphan_mediation_asset_ids:
            human_id = humanize(numerical_id)
            OVHBackend().delete_public_object(bucket="", object_id=human_id)

    # MediationSQLEntities assets
    print(
        f"{len(old_mediationsqlentities_asset_names)} assets that are related to a former MediationSQLEntity are about to be deleted"
    )
    if dry_run:
        pass
    else:
        for asset_name in old_mediationsqlentities_asset_names:
            OVHBackend().delete_public_object(bucket="", object_id=asset_name)
