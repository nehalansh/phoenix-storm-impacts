"""Build the storm-impact dataset from the raw event folders.

    python scripts/build_dataset.py RAW_DIR DOMAIN_SHP [--out data]

RAW_DIR
    One subfolder per event, named YYYY-MM-DD, holding
      * ``lsr_<start>_<end>.zip``: NWS Local Storm Reports downloaded from the
        Iowa Environmental Mesonet (https://mesonet.agron.iastate.edu/request/gis/lsrs.phtml),
        office PSR (Phoenix), shapefile+CSV format; <start> and <end> are the
        download window in UTC (YYYYMMDDHHMM). Several downloads per event are
        merged; empty (0-byte) files are skipped;
      * ``Flooding_Events_Updated.shp`` (optional): the flood reports selected
        by hand for the event, a subset of the reports in the downloads.
    plus ``StormEventDetails.xlsx`` with sheets "Precipitation", "Wind" and
    "Impact"; on each sheet the header is on row 3 with columns "Event Date",
    "Start date", "Start time", "End date", "End time",
    "Time of P in Phoenix (end hour)" and "Comments" (local time).
DOMAIN_SHP
    Polygons of the stormwater model domain (sub-catchments of the City of
    Phoenix SWMM model). Used only to flag reports inside it; not distributed.

Outputs (in --out): events.csv, storm_reports.csv/.gpkg, flood_reports.csv/.gpkg
(see README.md for every column).

Requires pandas >= 2, geopandas >= 1.0, pyogrio and openpyxl.
"""
import argparse
import glob
import io
import os
import re
import zipfile

import geopandas as gpd
import pandas as pd

EVENTS = ["2014-08-19", "2015-08-31", "2018-07-09", "2018-10-02", "2021-07-22",
          "2021-08-13", "2021-08-17", "2022-07-30", "2022-08-04"]
LOCAL_OFFSET = pd.Timedelta(hours=-7)   # Arizona: MST all year (UTC-7)
DOMAIN_TOLERANCE_M = 500.0              # reports within 500 m of the domain count as inside
COLUMNS = {"VALID": "time_utc", "TYPECODE": "type_code", "TYPETEXT": "type", "MAG": "magnitude",
           "CITY": "location", "COUNTY": "county", "STATE": "state", "SOURCE": "source",
           "REMARK": "remark", "LAT": "lat", "LON": "lon", "WFO": "wfo", "UGC": "ugc",
           "UGCNAME": "ugc_name"}
KEY = ["time_utc", "lat", "lon", "remark"]


def read_lsr(event_dir):
    """Reports of every non-empty download of an event, and the download window (UTC)."""
    frames, starts, ends = [], [], []
    for z in sorted(glob.glob(os.path.join(event_dir, "lsr_*.zip"))):
        if os.path.getsize(z) == 0:
            continue
        m = re.search(r"lsr_(\d{12})_(\d{12})", os.path.basename(z))
        starts.append(pd.to_datetime(m.group(1), format="%Y%m%d%H%M"))
        ends.append(pd.to_datetime(m.group(2), format="%Y%m%d%H%M"))
        with zipfile.ZipFile(z) as zz:
            name = next(n for n in zz.namelist() if n.endswith(".csv"))
            frames.append(pd.read_csv(io.BytesIO(zz.read(name)), dtype=str))
    reports = pd.concat(frames).drop_duplicates().reset_index(drop=True)
    return reports, min(starts), max(ends)


def tidy(df, event_id):
    out = df.rename(columns=COLUMNS)[list(COLUMNS.values())].copy()
    out["time_utc"] = pd.to_datetime(out.time_utc.astype(str), format="%Y%m%d%H%M")
    out["time_local"] = out.time_utc + LOCAL_OFFSET
    for c in ("lat", "lon", "magnitude"):
        out[c] = pd.to_numeric(out[c], errors="coerce")
    for c in ("type_code", "type", "location", "county", "state", "source", "remark",
              "wfo", "ugc", "ugc_name"):
        out[c] = out[c].astype(str).str.strip().replace({"nan": None})
    out.insert(0, "event_id", event_id)
    return out


def event_table(xlsx):
    """Event time windows (local) from StormEventDetails.xlsx."""
    sheets = pd.read_excel(xlsx, sheet_name=None, header=2)
    rows = {}

    def stamp(d, t):
        return None if pd.isna(d) or pd.isna(t) else f"{pd.Timestamp(d):%Y-%m-%d} {str(t)[:5]}"

    for kind, df in sheets.items():
        df.columns = [c.strip() for c in df.columns]
        k = kind.lower()
        for _, r in df.dropna(subset=["Event Date"]).iterrows():
            e = pd.Timestamp(r["Event Date"]).strftime("%Y-%m-%d")
            row = rows.setdefault(e, {"event_id": e})
            row[f"{k}_start_local"] = stamp(r["Start date"], r["Start time"])
            row[f"{k}_end_local"] = stamp(r["End date"], r["End time"])
            note = r.get("Time of P in Phoenix (end hour)")
            if k == "precipitation" and not pd.isna(note):
                row["precipitation_hours_note"] = str(note)
            if isinstance(r.get("Comments"), str) and r["Comments"].strip():
                row[f"{k}_comment"] = r["Comments"].strip()
    cols = ["event_id", "precipitation_start_local", "precipitation_end_local",
            "precipitation_hours_note", "precipitation_comment", "impact_start_local",
            "impact_end_local", "impact_comment", "wind_start_local", "wind_end_local", "wind_comment"]
    return pd.DataFrame([rows[e] for e in EVENTS]).reindex(columns=cols)


def event_window(row):
    """Earliest start and latest end of the precipitation and impact windows (local)."""
    starts = [pd.Timestamp(row[c]) for c in ("precipitation_start_local", "impact_start_local") if pd.notna(row[c])]
    ends = [pd.Timestamp(row[c]) for c in ("precipitation_end_local", "impact_end_local") if pd.notna(row[c])]
    return (min(starts) if starts else None, max(ends) if ends else None)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("raw_dir")
    ap.add_argument("domain_shp")
    ap.add_argument("--out", default="data")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    domain = gpd.read_file(args.domain_shp).to_crs(32612).union_all().buffer(DOMAIN_TOLERANCE_M)
    events = event_table(os.path.join(args.raw_dir, "StormEventDetails.xlsx")).set_index("event_id")

    storms, floods = [], []
    for e in EVENTS:
        d = os.path.join(args.raw_dir, e)
        raw, dl_start, dl_end = read_lsr(d)
        events.loc[e, "download_start_utc"] = f"{dl_start:%Y-%m-%d %H:%M}"
        events.loc[e, "download_end_utc"] = f"{dl_end:%Y-%m-%d %H:%M}"
        g = tidy(raw, e).sort_values(["time_utc", "lat", "lon", "type", "remark"]).reset_index(drop=True)
        g.insert(1, "report_uid", [f"{e}-{i:03d}" for i in range(1, len(g) + 1)])
        g = gpd.GeoDataFrame(g, geometry=gpd.points_from_xy(g.lon, g.lat), crs=4326)
        g["in_model_domain"] = g.to_crs(32612).within(domain)
        t0, t1 = event_window(events.loc[e])
        g["in_event_window"] = g.time_local.between(t0, t1) if t0 is not None else False
        # the same report issued more than once with different text: mark all but
        # the version with the longest text as duplicates of it
        g["_len"] = g.remark.fillna("").str.len()
        grp = g.groupby(["time_utc", "lat", "lon", "type"], sort=False)
        keep = g.loc[grp["_len"].idxmax(), ["time_utc", "lat", "lon", "type", "report_uid"]]
        g = g.merge(keep.rename(columns={"report_uid": "_keep"}), on=["time_utc", "lat", "lon", "type"])
        g["duplicate_of"] = g._keep.where(g._keep != g.report_uid)
        g = g.drop(columns=["_len", "_keep"])

        curated = os.path.join(d, "Flooding_Events_Updated.shp")
        if os.path.exists(curated):
            # the hand-selected shapefile decides WHICH reports are flood impacts;
            # attributes are taken from the original reports (the shapefile's
            # attribute columns are not reliable)
            sel = tidy(gpd.read_file(curated).drop(columns="geometry"), e)[KEY]
            hit = g.merge(sel.drop_duplicates(), on=KEY, how="inner")
            assert len(hit) == len(sel.drop_duplicates()), f"{e}: selected report missing from downloads"
            f = hit.copy()
            f["selection"] = "reviewed"
        else:
            f = g[g["type"].str.contains("FLOOD") & g.in_model_domain & g.in_event_window
                  & g.duplicate_of.isna()].copy()
            f["selection"] = "rule"
        g["is_flood_impact"] = g.report_uid.isin(f.report_uid)
        storms.append(g)
        floods.append(f)

    storms = gpd.GeoDataFrame(pd.concat(storms, ignore_index=True), crs=4326)
    floods = gpd.GeoDataFrame(pd.concat(floods, ignore_index=True), crs=4326)
    floods = floods.drop(columns=["in_model_domain", "in_event_window", "duplicate_of"])
    xy = floods.to_crs(32612).geometry
    floods["x_utm12n"], floods["y_utm12n"] = xy.x.round(1), xy.y.round(1)

    events["n_flood_reports"] = floods.groupby("event_id").size()
    events["n_storm_reports"] = storms[storms.duplicate_of.isna()].groupby("event_id").size()
    events["n_storm_reports_in_event_window"] = storms[storms.duplicate_of.isna() & storms.in_event_window].groupby("event_id").size()
    events["flood_report_selection"] = floods.groupby("event_id").selection.first()
    events.reset_index().to_csv(os.path.join(args.out, "events.csv"), index=False)

    order_s = ["event_id", "report_uid", "time_utc", "time_local", "type_code", "type", "magnitude",
               "location", "county", "state", "ugc", "ugc_name", "wfo", "source", "remark", "lat", "lon",
               "in_model_domain", "in_event_window", "is_flood_impact", "duplicate_of", "geometry"]
    order_f = ["event_id", "report_uid", "time_utc", "time_local", "type_code", "type", "magnitude",
               "location", "county", "state", "ugc", "ugc_name", "wfo", "source", "remark", "lat", "lon",
               "x_utm12n", "y_utm12n", "selection", "geometry"]
    for name, df, order in (("storm_reports", storms, order_s), ("flood_reports", floods, order_f)):
        df = df[order]
        df.drop(columns="geometry").to_csv(os.path.join(args.out, f"{name}.csv"), index=False,
                                           date_format="%Y-%m-%d %H:%M")
        df.to_file(os.path.join(args.out, f"{name}.gpkg"), layer=name, driver="GPKG")
    print(events[["n_flood_reports", "n_storm_reports", "n_storm_reports_in_event_window",
                  "flood_report_selection"]].to_string())


if __name__ == "__main__":
    main()
