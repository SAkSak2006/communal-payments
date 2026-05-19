import pytest

from app.models import Resident
from app.repositories.resident_repo import ResidentRepository


@pytest.mark.asyncio
async def test_find_resident_by_account_for_registration(session, seed_data):
    """Bot registration: find resident by personal account."""
    repo = ResidentRepository(session)
    resident = await repo.get_by_personal_account("1001-0001")

    assert resident is not None
    assert resident.full_name == "Иванов Иван Иванович"


@pytest.mark.asyncio
async def test_account_not_found(session, seed_data):
    """Bot registration: non-existent account returns None."""
    repo = ResidentRepository(session)
    resident = await repo.get_by_personal_account("0000-0000")

    assert resident is None


@pytest.mark.asyncio
async def test_link_telegram_id(session, seed_data):
    """Bot registration: link telegram_id to resident."""
    # Create unlinked resident
    repo = ResidentRepository(session)
    new_resident = await repo.create(
        full_name="Сидоров Пётр",
        phone="+79005555555",
        personal_account="1001-0003",
    )
    assert new_resident.telegram_id is None

    # Link telegram
    new_resident.telegram_id = 987654321
    new_resident.is_verified = True
    await session.commit()

    # Verify
    found = await repo.get_by_telegram_id(987654321)
    assert found is not None
    assert found.personal_account == "1001-0003"
    assert found.is_verified is True


@pytest.mark.asyncio
async def test_already_linked_account(session, seed_data):
    """Bot registration: already linked account should be detected."""
    repo = ResidentRepository(session)
    resident = await repo.get_by_personal_account("1001-0001")

    # Already has telegram_id from seed_data
    assert resident.telegram_id == 123456789

    # Should detect it's already linked
    is_linked = resident.telegram_id is not None
    assert is_linked is True


@pytest.mark.asyncio
async def test_find_by_telegram_unregistered(session, seed_data):
    """Bot: unregistered telegram user should not be found."""
    repo = ResidentRepository(session)
    resident = await repo.get_by_telegram_id(999999999)

    assert resident is None
