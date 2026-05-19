from decimal import Decimal

import pytest

from app.models import Resident, Address
from app.repositories.resident_repo import ResidentRepository


@pytest.mark.asyncio
async def test_get_resident_by_account(session, seed_data):
    """Should find resident by personal account."""
    repo = ResidentRepository(session)
    resident = await repo.get_by_personal_account("1001-0001")

    assert resident is not None
    assert resident.full_name == "Иванов Иван Иванович"


@pytest.mark.asyncio
async def test_get_resident_by_account_not_found(session, seed_data):
    """Non-existent account should return None."""
    repo = ResidentRepository(session)
    resident = await repo.get_by_personal_account("9999-9999")

    assert resident is None


@pytest.mark.asyncio
async def test_get_resident_by_telegram_id(session, seed_data):
    """Should find resident by telegram_id."""
    repo = ResidentRepository(session)
    resident = await repo.get_by_telegram_id(123456789)

    assert resident is not None
    assert resident.personal_account == "1001-0001"


@pytest.mark.asyncio
async def test_get_resident_with_addresses(session, seed_data):
    """Should load resident with addresses eagerly."""
    repo = ResidentRepository(session)
    resident = await repo.get_with_addresses(seed_data["resident"].id)

    assert resident is not None
    assert len(resident.addresses) == 1
    assert resident.addresses[0].city == "Москва"
    assert resident.addresses[0].apartment == "42"


@pytest.mark.asyncio
async def test_search_residents_by_name(session, seed_data):
    """Should find residents by partial name match."""
    repo = ResidentRepository(session)
    results = await repo.search("Иванов")

    assert len(results) >= 1
    assert any(r.full_name == "Иванов Иван Иванович" for r in results)


@pytest.mark.asyncio
async def test_search_residents_by_account(session, seed_data):
    """Should find residents by account number."""
    repo = ResidentRepository(session)
    results = await repo.search("1001")

    assert len(results) >= 1


@pytest.mark.asyncio
async def test_search_no_results(session, seed_data):
    """Search with no matches should return empty list."""
    repo = ResidentRepository(session)
    results = await repo.search("НесуществующийЖитель12345")

    assert len(results) == 0


@pytest.mark.asyncio
async def test_create_resident(session, seed_data):
    """Should create new resident."""
    repo = ResidentRepository(session)
    resident = await repo.create(
        full_name="Петрова Мария Сергеевна",
        phone="+79009876543",
        personal_account="1001-0002",
    )

    assert resident.id is not None
    assert resident.full_name == "Петрова Мария Сергеевна"
    assert resident.is_verified is False

    # Verify in DB
    found = await repo.get_by_personal_account("1001-0002")
    assert found is not None


@pytest.mark.asyncio
async def test_update_resident(session, seed_data):
    """Should update resident fields."""
    repo = ResidentRepository(session)
    resident = seed_data["resident"]

    updated = await repo.update(resident, phone="+79001111111")
    assert updated.phone == "+79001111111"


@pytest.mark.asyncio
async def test_resident_count(session, seed_data):
    """Count should return correct number."""
    repo = ResidentRepository(session)
    count = await repo.count()

    assert count >= 1
