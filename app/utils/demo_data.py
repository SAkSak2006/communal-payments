"""Script to populate database with demo data for testing."""
import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal

from app.database import async_session
from app.models import (
    Resident, Address, Meter, MeterReading, ReadingSource,
    PaymentPeriod, Payment, User, UserRole,
)
from app.services.auth_service import get_password_hash
from app.services.billing_service import calculate_charges_for_period


async def create_demo_data():
    async with async_session() as session:
        # === OPERATOR USER ===
        from sqlalchemy import select
        from app.models import UtilityService

        res = await session.execute(select(User).where(User.username == "operator"))
        if not res.scalar_one_or_none():
            operator = User(
                username="operator",
                email="operator@example.com",
                hashed_password=get_password_hash("operator123"),
                full_name="Петрова Анна Сергеевна",
                role=UserRole.OPERATOR,
            )
            session.add(operator)

        # === SERVICES (get existing) ===
        res = await session.execute(select(UtilityService))
        services = {s.code: s for s in res.scalars().all()}

        # === RESIDENTS ===
        residents_data = [
            {"full_name": "Иванов Иван Иванович", "phone": "+79001234501", "account": "2001-0001"},
            {"full_name": "Петрова Мария Сергеевна", "phone": "+79001234502", "account": "2001-0002"},
            {"full_name": "Сидоров Алексей Петрович", "phone": "+79001234503", "account": "2001-0003"},
            {"full_name": "Козлова Елена Викторовна", "phone": "+79001234504", "account": "2001-0004"},
            {"full_name": "Новиков Дмитрий Андреевич", "phone": "+79001234505", "account": "2001-0005"},
            {"full_name": "Морозова Ольга Николаевна", "phone": "+79001234506", "account": "2001-0006"},
            {"full_name": "Волков Сергей Александрович", "phone": "+79001234507", "account": "2001-0007"},
            {"full_name": "Лебедева Татьяна Дмитриевна", "phone": "+79001234508", "account": "2001-0008"},
            {"full_name": "Кузнецов Андрей Михайлович", "phone": "+79001234509", "account": "2001-0009"},
            {"full_name": "Соколова Наталья Игоревна", "phone": "+79001234510", "account": "2001-0010"},
        ]

        created_residents = []
        for rd in residents_data:
            res = await session.execute(
                select(Resident).where(Resident.personal_account == rd["account"])
            )
            if res.scalar_one_or_none():
                continue
            r = Resident(
                full_name=rd["full_name"],
                phone=rd["phone"],
                personal_account=rd["account"],
                is_verified=True,
            )
            session.add(r)
            created_residents.append(r)

        await session.flush()

        if not created_residents:
            print("Demo data already exists.")
            return

        # === ADDRESSES ===
        addresses_data = [
            {"city": "Москва", "street": "Ленина", "building": "10", "apartment": "1", "area": "45.2"},
            {"city": "Москва", "street": "Ленина", "building": "10", "apartment": "2", "area": "62.8"},
            {"city": "Москва", "street": "Ленина", "building": "10", "apartment": "3", "area": "38.5"},
            {"city": "Москва", "street": "Ленина", "building": "10", "apartment": "4", "area": "54.0"},
            {"city": "Москва", "street": "Ленина", "building": "10", "apartment": "5", "area": "71.3"},
            {"city": "Москва", "street": "Ленина", "building": "12", "apartment": "1", "area": "48.6"},
            {"city": "Москва", "street": "Ленина", "building": "12", "apartment": "2", "area": "55.0"},
            {"city": "Москва", "street": "Ленина", "building": "12", "apartment": "3", "area": "42.1"},
            {"city": "Москва", "street": "Пушкина", "building": "5", "apartment": "10", "area": "67.4"},
            {"city": "Москва", "street": "Пушкина", "building": "5", "apartment": "11", "area": "50.9"},
        ]

        created_addresses = []
        for i, ad in enumerate(addresses_data):
            addr = Address(
                city=ad["city"],
                street=ad["street"],
                building=ad["building"],
                apartment=ad["apartment"],
                area_sqm=Decimal(ad["area"]),
                resident_id=created_residents[i].id,
            )
            session.add(addr)
            created_addresses.append(addr)

        await session.flush()

        # === METERS (3 per address: cold water, hot water, electricity) ===
        meter_counter = 1
        created_meters = {}  # address_idx -> list of meters
        for i, addr in enumerate(created_addresses):
            meters = []
            for code in ["cold_water", "hot_water", "electricity"]:
                if code not in services:
                    continue
                svc = services[code]
                prefix = {"cold_water": "CW", "hot_water": "HW", "electricity": "EL"}[code]
                m = Meter(
                    address_id=addr.id,
                    service_id=svc.id,
                    serial_number=f"{prefix}-{meter_counter:04d}",
                    installation_date=date(2023, 1, 15),
                    verification_date=date(2027, 1, 15),
                )
                session.add(m)
                meters.append((m, code))
                meter_counter += 1
            created_meters[i] = meters

        await session.flush()

        # === PAYMENT PERIODS (Jan–Mar 2025) ===
        periods = {}
        for month in [1, 2, 3]:
            res = await session.execute(
                select(PaymentPeriod).where(
                    PaymentPeriod.year == 2025, PaymentPeriod.month == month
                )
            )
            p = res.scalar_one_or_none()
            if not p:
                p = PaymentPeriod(year=2025, month=month, is_closed=month < 3)
                session.add(p)
                await session.flush()
            periods[month] = p

        # === METER READINGS ===
        # Base values for each resident (simulate different consumption)
        base_readings = {
            "cold_water": [100, 85, 120, 95, 110, 90, 105, 130, 115, 98],
            "hot_water": [60, 50, 70, 55, 65, 52, 58, 75, 68, 54],
            "electricity": [1000, 850, 1200, 950, 1100, 900, 1050, 1300, 1150, 980],
        }

        monthly_consumption = {
            "cold_water": [8, 9, 7],
            "hot_water": [5, 6, 4],
            "electricity": [180, 200, 170],
        }

        for addr_idx, meters in created_meters.items():
            for meter, code in meters:
                if code not in base_readings:
                    continue
                base = Decimal(str(base_readings[code][addr_idx]))
                for month in [1, 2, 3]:
                    cons = Decimal(str(monthly_consumption[code][month - 1]))
                    prev = base + cons * (month - 1)
                    curr = prev + cons

                    reading = MeterReading(
                        meter_id=meter.id,
                        value=curr,
                        previous_value=prev,
                        consumption=cons,
                        period_year=2025,
                        period_month=month,
                        source=ReadingSource.ADMIN if month < 3 else ReadingSource.TELEGRAM,
                        submitted_by_resident=created_residents[addr_idx].id if month == 3 else None,
                        is_validated=month < 3,  # March readings unvalidated
                    )
                    session.add(reading)

        await session.commit()

        # === CALCULATE CHARGES for Jan and Feb ===
        for month in [1, 2]:
            stats = await calculate_charges_for_period(session, periods[month].id)
            print(f"  Charges {month}/2025: created={stats['created']}, skipped={stats['skipped']}")

        # === PAYMENTS (partial — some residents paid, some didn't) ===
        # Residents 0-6 paid for January, 0-4 paid for February
        from sqlalchemy import func
        from app.models import Charge

        for month, paying_count in [(1, 7), (2, 5)]:
            for idx in range(paying_count):
                # Get total charges for this resident in this period
                res = await session.execute(
                    select(func.coalesce(func.sum(Charge.amount), 0))
                    .join(Address, Address.id == Charge.address_id)
                    .where(
                        Address.resident_id == created_residents[idx].id,
                        Charge.period_id == periods[month].id,
                    )
                )
                total = res.scalar_one()
                if total <= 0:
                    continue

                payment = Payment(
                    resident_id=created_residents[idx].id,
                    amount=total,
                    payment_date=datetime(2025, month, 25, tzinfo=timezone.utc),
                    period_id=periods[month].id,
                    payment_method="card" if idx % 2 == 0 else "cash",
                    receipt_number=f"RCP-2025{month:02d}-{idx+1:03d}",
                )
                session.add(payment)

        await session.commit()
        print("Demo data created successfully!")
        print(f"  10 residents, 10 addresses, 30 meters")
        print(f"  Readings for Jan-Mar 2025 (March unvalidated)")
        print(f"  Charges calculated for Jan-Feb")
        print(f"  Payments: 7 for Jan, 5 for Feb (3-5 debtors)")
        print(f"  Operator user: operator / operator123")


if __name__ == "__main__":
    asyncio.run(create_demo_data())
