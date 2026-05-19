from decimal import Decimal
from typing import List, Dict

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Charge, Payment, Address, Resident, UtilityService, PaymentPeriod,
)


async def report_by_period(session: AsyncSession, period_id: int) -> Dict:
    """Summary report for a billing period."""
    # Total charges by service
    result = await session.execute(
        select(
            UtilityService.name,
            func.sum(Charge.consumption),
            func.sum(Charge.amount),
            func.count(Charge.id),
        )
        .join(UtilityService, UtilityService.id == Charge.service_id)
        .where(Charge.period_id == period_id)
        .group_by(UtilityService.name)
        .order_by(UtilityService.name)
    )
    by_service = []
    total_amount = Decimal("0")
    for svc_name, total_cons, total_amt, count in result.all():
        by_service.append({
            "service_name": svc_name,
            "total_consumption": total_cons,
            "total_amount": total_amt,
            "count": count,
        })
        total_amount += total_amt

    # Total payments for this period
    result2 = await session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.period_id == period_id
        )
    )
    total_paid = result2.scalar_one()

    return {
        "by_service": by_service,
        "total_charged": total_amount,
        "total_paid": total_paid,
        "debt": total_amount - total_paid,
    }


async def report_by_resident(session: AsyncSession, resident_id: int) -> Dict:
    """Detailed report for a single resident."""
    resident = await session.get(Resident, resident_id)
    if not resident:
        return {}

    # All charges
    result = await session.execute(
        select(
            Charge, UtilityService.name, UtilityService.unit,
            PaymentPeriod.year, PaymentPeriod.month,
        )
        .join(Address, Address.id == Charge.address_id)
        .join(UtilityService, UtilityService.id == Charge.service_id)
        .join(PaymentPeriod, PaymentPeriod.id == Charge.period_id)
        .where(Address.resident_id == resident_id)
        .order_by(PaymentPeriod.year.desc(), PaymentPeriod.month.desc(), UtilityService.name)
    )

    charges = []
    for charge, svc_name, svc_unit, yr, mo in result.all():
        charges.append({
            "period": f"{mo:02d}.{yr}",
            "service_name": svc_name,
            "consumption": charge.consumption,
            "unit": svc_unit,
            "amount": charge.amount,
        })

    # All payments
    from app.repositories.payment_repo import PaymentRepository
    pay_repo = PaymentRepository(session)
    total_paid = await pay_repo.get_total_paid(resident_id)
    total_charged = await pay_repo.get_total_charged(resident_id)

    return {
        "resident": resident,
        "charges": charges,
        "total_charged": total_charged,
        "total_paid": total_paid,
        "debt": max(Decimal("0"), total_charged - total_paid),
    }


async def debtors_report(session: AsyncSession) -> List[Dict]:
    """List of residents with outstanding debt."""
    result = await session.execute(
        select(
            Resident.id,
            Resident.full_name,
            Resident.personal_account,
            func.coalesce(func.sum(Charge.amount), 0).label("charged"),
        )
        .join(Address, Address.resident_id == Resident.id)
        .join(Charge, Charge.address_id == Address.id)
        .group_by(Resident.id, Resident.full_name, Resident.personal_account)
    )
    residents_charges = {row[0]: {"name": row[1], "account": row[2], "charged": row[3]} for row in result.all()}

    result2 = await session.execute(
        select(
            Resident.id,
            func.coalesce(func.sum(Payment.amount), 0).label("paid"),
        )
        .join(Payment, Payment.resident_id == Resident.id)
        .group_by(Resident.id)
    )
    paid_map = {row[0]: row[1] for row in result2.all()}

    debtors = []
    for res_id, info in residents_charges.items():
        paid = paid_map.get(res_id, Decimal("0"))
        debt = info["charged"] - paid
        if debt > 0:
            debtors.append({
                "id": res_id,
                "full_name": info["name"],
                "personal_account": info["account"],
                "charged": info["charged"],
                "paid": paid,
                "debt": debt,
            })

    debtors.sort(key=lambda x: x["debt"], reverse=True)
    return debtors
