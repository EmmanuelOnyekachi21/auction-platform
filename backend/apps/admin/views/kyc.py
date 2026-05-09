from datetime import datetime

from sqladmin import ModelView, action
from sqladmin.filters import BooleanFilter, StaticValuesFilter

from apps.users.enums import KYCDocuments, KYCStatus, KYCTier
from apps.users.kyc_models import KYCDocumentModel, KYCProfile


class KYCProfileAdmin(ModelView, model=KYCProfile):
    name = "KYC Profile"
    name_plural = "KYC Profiles"
    icon = "fa-solid fa-shield-halved"

    column_list = [
        KYCProfile.user_id,
        KYCProfile.current_tier,
        KYCProfile.email_verified,
        KYCProfile.phone_verified,
        KYCProfile.bvn_verified,
        KYCProfile.tier_1_completed_at,
        KYCProfile.tier_2_completed_at,
        KYCProfile.tier_3_completed_at,
        KYCProfile.last_verification_attempt,
        KYCProfile.rejection_reason,
        KYCProfile.bvn_attempt_count,
    ]

    column_formatters = {
        KYCProfile.bvn_verified: lambda m, a: (
            "✓ BVN Verified" if m.bvn_verified else "✗ BVN Not Verified"
        ),
    }

    column_filters = [
        StaticValuesFilter(
            KYCProfile.current_tier,
            title="KYC Tier",
            values=[(t.value, t.value) for t in KYCTier],
        ),
        BooleanFilter(KYCProfile.email_verified, title="Email Verified"),
        BooleanFilter(KYCProfile.bvn_verified, title="BVN Verified"),
    ]

    form_columns = [
        KYCProfile.current_tier,
        KYCProfile.email_verified,
        KYCProfile.phone_verified,
        KYCProfile.bvn_verified,
        KYCProfile.rejection_reason,
    ]

    @action(
        name="verify_bvn",
        label="Verify BVN",
        confirmation_message="Are you sure you want to verify BVN for selected users?",
    )
    async def verify_bvn(self, request, pks):
        from datetime import timezone

        from sqlalchemy.ext.asyncio import async_sessionmaker

        from apps.users.enums import KYCTier
        from config.database import engine

        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            for pk in pks:
                item = await session.get(KYCProfile, pk)
                if item:
                    item.bvn_verified = True
                    item.current_tier = KYCTier.TIER_2
                    item.tier_2_completed_at = datetime.now(timezone.utc)
            await session.commit()

    @action(
        name="reject_kyc",
        label="Reject KYC",
        confirmation_message="Are you sure you want to reject KYC for selected users?",
    )
    async def reject_kyc(self, request, pks):

        from sqlalchemy.ext.asyncio import async_sessionmaker

        from apps.users.enums import KYCTier
        from config.database import engine

        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            for pk in pks:
                item = await session.get(KYCProfile, pk)
                if item:
                    item.current_tier = KYCTier.TIER_1
                    item.bvn_verified = False
                    item.rejection_reason = "Rejected by admin"
            await session.commit()


class KYCDocumentAdmin(ModelView, model=KYCDocumentModel):
    name = "KYC Document"
    name_plural = "KYC Documents"
    icon = "fa-solid fa-file-shield"

    column_list = [
        KYCDocumentModel.user_id,
        KYCDocumentModel.document_type,
        KYCDocumentModel.document_url,
        KYCDocumentModel.verified_by_id,
        KYCDocumentModel.rejection_reason,
        KYCDocumentModel.status,
        KYCDocumentModel.expires_at,
        KYCDocumentModel.verified_at,
    ]

    column_labels = {
        "user_id": "User",
        "document_type": "Document Type",
        "status": "Status",
        "expires_at": "Expires At",
        "verified_at": "Verified At",
        "updated_at": "Updated At",
    }

    column_formatters = {
        "updated_at": lambda m, a: m.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        "verified_at": lambda m, a: (
            m.verified_at.strftime("%Y-%m-%d %H:%M:%S") if m.verified_at else None
        ),
        "expires_at": lambda m, a: (
            m.expires_at.strftime("%Y-%m-%d %H:%M:%S") if m.expires_at else None
        ),
        KYCDocumentModel.document_url: lambda m, a: (
            "View Document" if m.document_url else "No file"
        ),
    }

    column_filters = [
        StaticValuesFilter(
            KYCDocumentModel.status,
            title="Status",
            values=[(s.value, s.value) for s in KYCStatus],
        ),
        StaticValuesFilter(
            KYCDocumentModel.document_type,
            title="Document Type",
            values=[(d.value, d.value) for d in KYCDocuments],
        ),
    ]

    column_searchable_list = [
        KYCDocumentModel.user_id,
    ]

    form_columns = [
        KYCDocumentModel.status,
        KYCDocumentModel.rejection_reason,
        KYCDocumentModel.verified_by_id,
        KYCDocumentModel.expires_at,
        KYCDocumentModel.verified_at,
    ]

    @action(
        name="verify",
        label="Verify",
        confirmation_message="Are you sure you want to verify selected documents?",
    )
    async def verify_documents(self, request, pks):
        from datetime import timezone

        from sqlalchemy.ext.asyncio import async_sessionmaker

        from apps.users.enums import KYCStatus
        from config.database import engine

        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            for pk in pks:
                item = await session.get(KYCDocumentModel, pk)
                if item:
                    item.status = KYCStatus.VERIFIED
                    item.verified_at = datetime.now(timezone.utc)
            await session.commit()

    @action(
        name="reject",
        label="Reject",
        confirmation_message="Are you sure you want to reject selected documents?",
    )
    async def reject_documents(self, request, pks):
        from datetime import timezone

        from sqlalchemy.ext.asyncio import async_sessionmaker

        from apps.users.enums import KYCStatus
        from config.database import engine

        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            for pk in pks:
                item = await session.get(KYCDocumentModel, pk)
                if item:
                    item.status = KYCStatus.REJECTED
                    item.verified_at = datetime.now(timezone.utc)
            await session.commit()
