# phoenix-storm-impacts

Documented impacts of nine storms on the City of Phoenix, Arizona
(2014-2022): where and when street flooding was reported during each storm,
and every storm report (flooding, wind damage, gusts, hail, heavy rain, dust)
issued by the National Weather Service around it.

## Purpose

Models of urban flooding and of storm damage to infrastructure need
observations of what actually happened. Systematic records of street
flooding rarely exist; the most consistent public source is the NWS Local
Storm Reports, issued by forecasters from spotter, public, media and
agency reports. This dataset gathers, for nine storms with documented
impacts on stormwater and power infrastructure in Phoenix (intense monsoon
rainfall and/or damaging wind), the reports issued around each storm and
the subset that documents flooding inside the area covered by the City's
stormwater model. It was compiled to evaluate simulations of urban flooding
during these storms (see **Related publication**).

## The events

| Event | Rain over the region (local time) | Flood reports in the model domain | Distinct storm reports during the event | ... in the whole download |
|---|---|---|---|---|
| 2014-08-19 | 03:00-22:00 | 6 (rule) | 33 | 44 |
| 2015-08-31 | 19:00-23:00 | 4 | 38 | 82 |
| 2018-07-09 | 16:00-19:00 | 3 | 49 | 121 |
| 2018-10-02 | 01:00-23:00 | 11 | 39 | 39 |
| 2021-07-22 | 21:00 (22nd)-22:00 (23rd) | 4 | 33 | 77 |
| 2021-08-13 | 19:00 (13th)-06:00 (14th) | 7 | 37 | 44 |
| 2021-08-17 | 23:00 (16th)-19:00 (18th) | 10 | 75 | 95 |
| 2022-07-30 | 15:00-22:00 | 7 | 53 | 71 |
| 2022-08-04 | 04:00-07:00 | 4 | 5 | 7 |

Flood reports were selected by hand except for 2014-08-19, where the same
criteria were applied automatically ("rule"). "During the event" means
inside the event window defined below; the downloads span several days and
contain reports from other storms.

## Key terms

| Term | Meaning |
|---|---|
| Local Storm Report (LSR) | A report of a hazardous weather event (flooding, wind damage, hail...) issued by an NWS forecast office from spotters, the public, media or agencies. Times are when the event was observed, to the minute; locations are approximate (0.01 degree). |
| NWS Phoenix office (WFO PSR) | The forecast office issuing the reports. It covers south-central and western Arizona (Maricopa, Pinal, Gila, Yuma, La Paz counties) and south-eastern California (Imperial, Riverside, San Bernardino); the storm reports cover this whole area. |
| Model domain | The area covered by the sub-catchments of the City of Phoenix stormwater model (EPA SWMM), about 703 km^2 of central Phoenix. A report is "in the model domain" if it lies within 500 m of it. The polygon is derived from City infrastructure data and is not distributed; the `in_model_domain` flag records membership. |
| Event window | From the earliest start to the latest end of the precipitation and impact windows of the event (local time, `events.csv`). |
| Download window | The period over which the reports of an event were downloaded (UTC, `events.csv`); several days around the event. |
| MST / local time | Arizona time: Mountain Standard Time, UTC-7, no daylight saving. |
| MRMS | Multi-Radar Multi-Sensor, the NOAA radar precipitation product used to define the precipitation windows (not available for 2014). |
| UGC | NWS universal geographic code of the county (e.g. AZC013 = Maricopa County). |

## Files (`data/`)

| File | Rows | Content |
|---|---|---|
| `events.csv` | 9 | One row per event: time windows, notes, download window, report counts |
| `storm_reports.csv`, `.gpkg` | 602 (580 distinct) | Every Local Storm Report in the download window of each event |
| `flood_reports.csv`, `.gpkg` | 56 | Flood reports in the model domain selected as impacts of each event (a subset of `storm_reports`) |

The GeoPackages hold the same tables as the CSVs with point geometry in
WGS84 (EPSG:4326). Times are written as `YYYY-MM-DD HH:MM` without a time
zone: `time_utc` in UTC, `time_local` in MST (UTC-7).

### `storm_reports`

| Column | Description |
|---|---|
| `event_id` | Event (date of the event, `YYYY-MM-DD`) |
| `report_uid` | Unique report identifier, `<event_id>-<nnn>` |
| `time_utc`, `time_local` | Time of the observed event, UTC and MST |
| `type_code`, `type` | NWS report type: `F` FLASH FLOOD, `E` FLOOD, `R` HEAVY RAIN, `D` TSTM WND DMG (thunderstorm wind damage), `G` TSTM WND GST (gust), `O`/`N` non-thunderstorm wind damage/gust, `H` HAIL, `2` DUST STORM, `L` LIGHTNING |
| `magnitude` | Gust speed in mph (`G`, `N`), hail diameter in inches (`H`), rainfall in inches (`R`); empty for other types |
| `location` | Location as reported, relative to a place name (e.g. "3 S DEER VALLEY" = 3 miles south of Deer Valley) |
| `county`, `state`, `ugc`, `ugc_name` | County, state and county code |
| `wfo` | Issuing NWS office (PSR = Phoenix) |
| `source` | Who reported it (trained spotter, public, broadcast media, department of highways...) |
| `remark` | Report text, as issued (upper case; some special characters such as "/" were lost in the NWS text, e.g. "1 8 - 1 4 INCH" for 1/8-1/4 inch); empty for some gust and hail reports |
| `lat`, `lon` | Coordinates (WGS84, 0.01-degree precision) |
| `in_model_domain` | Within 500 m of the model domain |
| `in_event_window` | `time_local` within the event window |
| `is_flood_impact` | Selected as a flood impact (listed in `flood_reports`) |
| `duplicate_of` | For a report issued more than once with different text (same time, place and type), the `report_uid` of the version kept (the one with the longest text); empty otherwise. Filter `duplicate_of.isna()` to count distinct reports |

### `flood_reports`

The same columns as `storm_reports` (with `report_uid` linking the two),
plus `x_utm12n`, `y_utm12n` (UTM Zone 12N, m) and `selection`
(`reviewed`: chosen by hand; `rule`: chosen by the criteria below).

### `events.csv`

| Column | Description |
|---|---|
| `event_id` | Event date |
| `precipitation_start_local`, `precipitation_end_local` | Period of precipitation over the region (MRMS radar), MST |
| `precipitation_hours_note` | Free-text note of the hours with rain over Phoenix, as recorded (e.g. "8 PM, 9 PM") |
| `impact_start_local`, `impact_end_local` | Period of reported impacts, MST (where determined) |
| `wind_start_local`, `wind_end_local` | Period of damaging wind, MST (where determined; equal to the impact window when both are given) |
| `*_comment` | Notes |
| `download_start_utc`, `download_end_utc` | Period of the downloaded reports, UTC |
| `n_flood_reports`, `n_storm_reports`, `n_storm_reports_in_event_window` | Number of flood reports and of distinct storm reports |
| `flood_report_selection` | `reviewed` or `rule` |

Empty cells mean "not determined". For 2014-08-19 the windows are not
radar-based (no MRMS data); for 2021-08-17 the precipitation window starts
on the previous evening.

## Using the data

```python
import pandas as pd
import geopandas as gpd

events = pd.read_csv("data/events.csv")
floods = gpd.read_file("data/flood_reports.gpkg")          # 56 flood impacts
storms = pd.read_csv("data/storm_reports.csv", parse_dates=["time_utc", "time_local"])

floods.groupby("event_id").size()                           # flood reports per event
during = storms[storms.in_event_window & storms.duplicate_of.isna()]
during.groupby(["event_id", "type"]).size()                 # what each storm did
storms[storms.is_flood_impact].merge(floods[["report_uid", "selection"]], on="report_uid")
```

Each row is a report, not an incident: one flooded underpass may be reported
twice by different sources (e.g. 2021-08-13, I-17 at the Durango curve).

## How the flood reports were selected

For eight events, the flood and flash-flood reports inside the model domain
were reviewed by hand and those documenting flooding caused by the storm
were kept. For 2014-08-19, for which no manual selection exists, the same
criteria were applied automatically: type FLOOD or FLASH FLOOD, within 500 m
of the model domain, inside the event window, one version per re-issued
report. The manual selections include one report two days after the rain
(2021-07-25, I-10 flooded near 75th-91st Avenues) and exclude one report
inside the window (2018-10-02 10:32, 19th Avenue closed).

Cleaning of the raw downloads: empty and duplicate download files were
discarded; reports present in overlapping downloads were merged; the
attributes of the selected reports were taken from the original NWS records.

## Rebuilding

```bash
pip install "pandas>=2" "geopandas>=1.0" pyogrio openpyxl
python scripts/build_dataset.py RAW_DIR DOMAIN_SHP --out data
```

The script docstring describes the expected raw folders: one per event with
the report downloads (from the Iowa Environmental Mesonet, office PSR, over
the download windows listed in `events.csv`) and the manual selection
(`Flooding_Events_Updated.shp`, optional), and the event spreadsheet.
`DOMAIN_SHP` is the model domain, which is not distributed.

## Sources

NWS Local Storm Reports, Phoenix Weather Forecast Office, retrieved from the
Iowa Environmental Mesonet: https://mesonet.agron.iastate.edu/request/gis/lsrs.phtml

## Related publication

Srivastava, N. A., Sparks, R., Chester, M., Porto, M., Johnson, N., and
Mascaro, G. (2026). A coupled stormwater-power model for the simulation of
cascading infrastructure failures: An application in Phoenix, AZ.
*Environmental Modelling & Software*, 201, 106980.
https://doi.org/10.1016/j.envsoft.2026.106980

## Citation

See [CITATION.cff](CITATION.cff).

## Acknowledgements

This work has been supported by the National Institute of Standards and
Technology (NIST)-National Science Foundation (NSF) award #70NANB22H056,
"DRRG: Assessing the Utility of Safe-To-Fail Design to Improve Climate
Hazards Resilience of Interdependent Infrastructure Systems."

## License

Data (`data/`): CC BY 4.0, see [data/LICENSE](data/LICENSE). Script: MIT,
see [LICENSE](LICENSE). The underlying NWS reports are in the public domain.
