def test_create_animal_and_list(client):
    r = client.post(
        "/animals/",
        json={
            "tattoo": "D1",
            "sex": "F",
            "status": "breeder",
            "breed": "NZ",
            "color": "white",
            "birth_date": "2025-12-01",
            "source": "home",
            "notes": None,
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "animal_id" in data

    r2 = client.get("/animals/")
    assert r2.status_code == 200
    assert any(a["tattoo"] == "D1" for a in r2.json())


def test_breeding_litter_generate_kits_harvest_and_metrics_flow(client):
    doe = client.post("/animals/", json={"tattoo": "DOE2", "sex": "F", "status": "breeder"}).json()
    buck = client.post("/animals/", json={"tattoo": "BUK2", "sex": "M", "status": "breeder"}).json()

    b = client.post(
        "/breedings/",
        json={"doe_id": doe["animal_id"], "buck_id": buck["animal_id"], "bred_date": "2026-01-01"},
    )
    assert b.status_code == 200, b.text
    breeding = b.json()
    assert breeding["result"] == "pending"

    l = client.post(
        "/litters/",
        json={
            "breeding_id": breeding["breeding_id"],
            "kindling_date": "2026-02-01",
            "born_alive": 8,
            "born_dead": 1,
            "weaned_count": 7,
        },
    )
    assert l.status_code == 200, l.text
    litter = l.json()

    g = client.post(
        f"/litters/{litter['litter_id']}/generate-kits",
        json={"weaned_count": 7, "male_count": 3, "female_count": 4},
    )
    assert g.status_code == 200, g.text
    gj = g.json()
    assert gj["created"] == 7
    assert len(gj["animal_ids"]) == 7
    assert all(t.startswith(f"L{litter['litter_id']}-K") for t in gj["tattoos"])

    lk = client.get(f"/litters/{litter['litter_id']}/kits")
    assert lk.status_code == 200
    kits = lk.json()
    assert len(kits) == 7

    kit0 = kits[0]
    h = client.post(
        "/harvests/",
        json={
            "animal_id": kit0["animal_id"],
            "harvest_date": "2026-04-10",
            "live_weight_grams": 2800,
            "carcass_weight_grams": 1600,
        },
    )
    assert h.status_code == 200, h.text

    m = client.get("/metrics")
    assert m.status_code == 200
    mj = m.json()
    assert mj["total_litters"] >= 1
    assert mj["harvested_rabbits"] >= 1


def test_cannot_create_animal_as_deceased_or_harvested(client):
    r1 = client.post("/animals/", json={"tattoo": "BAD-DEAD", "sex": "U", "status": "deceased"})
    assert r1.status_code == 400

    r2 = client.post("/animals/", json={"tattoo": "BAD-HARV", "sex": "U", "status": "harvested"})
    assert r2.status_code == 400


def test_mark_animal_deceased_flow(client):
    a = client.post("/animals/", json={"tattoo": "X-DEAD", "sex": "U", "status": "growout"})
    assert a.status_code == 200, a.text
    aj = a.json()

    r = client.patch(
        f"/animals/{aj['animal_id']}",
        json={"status": "deceased", "death_date": "2026-02-01", "death_reason": "illness"},
    )
    assert r.status_code == 200, r.text
    uj = r.json()
    assert uj["status"] == "deceased"
    assert uj["death_date"] == "2026-02-01"
    assert uj["death_reason"] == "illness"

    lst = client.get("/animals/")
    assert lst.status_code == 200
    assert any(x["tattoo"] == "X-DEAD" and x["status"] == "deceased" for x in lst.json())


def test_dashboard_todo_endpoint_exists(client):
    r = client.get("/dashboard/todo")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "kindlings_due" in data
    assert "weanings_due" in data
    assert "harvest_ready" in data
    assert "params" in data
    assert "as_of" in data


def test_reports_csv_endpoints_exist_and_return_csv(client):
    r1 = client.get("/reports/breedings.csv")
    assert r1.status_code == 200, r1.text
    assert "text/csv" in r1.headers.get("content-type", "")
    assert "breeding_id" in r1.text.splitlines()[0]

    r2 = client.get("/reports/litters.csv")
    assert r2.status_code == 200, r2.text
    assert "text/csv" in r2.headers.get("content-type", "")
    assert "litter_id" in r2.text.splitlines()[0]

    r3 = client.get("/reports/harvests.csv")
    assert r3.status_code == 200, r3.text
    assert "text/csv" in r3.headers.get("content-type", "")
    assert "harvest_id" in r3.text.splitlines()[0]

    r4 = client.get("/reports/feed-costs.csv")
    assert r4.status_code == 200, r4.text
    assert "text/csv" in r4.headers.get("content-type", "")
    assert "feed_cost_id" in r4.text.splitlines()[0]


def test_reports_summary_endpoint_exists(client):
    r = client.get("/reports/summary")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "kpis" in data
    assert "series" in data


def test_reports_date_filters_work(client):
    doe = client.post("/animals/", json={"tattoo": "DOE-RPT", "sex": "F", "status": "breeder"}).json()
    buck = client.post("/animals/", json={"tattoo": "BUK-RPT", "sex": "M", "status": "breeder"}).json()

    b = client.post(
        "/breedings/",
        json={"doe_id": doe["animal_id"], "buck_id": buck["animal_id"], "bred_date": "2026-01-01"},
    )
    assert b.status_code == 200, b.text

    r_all = client.get("/reports/breedings.csv")
    assert r_all.status_code == 200
    assert "2026-01-01" in r_all.text

    r_future = client.get("/reports/breedings.csv?start_date=2099-01-01&end_date=2099-12-31")
    assert r_future.status_code == 200
    assert "2026-01-01" not in r_future.text

    lines = [ln for ln in r_future.text.splitlines() if ln.strip()]
    assert len(lines) >= 1
    assert lines[0].startswith("breeding_id")


def test_feed_cost_create_and_list(client):
    r = client.post(
        "/feed-costs/",
        json={
            "date": "2026-01-15",
            "description": "50lb pellets",
            "cost_per_unit": 0.60,
            "total_cost": 30.00,
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "feed_cost_id" in data
    assert data["total_cost"] == 30.00

    r2 = client.get("/feed-costs/")
    assert r2.status_code == 200
    assert any(fc["description"] == "50lb pellets" for fc in r2.json())


def test_feed_cost_delete(client):
    r = client.post(
        "/feed-costs/",
        json={"date": "2026-02-01", "total_cost": 25.00},
    )
    assert r.status_code == 200, r.text
    fc_id = r.json()["feed_cost_id"]

    rd = client.delete(f"/feed-costs/{fc_id}")
    assert rd.status_code == 204, rd.text

    r2 = client.get("/feed-costs/")
    assert not any(fc["feed_cost_id"] == fc_id for fc in r2.json())


def test_feed_cost_appears_in_reports_summary(client):
    client.post("/feed-costs/", json={"date": "2026-03-01", "total_cost": 50.00})
    client.post("/feed-costs/", json={"date": "2026-04-01", "total_cost": 40.00})

    r = client.get("/reports/summary")
    assert r.status_code == 200, r.text
    kpis = r.json()["kpis"]
    assert kpis["total_feed_cost"] == 90.00
    assert kpis["avg_feed_cost_per_month"] == 45.00

    series = r.json()["series"]
    assert "feed_cost" in series
    months = {p["month"]: p["value"] for p in series["feed_cost"]["points"]}
    assert months.get("2026-03") == 50.00
    assert months.get("2026-04") == 40.00
