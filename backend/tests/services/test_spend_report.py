from app.services.expenditure import SpendRow, spend_report


def row(
    practice: str, provider: str, *, notes: int, cost: int, unpriced: int = 0, plan: str = "essentials"
) -> SpendRow:
    return SpendRow(
        f"id-{practice}", practice, plan, f"id-{provider}", provider, notes, notes, 1_000, 100, cost, unpriced
    )


def test_cost_per_note_is_kept_to_a_hundredth_of_a_cent():
    report = spend_report([row("Lakeside", "Elena Varga", notes=3, cost=100_000)])
    assert (report["totals"]["cost_usd"], report["totals"]["cost_per_note_usd"]) == (0.1, 0.0333)


def test_an_unpriced_run_leaves_cost_per_note_unknown_but_counts_the_rest():
    report = spend_report([row("Lakeside", "Elena Varga", notes=2, cost=40_000, unpriced=1)])
    assert (report["totals"]["cost_usd"], report["totals"]["cost_per_note_usd"]) == (0.04, None)
    assert report["totals"]["unpriced_analyses"] == 1


def test_practices_and_providers_run_from_the_highest_cost_then_by_name():
    report = spend_report(
        [
            row("Lakeside", "Omar Haddad", notes=1, cost=10_000),
            row("Hillside", "Ana Ruiz", notes=1, cost=30_000, plan="trial"),
            row("Lakeside", "Elena Varga", notes=1, cost=10_000),
            row("Lakeside", "Ben Cole", notes=1, cost=15_000),
        ]
    )
    practices = report["practices"]
    assert [(practice["name"], practice["cost_usd"]) for practice in practices] == [
        ("Lakeside", 0.04),
        ("Hillside", 0.03),
    ]
    assert [provider["name"] for provider in practices[0]["providers"]] == ["Ben Cole", "Elena Varga", "Omar Haddad"]
    assert (practices[0]["plan_monthly_cents"], practices[1]["plan_monthly_cents"]) == (14_900, None)
